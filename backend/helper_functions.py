import re
import anthropic
import os
from postmarker.core import PostmarkClient
from dotenv import load_dotenv
load_dotenv()


grounding_actions = [
    {
        "name": "reply",
        "description": "Talk to the user / reply to the input. Note that replying to the user is final, and the decision loop will end after this action is selected. This means that you should only select it once you have finished the task, or when you need more user input to continue the task. Please note that the reply message should be in markdown format.",
        "action": "reply <MESSAGE>"
    },
    {
        "name": "search", 
        "description": "Search the web for information. This will be used to answer questions or retrieve information that is not available in your current working memory. Please note that this action is meant to be used to augment your knowledge, so use it only when the knowledge you need for a task is not available in your current working memory.",
        "action": "search <QUERY>"
    },
    {
        "name": "browse",
        "description": "Browse the web for information. This will be used if you want to take any action that requires you to use the browser",
        "action": "browse <INTENTION>"
    },
    {
        "name": "email",
        "description": "Send an email to a specified email address. This will be used if you need to send an email to a user. Please do not use this unless you have specifically been asked to send an email. Please note that the body of the email should be in html format.",
        "action": 'email "<EMAIL_ADDRESS>" "<SUBJECT>" """<BODY>"""'
    }
]


def get_available_actions(selected_actions):
    "This function takes in the list of actions avaiable to the agent and gets a string that it can add to the prompt"

    actions_instructions = load_file("actions.txt")

    selected_actions = ["reply", "search", "email"]

    available_actions = []
    for action in grounding_actions:
        if action["name"] in selected_actions:
            available_actions.append(f"{action['action']} -> {action['description']}")
    
    grounding_actions_str = "\n".join(available_actions)
    
    # Replace the placeholder in the actions instructions
    actions_text = actions_instructions.replace("{{grounding_actions}}", grounding_actions_str)
    
    return actions_text


def sort_actions_by_priority(actions):
        actions_with_priorities = []
        
        for action in actions:
            # Use regex to extract the number at the end of the action, if it exists
            match = re.search(r'(\d+)', action)
            if match:
                priority = int(match.group(1))
                actions_with_priorities.append((action, priority))
        
        # Sort actions based on the numerical values in descending order
        sorted_actions = sorted(actions_with_priorities, key=lambda x: x[1], reverse=True)
        
        # Return the action with the highest priority if available
        return sorted_actions[0][0] if sorted_actions else None


def load_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()



client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def use_claude(user_prompt, system_prompt=None, temperature=1, json=False, tools=[], images=[]):
    message_params = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 8192,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": []
            }
        ]
    }
    
    if system_prompt is not None:
        message_params["system"] = system_prompt

    if tools is not None and len(tools) > 0:
        message_params["tools"] = tools

    content = []
    # if images:
    #     processed_images = process_images(images)
    #     for i, image_data in enumerate(processed_images):
    #         content.append(image_data["image"])
    #         if image_data["text"]:
    #             content.append({"type": "text", "text": f"Description for Image {i+1}: {image_data['text']}"})

    content.append({"type": "text", "text": user_prompt})
    message_params["messages"][0]["content"] = content
    
    message = client.messages.create(**message_params)

    return message.content[0].text


postmark = PostmarkClient(server_token=os.getenv("POSTMARK_API_KEY"))

def send_email(email_address, subject, body):
    
    postmark.emails.send(
        From='soumil@skillpool.tech',
        To=email_address,
        Subject=subject,
        HtmlBody=body
    )