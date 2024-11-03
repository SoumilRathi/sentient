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
from scrapy.crawler import CrawlerProcess
from scrapy import Spider, Request
from scrapingbee import ScrapingBeeClient
from datetime import datetime
import asyncio
from typing import Dict, List
import time

# Load environment variables from .env file
load_dotenv()

scrapingbee_client = ScrapingBeeClient(api_key=os.getenv("SCRAPINGBEE_API_KEY"))

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
        self.reminders: Dict[datetime, List[dict]] = {}

        self.reminder_thread = None
        self.reminder_thread_lock = threading.Lock()
        # Only start reminder thread if it's not already running
        with self.reminder_thread_lock:
            if self.reminder_thread is None or not self.reminder_thread.is_alive():
                self.reminder_thread = threading.Thread(target=self._check_reminders, daemon=True)
                self.reminder_thread.start()

    def start(self, selected_actions, behavior):
        """Start the agent"""
        self.reset()
        self.selected_actions = selected_actions
        self.behavior = behavior

    
    def browse_web(self):
        """Browses the web"""
        pass
    
    def web_search(self, query):
        """Conducts a web search using Google Custom Search API, creates a Scrapy spider for deep content extraction"""
        search_url = f"https://www.googleapis.com/customsearch/v1"
        params = {
            "key": os.getenv("GOOGLE_SEARCH_API_KEY"), 
            "cx": os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID"),
            "q": query,
        }
        
        response = requests.get(search_url, params=params)
        search_output = f"Query: {query}\n\n"
        
        if response.status_code == 200:
            search_results = response.json()
            
            # Extract URLs from search results
            urls = []
            for item in search_results.get('items', [])[:5]:
                urls.append(item.get('link'))
            
            for url in urls:
                response = scrapingbee_client.get(url,
                    params = { 
                        'ai_query': query,
                        'premium_proxy': True,
                        'country_code': 'us',
                    }
                )
                print(response.content.decode('utf-8'));
                search_output += f"""
                URL: {url}
                CONTENT:
                {response.content.decode('utf-8')}
                """
       
        else:
            print(f"Failed to retrieve search results, status code: {response.status_code}")
            return f"Failed to retrieve search results, status code: {response.status_code}"

        if search_output == "":
            self.working_memory.store_observation("Web search returned no results.")
            return

        print("ALL SEARCH OUTPUT: ", search_output)

        # Process the search output into segments and add it to knowledge
        self.working_memory.text_to_knowledge(search_output, query)
        return

    def scrape_webpage(self, url):
        """Legacy scraping method - now handled by Scrapy spider"""
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
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
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
        6. If there is any task that has a reminder or a specific time associated with it, don't conduct the action now. Instead, set a reminder for the specified time, which will be added to your working memory when the reminder is triggered.
        7. Please note that if you notice a reminder for a task within your previous actions within your working memory, you should ignore that, since that's a reminder for the future. Any reminders that you actually have to act on will be present within your observations with the prefix "REMINDER:"
        8. If acting on a reminder within your observations, please first check if an action corresponding to that reminder has already been taken. If so, that reminder is no longer relevant and can be ignored.

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
        4. Is there any action that requires other actions to be completed first? If so, give higher priority to the actions to be completed first.

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
        """Executes the selected action"""
        isFinal = False
        # get the first word of the action
        action_name = action.split()[0]

        if action_name == "reply":
            reply_message = action[6:]
            if "<wait>" in reply_message:
                reply_message = reply_message.replace("<wait>", "")
                isFinal = True
            if self.reply_callback:
                self.reply_callback(reply_message, self.client_sid)
            self.working_memory.store_conversation_history({
                "from": "agent",
                "message": reply_message
            })
        elif action_name == "search":
            query = action[7:].strip('"')  # Extract search query 
            self.web_search(query)
            print(f"Search completed for query: {query}")
        elif action_name == "email":
            print(f"Sending email: {action[7:]}")
            # Extract email, subject and body from the action string
            email_content = action[6:].strip()
            
            # Find first quote-wrapped section (email)
            first_quote_start = email_content.find('"') + 1
            first_quote_end = email_content.find('"', first_quote_start)
            email_address = email_content[first_quote_start:first_quote_end]
            
            # Find second quote-wrapped section (subject)
            second_quote_start = email_content.find('"', first_quote_end + 1) + 1
            second_quote_end = email_content.find('"', second_quote_start)
            subject = email_content[second_quote_start:second_quote_end]
            
            # Find body section (either triple or double quoted)
            remaining = email_content[second_quote_end + 1:].strip()
            if remaining.startswith('"""'):
                body_start = remaining.find('"""') + 3
                body_end = remaining.find('"""', body_start)
                body = remaining[body_start:body_end]
            else:
                body_start = remaining.find('"') + 1
                body_end = remaining.find('"', body_start)
                body = remaining[body_start:body_end]
            
            send_email(email_address, subject, body)
            print(f"Sending email to: {email_address}")
            print(f"Subject: {subject}")
            print(f"Body: {body}")
        elif action_name == "reason":
            print(f"Reasoning: {action[7:]}")
            self.working_memory.reason(action[7:])

        elif action_name == "record":
            self.working_memory.observations.append(action[6:])

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

        elif action_name == "remind":
            # Extract time and task from the remind action
            # Format: remind <TIME> "<TASK>"
            parts = action[7:].split(' "', 1)
            if len(parts) == 2:
                time_str = parts[0].strip()
                task = parts[1].strip('"')
                self.set_reminder(time_str, task)

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


    

    def _check_reminders(self):
        """Background thread that checks for due reminders"""
        while True:
            current_time = datetime.now()
            reminders_to_process = []

            print("CURRENT TIME: ", current_time)
            print("REMINDERS: ", self.reminders)
            
            # Create a copy of reminder times to avoid modification during iteration
            reminder_times = list(self.reminders.keys())
            
            # Check for due reminders
            for reminder_time in reminder_times:
                print("REMINDER TIME: ", reminder_time)
                if current_time >= reminder_time:
                    reminders_to_process.extend(self.reminders[reminder_time])
                    del self.reminders[reminder_time]
            
            # Process due reminders
            for reminder in reminders_to_process:
                print("PROCESSING REMINDER: ", reminder)
                self.process_reminder(reminder)
            
            # Sleep for a short interval before next check
            time.sleep(60)  # Check every minute
    def process_reminder(self, reminder):
        """Process a due reminder"""
        # Add reminder context to working memory
        self.working_memory.store_observation(f"REMINDER: {reminder['message']}")
        
        # Start decision loop if not already running
        if not self.decision_loop_running:
            self.decision_thread = threading.Thread(target=self.make_decision)
            self.decision_thread.start()
    
    def set_reminder(self, time_str: str, message: str):
        """Set a reminder for a specific time"""

        print("Sets a reminder for: ", time_str)
        try:
            reminder_time = datetime.fromisoformat(time_str)
            if reminder_time not in self.reminders:
                self.reminders[reminder_time] = []
            
            self.reminders[reminder_time].append({
                'message': message,
                'set_at': datetime.now()
            })
            
            print("Reminder set for: ", reminder_time)
            print("Reminders now: ", self.reminders)
            return True
        except ValueError:
            print(f"Invalid datetime format: {time_str}")
            return False
