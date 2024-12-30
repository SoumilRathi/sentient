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
        self.pending_decision = False
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
        You are an intelligent agent designed to propose actions based on your current working memory and a set of available actions. Your primary goal is to quickly and efficiently select the most appropriate actions for any given situation.

        Here is your current working memory:
        <working_memory>
        {self.working_memory.print()}
        </working_memory>

        Your task is to propose and use the ideal action that you could potentially take at this step. Follow these steps:
        1. Do not generate new knowledge or information. Rely solely on the information provided in your working memory. You will have information both in the form of info dumps and in the form of knowledge segments.
        2. When using variables, check if they're available in your working memory. If not, determine the best way to obtain the needed information (e.g., asking the user, web search).
        3. For tasks with specific times or reminders, set a reminder instead of acting immediately.
        4. Ignore reminders from previous actions in your working memory. Only act on reminders prefixed with "REMINDER:" in your observations.
        5. Before acting on a reminder, verify that the corresponding action hasn't already been taken.
        6. Use the browse action for online service tasks requested by the user.
        7. Utilize existing knowledge in your working memory before performing a web search.
        8. After providing the user's desired output, use the wait action to pause for additional input.
        9. Perform only one web search at a time. Make use of existing search results before initiating a new search.
        10. Prioritize obtaining personal information from the user when necessary for task completion.
        11. Avoid repeating queries to the user. Wait for a response if information has been requested.
        13. IMPORTANT: Do not use placeholders for tools requiring specific inputs like email addresses; ask the user for the actual information first instead.
        14. IMPORTANT: If you have information / knowledge in your working memory already, do not use search again. 
        15. IMPORTANT: If you have already replied to the user, do not reply again with the same message. Wait for the user. Don't repeat the same reply multiple times.
        16. IMPORTANT: You can view the previous actions in your working memory. Don't repeat the same action multiple times. If you have made an action before, DO NOT meaninnglessly repeat it.
        17. IMPORTANT: If you have already sent the user an email about something, you do not need to send another one. Instead, you can reply to them informing them that the email has been sent.

        Before proposing an action, wrap your reasoning process inside <action_analysis> tags:

        1. Identify the current task or query from the working memory.
        2. List all possible actions that could be taken.
        3. Check for any reminders or time-sensitive tasks in the working memory.
        4. For each possible action:
            a. Evaluate it against the given constraints and instructions.
            b. Consider its relevance and priority in the current context.
            c. Analyze potential short-term and long-term outcomes.
            d. If the action requires information from the user, check if you have already asked for it. If so, do not ask again. If not, reply and ask the information first. 
        5. Determine the most appropriate action based on your evaluation.
        6. Double-check that the chosen action adheres to all constraints, especially tool usage and instruction following.
        7. Consider any potential consequences or follow-up actions that may be needed.
        8. IMPORTANT: Ensure that the agent does not require you to enter any placeholders for specific inputs. If it does, use reply to get the information instead.
        9. IMPORTANT: Ensure that the action is not a repeat of a previous action. If it is, do not propose it, do something else. 

        After your reasoning, provide a brief summary of your proposed action and then execute it using the appropriate tool. Your response should be concise and action-oriented.

        Example output structure:

        <action_analysis>
        [Your step-by-step reasoning process]
        </action_analysis>

        Proposed Action: [Brief description of the chosen action]

        [Execute the action using the appropriate tool]

        Remember to prioritize quick and efficient responses while strictly adhering to the given instructions and constraints.
        """

        tools = get_available_tools(self.selected_actions)

        print("Checkpoint 2")

        response = use_claude_tools(prompt, images=self.images, tools=tools)

        print("Checkpoint 3")

        print("RESPONSE: ", response)
        # response = use_claude_tools(prompt, images=self.images, tools=tools, stream=True)

        return response


    def execute_action(self, action):
        """Executes the selected action"""
        isFinal = False

        isDecisionNeeded = False
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
        
        action_to_store = action

        print("ACTION NAME: ", action_name)

        if action_name == "reply":
            reply_message = action["input"]["message"]
            
            if "<wait>" in reply_message:
                reply_message = reply_message.replace("<wait>", "")
                isFinal = True
            if self.reply_callback:
                self.reply_callback(reply_message, self.client_sid)

            action_to_store = "Reply successfully sent to user: " + reply_message

            print("WORKING MEMORY BEFORE TAKING THE ACTION: ", self.working_memory.print())
            
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

            action_to_store = "Searched for: " + query

            self.web_search(query)
        
        elif action_name == "email":
            # Extract email, subject and body from the action string
            email_address = action["input"]["email_address"]
            subject = action["input"]["subject"]
            body = action["input"]["body"]

            action_to_store = "Email sent to " + email_address + " with subject " + subject;
            send_email(email_address, subject, body)
            print(f"Email successfully sent to: {email_address}")
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
            time = action["input"]["time"]
            message = action["input"]["message"]
            single_shot = action["input"]["single_shot"]
            action_to_store = "Reminder successfully set for: " + time + " with message: " + message;
            self.set_reminder(time, message, single_shot)

        elif action_name == "code":
            task = action["input"]["code"]
            print(f"Writing code: {task}")
            result = generate_and_execute(task, self.working_memory)
            self.working_memory.store_observation("Task to write code: " + task + "\n" + "Result: " + result)

        elif action_name == "wait":
            if not self.pending_decision:
                isFinal = True
                isAsync = True
            action_to_store = "Waiting for user input"

        print(f"Executing action: {action}")

        self.working_memory.store_action(action_to_store)

        return isFinal
    
    def make_decision(self):
        """Main decision-making loop"""
        print("Checkpoint 1: Starting decision loop")
        self.decision_loop_running = True
        while self.decision_loop_running:
            self.pending_decision = False
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
            print("Starting decision loop")
            self.decision_thread = threading.Thread(target=self.make_decision)
            print("thread created")
            self.decision_thread.start()
            print("thread started")
        else: 
            self.pending_decision = True
            print("Decision loop is already running")

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
            
            # # Check for due reminders
            # for reminder_time in reminder_times:
            #     print("REMINDER TIME: ", reminder_time)
            #     if current_time >= reminder_time:
            #         reminders_to_process.extend(self.reminders[reminder_time])
            #         del self.reminders[reminder_time]
            
            # # Process due reminders
            # for reminder in reminders_to_process:
            #     print("PROCESSING REMINDER: ", reminder)
            #     self.process_reminder(reminder)


            # TODO: Add a check for reminders that are due
            
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
    
    def set_reminder(self, time, message, single_shot):
        """Set a reminder for a specific time"""

        print("Sets a reminder for: ", time, message, single_shot   )
        try:
            reminder_time = datetime.fromisoformat(time)
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
            print(f"Invalid datetime format: {time}")
            return False

        

if __name__ == "__main__":
    agent = Agent()
    # agent.set_reminder("2024-12-01T12:00:00", "Test reminder")
    agent.receive_input("Hey what's up!", 1);

