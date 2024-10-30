import random
import json
import re
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from memory.working_memory import WorkingMemory
from memory.lt_memory import LongTermMemory
from helper_functions import sort_actions_by_priority, actions_instructions
import threading
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

client = OpenAI(api_key='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')

class Agent:
    def __init__(self):
        """Initialize the agent with working and long-term memory and OpenAI API key"""
        self.reply_callback = None 
        self.working_memory = WorkingMemory()
        self.long_term_memory = LongTermMemory()
        self.client_sid = None
        # self.actions_instructions = self.load_actions_from_file("actions.txt")
        self.decision_loop_running = False
        self.decision_thread = None

    def web_search(self, query):
        """Conducts a web search using Google Custom Search API, scrapes the top results, and returns the extracted content"""
        search_url = f"https://www.googleapis.com/customsearch/v1"
        params = {
            "key": os.getenv("GOOGLE_SEARCH_API_KEY"),
            "cx": os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID"),
            "q": query,
        }
        
        response = requests.get(search_url, params=params)
        if response.status_code == 200:
            search_results = response.json()

            # Parse and scrape the top results
            extracted_content = []
            for item in search_results.get('items', [])[:5]:  # Limit to top 5 results
                title = item.get('title')
                link = item.get('link')
                
                try:
                    page_content = self.scrape_webpage(link)
                    extracted_content.append(f"Title: {title}\nContent: {page_content}\n")
                except Exception as e:
                    print(f"Failed to scrape {link}: {str(e)}")

            # Add the extracted content to working memory
            for content in extracted_content:
                self.working_memory.store_knowledge(content)

            search_output = "\n".join(extracted_content)
            print(f"Extracted content from {len(extracted_content)} webpages")
            return search_output

        else:
            print(f"Failed to retrieve search results, status code: {response.status_code}")
            return f"Failed to retrieve search results, status code: {response.status_code}"

    def scrape_webpage(self, url):
        """Scrapes the content of a webpage"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract text content
        text = soup.get_text()
        
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)

        print("SCRAPED CONTENT: ", text)

        
        # Limit the text to a reasonable length (e.g., first 1000 characters)
        return text[:1000]

    
    def load_actions_from_file(self, filename):
        """Load actions from a text file"""
        with open(filename, 'r') as file:
            content = file.read()
        return content

    def reset(self):
        """Reset the agent to its initial state"""
        self.working_memory = WorkingMemory()
        self.long_term_memory = LongTermMemory()
        self.decision_loop_running = False
        self.decision_thread = None
        print("Agent has been reset to its initial state.")

    def select_action(self, best_action):
        """Decides to either select the highest-scoring action or reject all actions"""

        system_prompt = f"""
        You are an intelligent agent. You have access to your current working memory, and the actions available to you. 

        You will be given an input, access to your current working memory, and the selected best action to take. 

        Your choice is to decide to either execute the action or reject it. If you execute the action, that means that it is the best action to take at this stage.
        If you reject the action, new actions will be proposed and evaluated for this state. 

        If you wish to execute the action, output "<execute>". If you wish to reject the action, output "<reject>". 
        First output about what that action would do and entail, and then output the choice. 

        {actions_instructions}
        """

        user_prompt = f"""
        # Working Memory
        {self.working_memory.print()}

        # Selected Action
        {best_action}
        """

        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]

        # Call OpenAI API to determine the action
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        # Extract the LLM's response (the chosen action)
        response_content = completion.choices[0].message.content

        if "<execute>" in response_content:
            return best_action
        else:
            return None
    
    def evaluate_actions(self, actions): 
        """Evaluates the proposed actions and assigns them a score based on their relevance"""

        system_prompt = f"""
        You are an intelligent agent. You have access to your current working memory, and the actions available to you. 

        You will be given an input, access to your current working memory, and a list of proposed actions.

        Your job is to, one by one, evaluate each proposed action based on how helpful it would be at the moment, given the working memory and everything you know about the actions.

        Once you have evaluated each action, give them a score out of 10 based on your evaluation, and output the final list of actions with their scores in the following format:

        {{
            "action 1": "score 1",
            "action 2": "score 2",
            "action 3": "score 3",
            ...
        }}

        Please note that for the scores, you should just output the number as a plain integer, not a fraction, decimal, or sentence.

        {actions_instructions}


        Please evaluate each action carefully first, writing down your evaluation for each action. Then finally output the final list with the scores. 
        """

        user_prompt = f"""
        # Working Memory
        {self.working_memory.print()}

        # Actions
        {', '.join(actions)}
        """

        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]

        print("EVALUATING ACTIONS: ", messages)

        # Call OpenAI API to determine the action
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        # Extract the LLM's response (the chosen action)
        response_content = completion.choices[0].message.content

        print("EVALUATED ACTIONS: ", response_content)

        # Find the JSON-like part in the response
        start = response_content.find('{')
        end = response_content.find('}') + 1
        if start != -1 and end != -1:
            proposed_actions = response_content[start:end]
            
            # Separate the last character '}' from the rest, strip whitespaces from the rest
            before_closing_brace = proposed_actions[:-1].rstrip()  # Strip everything except the last character
            if before_closing_brace[-1] == ',':  # Check if there's a comma before the closing brace
                before_closing_brace = before_closing_brace[:-1]  # Remove the comma

            proposed_actions = before_closing_brace + '}'  # Add the closing brace back

        else:
            proposed_actions = "{}"  # Return empty object if no brackets found

        print("SCORED ACTIONS: ", proposed_actions)
        return json.loads(proposed_actions)
    
    
    def propose_actions(self):
        """Use OpenAI API to select the best action based on memory"""

        # Construct the user prompt with proposed actions and memory context
        user_prompt = f"""
        You are an intelligent agent with access to your current working memory and a set of available actions. Your task is to propose up to five potential actions based on the given input. Here is your current working memory:

        <working_memory>
        {self.working_memory.print()}
        </working_memory>

        Important constraints and instructions:

        1. Do not generate new knowledge or information on your own. You are prone to hallucinations and must not make any assumptions.
        2. Use only the provided actions to acquire new knowledge.
        3. Consider how to provide the best eventual output based on the given input.
        4. Choose actions that will help you reach that output.

        Available actions:
        {actions_instructions}

        Each action is represented as a string. Your task is to propose up to five actions that you could potentially take at this step. These actions are not to be taken in order; one of the proposed actions will be selected and executed at this stage.

        Before providing your final output, use the <action_analysis> tags to think through your action selection process. Consider the following:
        - For each potential action:
        1. How does it relate to the information in your working memory?
        2. What are the potential outcomes of this action?
        3. How relevant and priority is this action given the current context?
        - Which actions are most likely to lead to a productive outcome?
        - Are there any actions that might be redundant or less useful given the current context?

        After your analysis, provide your final chosen actions in a JSON format. Here's an example of the expected output structure (note that this is just a format example, not a suggestion for actual actions):

        {{
            "actions": ["action_1 'parameter'", "action_2 'parameter'", "action_3 'parameter'"]
        }}

        Remember, you must propose at least one action and no more than five actions. Each action should be a string that matches the format of the available actions provided to you.

        Now, begin your action analysis:

        """

        messages = [
            {
                "role": "user",
                "content": user_prompt
            }
        ]


        # Call OpenAI API to determine the action
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        

        # Extract the LLM's response (the chosen action)
        response_content = completion.choices[0].message.content

        print("PROPOSED ACTIONS + THOUGHT PROCESS: ", response_content)

        start = response_content.find('{')
        end = response_content.find('}') + 1
        if start != -1 and end != -1:
            proposed_actions = json.loads(response_content[start:end])["actions"]
        else:
            proposed_actions = "{}"  # Return empty array if no brackets found

        print("PROPOSED ACTIONS: ", proposed_actions)
        return proposed_actions

   
    def reason(self, focus):
        """Reason about the current working memory"""
        system_prompt = """
        You are an intelligent reasoning agent. You have access to your current working memory, and you will be given a focus topic that you have to reason about.

        This means that you have to use the working memory that you have available and use it to reason new knowledge related to the focus topic. 

        Please ensure that you do not introduce any new information or knowledge that is not already present in the working memory. 
        
        There are other ways to introduce new knowledge if you need to, but ensure that you only use the current knowledge that you have available, and not make any new assumptions.

        Any new knowledge that you reason should be in the form of sentences. Take your time to think about it and reason it out. 

        Output your new knowledge as a list of sentences. Even if you only have one sentence, output it as a list. 
        
        If there is no new knowledge that you can reason from the current working memory, simply output an empty list.
        """
        
        user_prompt = f"""
        # Focus
        {focus}

        # Working Memory
        {self.working_memory.print()}
        """
        
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
        
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        
        response_content = completion.choices[0].message.content

        print("REASONING: ", response_content)
        # Find the list within square brackets
        start = response_content.find('[')
        end = response_content.find(']') + 1
        if start != -1 and end != -1:
            list_content = response_content[start:end]
            # Manually parse the string into a list
            reasoned_sentences = [sentence.strip().strip('"') for sentence in list_content.strip('[]').split(',')]
            # Remove any empty strings from the list
            reasoned_sentences = [sentence for sentence in reasoned_sentences if sentence]
        else:
            reasoned_sentences = []  # Empty list if no brackets found

        # Store the reasoned knowledge in working memory
        for sentence in reasoned_sentences:
            self.working_memory.store_knowledge(sentence)

        
        return response_content
        
        
    
    def execute_action(self, action):
        """Executes the selected action. This will simply do whatever the action is supposed to do, and then store the action in the working memory"""

        isFinal = False
        # get the first word of the action
        action_name = action.split()[0]

        if action_name == "reply":
            if self.reply_callback:
                self.reply_callback(action[6:], self.client_sid)
            isFinal = True
        elif action_name == "search":
            print("SEARCHING", action)
            query = action[7:].strip('"')  # Extract search query 
            search_results = self.web_search(query)
            self.working_memory.store_knowledge(f"Search results for '{query}': {search_results}")
            print(f"Search completed for query: {query}")
        elif action_name == "retrieve":
            print("RETRIEVING MEMORY", action)

            # Split the action, but keep quoted parts together
            action_parts = re.findall(r'[^\s"]+|"[^"]*"', action)
            
            # get the second word of the action
            memory_type = action_parts[1]
            # Join the rest of the parts as the memory_request, removing quotes if present
            memory_request = ' '.join(action_parts[2:]).strip('"')

            # assume that the retrieved memory is empty for now (no memory)
            retrieved_memory = self.long_term_memory.retrieve_memory(memory_type, memory_request)

            self.working_memory.store_retrieved_memory(memory_type, memory_request, retrieved_memory)

            print("MEMORY RETRIEVED AND STORED")
            print(self.working_memory.retrieved_memory)

        elif action_name == "reason":
            print(f"Reasoning: {action[7:]}")

        elif action_name == "learn":
            print(f"Learning: {action[6:]}")

        print(f"Executing action: {action}")

        self.working_memory.store_action(action)

        return isFinal
    
    def make_decision(self):
        """Main decision-making loop"""
        self.decision_loop_running = True
        while self.decision_loop_running:
            selected_action = None
            n = 0
            while selected_action is None and n < 3:
                proposed_actions = self.propose_actions()
                scored_actions = self.evaluate_actions(proposed_actions)

                best_action = max(scored_actions, key=scored_actions.get)

                print("BEST ACTION: ", best_action)
                selected_action = self.select_action(best_action)
                n += 1

            if selected_action is None:
                print("Couldn't select an action to pick - must fix something")
                break

            print("FINAL SELECTED ACTION: ", selected_action)
            is_final = self.execute_action(selected_action)
            
            if is_final:
                self.decision_loop_running = False

            print("WORKING MEMORY NOW: ", self.working_memory.print())
            
            print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
    
    def receive_input(self, input, client_sid):
        """Receive input from the user"""
        self.working_memory.store_observation(input)
        self.client_sid = client_sid
        if not self.decision_loop_running:
            self.decision_thread = threading.Thread(target=self.make_decision)
            self.decision_thread.start()



