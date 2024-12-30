import re
import anthropic
import os
from postmarker.core import PostmarkClient
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


all_tools = [
    {
        "name": "reply",
        "description": "Talk to the user / reply to the input. Note that replying to the user is final, and the decision loop will end after this action is selected. This means that you should only select it once you have finished the task, or when you need more user input to continue the task. ",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to reply with. Please note that the reply message should be in **markdown** format."
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "search", 
        "description": "Search the web for information. This will be used to answer questions or retrieve information that is not available in your current working memory. Please note that this action is meant to be used to augment your knowledge, so use it only when the knowledge you need for a task is not available in your current working memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The query to search the web with"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "browse",
        "description": "Control a browser to complete a task. This will be used to use the browser on behalf the user to complete a task. Please understand that this action is for browsing and taking actions on the web, and not for searching the web for information. That is what the search action is for.",
        "input_schema": {
            "type": "object",
            "properties": {
                "intention": {
                    "type": "string",
                    "description": "The intention to browse the web with"
                }
            },
            "required": ["intention"]
        }
    },
    {
        "name": "email",
        "description": "Send an email to a specified email address. This will be used if you need to send an email to a user. Please do not use this unless you have specifically been asked to send an email. Please note that the body of the email should be in html format. Ensure that the body is always in html format, as it will present an error otherwise.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email_address": {
                    "type": "string",
                    "description": "The email address to send the email to"
                },
                "subject": {
                    "type": "string",
                    "description": "The subject of the email"
                },
                "body": {
                    "type": "string",
                    "description": "The body of the email, in html format. Start with <html> and end with </html>"
                }
            },
            "required": ["email_address", "subject", "body"]
        }
    },
    {
        "name": "wait",
        "description": "Wait until you next get asked to do something. This should be used when there's nothing else you have been asked to do",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string", 
                    "description": "The reason for waiting"
                }
            },
            "required": ["reason"]
        }
    },
    {
        "name": "remind",
        "description": "Set a reminder for a specific time with a specific message. This will be used if you need to schedule tasks for yourself to do for the user at a later time",
        "input_schema": {
            "type": "object",
            "properties": {
                "time": {
                    "type": "string", 
                    "description": "The time to set the reminder for in ISO format"
                },
                "message": {
                    "type": "string", 
                    "description": "The message to set the reminder for. This is the task that you will be reminded to do"
                },
                "single_shot": {
                    "type": "boolean", 
                    "description": "Whether this is a single shot reminder or a recurring reminder. If it is a recurring reminder, you will be reminded every day at the same time"
                }
            },
            "required": ["time", "message", "type"]
        }
    },
]


def get_available_tools(selected_actions):
    return all_tools

# def get_available_actions(selected_actions):
#     "This function takes in the list of actions avaiable to the agent and gets a string that it can add to the prompt"

#     actions_instructions = load_file("actions.txt")

#     available_actions = []
#     for action in grounding_actions:
#         available_actions.append(f"{action['action']} -> {action['description']}")
    
#     grounding_actions_str = "\n".join(available_actions)
    
#     # Replace the placeholder in the actions instructions
#     actions_text = actions_instructions.replace("{{grounding_actions}}", grounding_actions_str)
    
#     return actions_text


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

def process_images(images):
    processed_images = []
    for image_data in images:
        image = image_data['image']
        text = image_data['text']
        if image.startswith('data:image/'):
            image_type, image_data = image.split(',', 1)
            media_type = image_type.split(';')[0].split(':')[1]
            processed_images.append({
                "image": {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    }
                },
                "text": text
            })
    return processed_images

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def use_claude(user_prompt, system_prompt=None, temperature=1, json=False, tools=[], images=[], sonnet=False):
    message_params = {
        "model": "claude-3-5-sonnet-20240620" if sonnet else "claude-3-5-haiku-20241022",
        "max_tokens": 1024,
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
    if images and len(images) > 0:
        processed_images = process_images(images)
        for i, image_data in enumerate(processed_images):
            content.append(image_data["image"])
            if image_data["text"]:
                content.append({"type": "text", "text": f"Description for Image {i+1}: {image_data['text']}"})

    content.append({"type": "text", "text": user_prompt})
    message_params["messages"][0]["content"] = content
    
    message = client.messages.create(**message_params)

    return message.content[0].text

ds_client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
def use_deepseek(prompt):
    
    response = ds_client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": prompt},
        ],
        stream=False
    )

    return response.choices[0].message.content


def use_claude_tools(user_prompt, system_prompt=None, temperature=1, json=False, tools=[], images=[], stream=False):
    message_params = {
        # "model": "claude-3-5-haiku-20241022",
        "model": "claude-3-5-sonnet-20240620",
        "max_tokens": 1024,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": []
            }
        ],
        "tools": tools,
    }
    
    if system_prompt is not None:
        message_params["system"] = system_prompt

    content = []
    if images and len(images) > 0:
        processed_images = process_images(images)
        for i, image_data in enumerate(processed_images):
            content.append(image_data["image"])
            if image_data["text"]:
                content.append({"type": "text", "text": f"Description for Image {i+1}: {image_data['text']}"})

    content.append({"type": "text", "text": user_prompt})
    message_params["messages"][0]["content"] = content


    message = client.messages.create(**message_params)

    print("MESSAGE: ", message, "with prompt: ", user_prompt)

    for content_block in message.content:
        if content_block.type == "tool_use":
            response = {
                "tool": content_block.name,
                "input": content_block.input,
            }

    print("RESPONSE: ", response)

    return response

    # if stream:
    #     print("STREAMING MESSAGE PARAMS: ", message_params)
    #     with client.messages.stream(**message_params) as stream:
    #         for message in stream:
    #             yield message
    # else:
    #     print("MESSAGE PARAMS: ", message_params)
        

    

def use_claude_stream(user_prompt, system_prompt=None, temperature=1, json=False, tools=[], images=[]):
    message_params = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 1024,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": []
            }
        ],
    }
    
    if system_prompt is not None:
        message_params["system"] = system_prompt

    if tools is not None and len(tools) > 0:
        message_params["tools"] = tools

    content = []
    if images and len(images) > 0:
        processed_images = process_images(images)
        for i, image_data in enumerate(processed_images):
            content.append(image_data["image"])
            if image_data["text"]:
                content.append({"type": "text", "text": f"Description for Image {i+1}: {image_data['text']}"})

    content.append({"type": "text", "text": user_prompt})
    message_params["messages"][0]["content"] = content
    
    with client.messages.stream(**message_params) as stream:
        for message in stream:

            if message.type == "content_block_delta":
                yield message.delta.text


postmark = PostmarkClient(server_token=os.getenv("POSTMARK_API_KEY"))

def send_email(email_address, subject, body):
    
    postmark.emails.send(
        From='soumil@skillpool.tech',
        To=email_address,
        Subject=subject,
        HtmlBody=body
    )



if __name__ == "__main__":
    print(use_deepseek("What is the weather in San Francisco?"))