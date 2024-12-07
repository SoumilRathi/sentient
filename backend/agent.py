import random
import json
import re
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from memory.working_memory import WorkingMemory
from memory.lt_memory import LongTermMemory
from helper_functions import sort_actions_by_priority, use_claude, send_email, get_available_tools, use_claude_tools
import threading
import os
from dotenv import load_dotenv
from scrapy.crawler import CrawlerProcess
from scrapy import Spider, Request
from scrapingbee import ScrapingBeeClient
from datetime import datetime
from browsing.browsing import BrowsingAgent
import asyncio
from typing import Dict, List
import time
from helper.code_execution import generate_and_execute
from scrapeTest import search

# Load environment variables from .env file
load_dotenv()

scrapingbee_client = ScrapingBeeClient(api_key=os.getenv("SCRAPINGBEE_API_KEY"))

class Agent:

    def __init__(self):
        """Initialize the agent with working and long-term memory and OpenAI API key"""
        print("Agent initialized")
        self.working_memory = WorkingMemory()
        self.long_term_memory = LongTermMemory()
        self.browsing_agent = None
        self.client_sid = None
        self.images = []
        # self.actions_instructions = self.load_actions_from_file("actions.txt")
        self.decision_loop_running = False
        self.decision_thread = None
        self.selected_actions = ["reply", "email", "search"]
        self.behavior = ""
        self.reminders: Dict[datetime, List[dict]] = {}

        self.reminder_thread = None
        self.reminder_thread_lock = threading.Lock()
        # Only start reminder thread if it's not already running
        with self.reminder_thread_lock:
            if self.reminder_thread is None or not self.reminder_thread.is_alive():
                self.reminder_thread = threading.Thread(target=self._check_reminders, daemon=True)
                self.reminder_thread.start()

        # Callbacks
        self.reply_callback = None 
        self.reply_streaming_callback = None
        self.browser_view_callback = None
        self.searching_callback = None
        self.searching_logo_callback = None


    def start(self, selected_actions, behavior):
        """Start the agent"""
        self.reset()
        self.selected_actions = selected_actions
        self.behavior = behavior


    def web_search(self, query):
        """Conducts a web search using Google Custom Search API, creates a Scrapy spider for deep content extraction"""
       
        search_output = search(query, self.searching_logo_callback)
        # Process the search output into segments and add it to knowledge
        self.working_memory.dump_info(search_output)
       
        def save_info(info, query):    
            self.working_memory.text_to_knowledge(info, query)
            self.working_memory.remove_info(info)

        threading.Thread(target=save_info, args=(search_output, query)).start()
        return

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
        You are an intelligent agent designed to propose actions based on your current working memory and a set of available actions. Your goal is to quickly and efficiently select the most appropriate actions for the given situation.

        Here is your current working memory:
        <working_memory>
        {self.working_memory.print()}
        </working_memory>


        Your task is to propose and use the ideal action that you could potentially take at this step. Consider the relevance, priority, and potential outcomes of each action given the current context, and propose the best action.

        Directly use the best tools based on the various instructions you have been given.

        Important constraints and instructions:

        1. Do not generate new knowledge or information on your own. You are prone to hallucinations and must not make any assumptions.
        2. Use only the provided actions to acquire new knowledge.
        3. Consider how to provide the best eventual output based on the given input.
        4. Choose actions that will help you reach that output.
        5. When you have to enter or use explicit variables, identify if you have the required variable in your working memory. If you do, use it. If not, identify the best way to get the value you need. This could be asking the user, searching the web, or more. Determine this based on the variable at hand.
        6. If there is any task that has a reminder or a specific time associated with it, don't conduct the action now. Instead, set a reminder for the specified time, which will be added to your working memory when the reminder is triggered.
        7. Please note that if you notice a reminder for a task within your previous actions within your working memory, you should ignore that, since that's a reminder for the future. Any reminders that you actually have to act on will be present within your observations with the prefix "REMINDER:"
        8. If acting on a reminder within your observations, please first check if an action corresponding to that reminder has already been taken. If so, that reminder is no longer relevant and can be ignored.
        9. If you will need any additional information from the user during the course of this task, prioritize asking the user for that information over any other action, so that the user can provide the information immediately and you can continue with the task. In this scenario, no matter what, this action will be the highest priority.
        10. If the user asks you to conduct actions on their behalf on online services, you can use the browse action to do so.
        11. If you have relevant knowledge within your working memory already, you don't need to search the web again for it.
        12. You may have knowledge either in the form of your knowledge in the working memory or in the form of an info dump. Both are valid.
        13. Do not search the web multiple times in a row. This is a waste of resources. Instead, try to make do with a single search, and if you need to refine more, just reply to the user and take it from there. This means that you should try to make do with the search results that you already have.

        When evaluating an action, consider the following:
        1. How does it relate to the information in your working memory?
        2. What are the potential outcomes of this action?
        3. How relevant and priority is this action given the current context?
            - Which actions are most likely to lead to a productive outcome?
            - Are there any actions that might be redundant or less useful given the current context?
        4. Is there any action that requires other actions to be completed first? If so, give higher priority to the actions to be completed first.
        5. Is there any additional information you need from the user to complete the task? If so, prioritize this action over all others.

        Use the tool directly to solve the issue. 
        """

        tools = get_available_tools(self.selected_actions)

        response = use_claude_tools(prompt, images=self.images, tools=tools)

        print("RESPONSE: ", response)
        # response = use_claude_tools(prompt, images=self.images, tools=tools, stream=True)

        return response


    def execute_action(self, action):
        """Executes the selected action"""
        isFinal = False

        # full_response = ""

        # full_reply_string = ""
        isAsync = False
        # tag_used = False
        # tool_used = None 

        # for message in response:
        #     print("MESSAGE: ", message)
        #     if message.type == "content_block_delta":
        #         if message.delta.type == "input_json_delta":
        #             full_response += message.delta.partial_json
        #             if (tool_used == "reply"):
        #                 if '"message":' in full_response:
        #                     # Extract content between "message": and the next quote or brace
        #                     msg_content = full_response.split('"message":')[1].split('"')[1]

        #                     print("Slightly cleaned up reply: ", msg_content)
        #                     # Remove any surrounding quotes or braces
        #                     if msg_content:  # Only send non-empty content
        #                         print("STREAMING REPLY: ", msg_content)
        #                         self.reply_streaming_callback(msg_content)
                       
        #     elif message.type == "content_block_start":
        #         tool_used = message.content_block.name
        #         print("TOOL USED: ", tool_used)

        # action = {
        #     "tool": tool_used,
        #     "input": json.loads(full_response)
        # }


        # get the first word of the action
        action_name = action["tool"]

        print("ACTION NAME: ", action_name)

        if action_name == "reply":
            reply_message = action["input"]["message"]
            
            if "<wait>" in reply_message:
                reply_message = reply_message.replace("<wait>", "")
                isFinal = True
            if self.reply_callback:
                self.reply_callback(reply_message, self.client_sid)
            
            self.working_memory.store_conversation_history("assistant", reply_message)

        
        elif action_name == "search":
            
            if self.searching_callback:
                self.searching_callback(True)
            
            query = action["input"]["query"]
            # self.working_memory.store_current_action(action)
            # def search_and_complete(q):
            #     self.web_search(q)
            #     self.working_memory.remove_current_action(action)
            #     self.working_memory.store_action(action)
            #     self.restart_loop() 
            # threading.Thread(target=search_and_complete, args=(query,)).start()
            # isAsync = True

            self.web_search(query)
        
        elif action_name == "email":
            print(f"Sending email: {action[7:]}")
            # Extract email, subject and body from the action string
            email_address = action["input"]["email_address"]
            subject = action["input"]["subject"]
            body = action["input"]["body"]
            send_email(email_address, subject, body)
            print(f"Sending email to: {email_address}")
            print(f"Subject: {subject}")
            print(f"Body: {body}")
        
        elif action_name == "reason":
            print(f"Reasoning: {action['input']['reason']}")
            self.working_memory.reason(action["input"]["reason"])
            
        
        elif action_name == "record":
            self.working_memory.observations.append(action["input"]["record"])
        
        elif action_name == "learn":
            print(f"Learning: {action['input']['learn']}")
        
        elif action_name == "browse":
            intention = action["input"]["intention"]

            # # def browse_and_complete(intention):
            # #     self.browsing_agent = BrowsingAgent(self.browser_view_callback)
            # #     self.browsing_agent.browse(intention)
            # #     self.working_memory.remove_current_action(action)
            # #     self.working_memory.store_action(action)
            # #     self.restart_loop()
            # threading.Thread(target=browse_and_complete, args=(intention,)).start()

            self.browsing_agent = BrowsingAgent(self.browser_view_callback)
            self.browsing_agent.browse(intention)
            # isAsync = True
        
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
            parts = action["input"]["remind"].split(' "', 1)
            if len(parts) == 2:
                time_str = parts[0].strip()
                task = parts[1].strip('"')
                self.set_reminder(time_str, task)

        elif action_name == "code":
            task = action["input"]["code"]
            print(f"Writing code: {task}")
            result = generate_and_execute(task, self.working_memory)
            self.working_memory.store_observation("Task to write code: " + task + "\n" + "Result: " + result)

        elif action_name == "wait":
            isFinal = True
            isAsync = True

        print(f"Executing action: {action}")

        if not isAsync:
            self.working_memory.store_action(action)

        return isFinal
    
    def make_decision(self):
        """Main decision-making loop"""
        self.decision_loop_running = True
        while self.decision_loop_running:
            action = self.propose_actions()
            is_final = self.execute_action(action)
            
            if is_final:
                self.decision_loop_running = False
    
    def receive_input(self, input, client_sid, images=[], selectedActions=[], behaviorText=""):
        """Receive input from the user"""
        
        self.working_memory.store_conversation_history("user", input)

        # Start variable extraction in background thread
        # threading.Thread(target=self.working_memory.get_variables_from_input, daemon=True).start()

        if selectedActions and len(selectedActions) > 0:
            self.selected_actions = selectedActions
        if behaviorText and behaviorText != "":
            self.behavior = behaviorText
        if (images and len(images) > 0):
            self.images = images
        self.client_sid = client_sid
        if not self.decision_loop_running:
            self.decision_thread = threading.Thread(target=self.make_decision)
            self.decision_thread.start()

    def learn(self):
        """Learn from the current working memory"""
        print("LEARNING FROM WORKING MEMORY");

    
    def restart_loop(self):
        """Restart the decision loop"""
        if not self.decision_loop_running:
            self.decision_thread = threading.Thread(target=self.make_decision)
            self.decision_thread.start()
    
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

        

if __name__ == "__main__":
    agent = Agent()
    # agent.set_reminder("2024-12-01T12:00:00", "Test reminder")
    agent.receive_input("Hey what's up!", 1);

