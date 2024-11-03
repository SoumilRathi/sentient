import random
import json
import re
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from memory.working_memory import WorkingMemory
from memory.lt_memory import LongTermMemory
from helper_functions import sort_actions_by_priority, get_available_actions, use_claude, send_email
import threading
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Agent:
    def __init__(self):
        """Initialize the agent with working and long-term memory and OpenAI API key"""
        print("Agent initialized")
        self.reply_callback = None 
        self.working_memory = WorkingMemory()
        self.long_term_memory = LongTermMemory()
        self.client_sid = None
        # self.actions_instructions = self.load_actions_from_file("actions.txt")
        self.decision_loop_running = False
        self.decision_thread = None
        self.selected_actions = ["reply"]
        self.behavior = ""

    def start(self, selected_actions, behavior):
        """Start the agent"""
        self.reset()
        self.selected_actions = selected_actions
        self.behavior = behavior

    
    def browse_web(self):
        """Browses the web"""
        pass
    
    def web_search(self, query):
        """Conducts a web search using Google Custom Search API, scrapes the top results, and returns the extracted content"""
        search_url = f"https://www.googleapis.com/customsearch/v1"
        params = {
            "key": os.getenv("GOOGLE_SEARCH_API_KEY"),
            "cx": os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID"),
            "q": query,
        }
        
        response = requests.get(search_url, params=params)
        search_output = "";
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

            search_output = "\n".join(extracted_content)
            print(f"Extracted content from {len(extracted_content)} webpages")

        else:
            print(f"Failed to retrieve search results, status code: {response.status_code}")
            return f"Failed to retrieve search results, status code: {response.status_code}"


        if (search_output == ""):
            self.working_memory.store_observation("Web search returned no results.")
            return;

        print("ALL SEARCH OUTPUT: ", search_output)

        # process the search output into segments and add it to knowledge
        self.working_memory.text_to_knowledge(search_output)
        return;



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
        # Limit the text to a reasonable length (e.g., first 1000 characters)
        return text

    
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
    
    def propose_actions(self):
        """Use OpenAI API to select the best action based on memory"""

        # Construct the user prompt with proposed actions and memory context
        prompt = f"""
        You are an intelligent agent with access to your current working memory and a set of available actions. Your task is to propose up to five potential actions based on the given input. 
        
        Here is the behavior you will adhere to:
        {self.behavior}
        
        Here is your current working memory:

        <working_memory>
        {self.working_memory.print()}
        </working_memory>

        Important constraints and instructions:

        1. Do not generate new knowledge or information on your own. You are prone to hallucinations and must not make any assumptions.
        2. Use only the provided actions to acquire new knowledge.
        3. Consider how to provide the best eventual output based on the given input.
        4. Choose actions that will help you reach that output.
        5. When you have to enter or use explicit variables, identify if you have the required variable in your working memory. If you do, use it. If not, identify the best way to get the value you need. This could be asking the user, searching the web, or more. Determine this based on the variable at hand.

        Available actions:
        {get_available_actions(self.selected_actions)}

        Each action is represented as a string. Your task is to propose up to five actions that you could potentially take at this step. These actions are not to be taken in order; one of the proposed actions will be selected and executed at this stage.

        Before providing your final output, use the <action_analysis> tags to think through your action selection process. Consider the following:
        - For each potential action:
        1. How does it relate to the information in your working memory?
        2. What are the potential outcomes of this action?
        3. How relevant and priority is this action given the current context?
        - Which actions are most likely to lead to a productive outcome?
        - Are there any actions that might be redundant or less useful given the current context?

        After your analysis, provide your final chosen actions in a JSON format. Here's an example of the expected output structure (note that this is just a format example, not a suggestion for actual actions):

        <final>
        {{
            "actions": ["action_1 'parameter'", "action_2 'parameter'", "action_3 'parameter'"]
        }}
        </final>

        Remember, you must propose at least one action and no more than five actions. Each action should be a string that matches the format of the available actions provided to you.

        Now, begin your action analysis:

        """

        response = use_claude(prompt)

        print("PROPOSED ACTIONS + THOUGHT PROCESS: ", response)

        # Find the <final> tag and extract JSON content
        final_start = response.find('<final>')
        final_end = response.find('</final>')
        
        if final_start != -1 and final_end != -1:
            # Extract JSON string between <final> tags and handle escaped quotes
            json_str = response[final_start + 7:final_end].strip()
            # Replace escaped single quotes with regular single quotes
            json_str = json_str.replace("\\'", "'")
            try:
                proposed_actions = json.loads(json_str)["actions"]
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                # If JSON parsing fails, try to extract actions using string manipulation
                if '"actions": [' in json_str:
                    actions_start = json_str.find('"actions": [') + 11
                    actions_end = json_str.rfind(']')
                    actions_str = json_str[actions_start:actions_end+1]
                    # Parse the array string manually
                    proposed_actions = [a.strip()[1:-1] for a in actions_str.split(',')]
                else:
                    proposed_actions = []
        else:
            proposed_actions = []  # Return empty list if no <final> tags found

        # Take first proposed action if available, otherwise None
        action_to_take = proposed_actions[0] if proposed_actions else None
        return action_to_take
        
    
    def execute_action(self, action):
        """Executes the selected action. This will simply do whatever the action is supposed to do, and then store the action in the working memory"""

        isFinal = False
        # get the first word of the action
        action_name = action.split()[0]

        if action_name == "reply":
            if self.reply_callback:
                self.reply_callback(action[6:], self.client_sid)
            self.working_memory.store_conversation_history({
                "from": "agent",
                "message": action[6:]
            })
        elif action_name == "search":
            query = action[7:].strip('"')  # Extract search query 
            self.web_search(query)
            print(f"Search completed for query: {query}")
        elif action_name == "email":
            print(f"Sending email: {action[7:]}")
            # Extract email, subject and body from the action string
            email_match = re.search(r'"([^"]+)"\s+"([^"]+)"\s+"""([\s\S]+?)"""', action[6:])
            if email_match:
                email_address = email_match.group(1)
                subject = email_match.group(2)
                body = email_match.group(3)
                send_email(email_address, subject, body)
                print(f"Sending email to: {email_address}")
                print(f"Subject: {subject}") 
                print(f"Body: {body}")
        elif action_name == "reason":
            print(f"Reasoning: {action[7:]}")

        elif action_name == "learn":
            print(f"Learning: {action[6:]}")

        elif action_name == "finish":
            self.learn()
            try:
                if self.finish_callback:
                    self.finish_callback(self.client_sid, self.project_id)
            except Exception as e:
                print("lmao no finish callback")
            isFinal = True

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
                selected_action = self.propose_actions()
                # trying out the action selection with just one llm call to save resources lmao
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
        self.working_memory.store_conversation_history({
            "from": "user",
            "message": input
        })
        self.working_memory.get_variables_from_input()
        self.client_sid = client_sid
        if not self.decision_loop_running:
            self.decision_thread = threading.Thread(target=self.make_decision)
            self.decision_thread.start()

    def learn(self):
        """Learn from the current working memory"""
        print("LEARNING FROM WORKING MEMORY");

    def reset(self):
        """Reset the agent to its initial state"""
        self.working_memory = WorkingMemory()
        self.long_term_memory = LongTermMemory()
