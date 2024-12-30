from playwright.sync_api import Playwright, sync_playwright
from browserbase import Browserbase
import os
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image, ImageDraw
import io
import time
import json
import asyncio

load_dotenv()

BROWSERBASE_API_KEY = os.environ["BROWSERBASE_API_KEY"]
BROWSERBASE_PROJECT_ID = os.environ["BROWSERBASE_PROJECT_ID"]

bb = Browserbase(api_key=BROWSERBASE_API_KEY)


def locate_element(element_to_locate, page):
    "Locates the element to move to"

    try:
        element = page.get_by_text(element_to_locate, exact=True).first
        if element.is_visible():
            return element
    except:
        pass

    try:
        element = page.get_by_placeholder(element_to_locate).first
        if element.is_visible():
            return element
    except:
        pass

    html = page.content()

    # Chunk HTML into sections of 20000 characters
    chunk_size = 20000
    html_chunks = []
    
    # Split HTML into chunks while preserving tag structure
    current_chunk = ""
    buffer = ""
    
    for char in html:
        buffer += char
        
        if char == '>':
            if len(current_chunk) + len(buffer) >= chunk_size:
                html_chunks.append(current_chunk)
                current_chunk = buffer
            else:
                current_chunk += buffer
            buffer = ""
                
    # Add final chunk
    if current_chunk or buffer:
        html_chunks.append(current_chunk + buffer)


    for chunk in html_chunks:
        prompt = f"""
        You are an LLM that can parse HTML and find the element that matches the description given to you.

        Respond with the HTML of the element that matches the description given to you.

        HTML: {chunk}
        Description: {element_to_locate}

        If the element is not present in the given HTML chunk, output NA for all fields.

        Please output your final response in the following JSON format: (if any of the fields are not present, just write NA). Ensure that you output the entire JSON object, and nothing else
        {{
            "element": "<HTML of the element>",
            "id": "<id of the element>",
            "label": "<label for the element>",
            "placeholder": "<placeholder for the element>",
            "text": "<text for the element>"
        }}
        """

        response = use_deepseek(prompt)

        print("Response: ", response)

        # Find the JSON response between curly braces
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_response = response[json_start:json_end]
        else:
            json_response = "{}"

        print("JSON response: ", json_response)

        # Parse the JSON response
        element_data = json.loads(json_response)

        print("Element data: ", element_data)

        if (element_data["element"] == "NA" and element_data["id"] == "NA" and element_data["placeholder"] == "NA" and element_data["label"] == "NA" and element_data["text"] == "NA"):
            # The element is absolutely not in this chunk
            continue

        if (element_data["id"] != "NA"):
            element = page.locator(f'id={element_data["id"]}').first
        if (element_data["placeholder"] != "NA"):
            element = page.get_by_placeholder(element_data['placeholder']).first
        elif (element_data["label"] != "NA"):
            element = page.get_by_label(element_data['label']).first
        elif (element_data["text"] != "NA"):
            element = page.get_by_text(element_data['text']).first

        return element

def run(playwright: Playwright) -> None:
    """Run browser automation session using Playwright and Browserbase."""
    # Create a session on Browserbase with proxy and stealth settings
    session = bb.sessions.create(
        project_id=BROWSERBASE_PROJECT_ID,
        proxies=True,
    )

    debug_urls = bb.sessions.debug(session.id)
    debug_connection_url = debug_urls.debugger_fullscreen_url

    print("BROWSER VIEW URL: ", debug_connection_url)

    # Connect to the remote session
    chromium = playwright.chromium
    browser = chromium.connect_over_cdp(session.connect_url)
    context = browser.contexts[0]
    page = context.pages[0]

    # Set longer timeout for proxy connections
    page.set_default_navigation_timeout(60000)

    try:
        # Execute Playwright actions on the remote browser tab
        page.goto("https://www.coursera.org/search?query=Artificial%20Intelligence%20for%20Healthcare")

        # time.sleep(2)

        # print("Doing the element movement now")

        # element = locate_element("AI in Healthcare", page)

        # print("Element: ", element)

        # print("Element html: ", element)

        # bbox = element.bounding_box()

        # cursor_location = {
        #     "x": bbox['x'] + bbox['width'] / 2,
        #     "y": bbox['y'] + bbox['height'] / 2
        # }

        # print("Cursor location: ", cursor_location)

        # page.mouse.move(cursor_location["x"], cursor_location["y"])

        # time.sleep(3)

        # print("Clicking the element now")

        # print("Pages before: ", context.pages)

        # page.mouse.click(cursor_location["x"], cursor_location["y"], button="middle")

        # time.sleep(5)

        # print("Pages after: ", context.pages)

        time.sleep(120)

        # see what happens
        

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        page.close()
        browser.close()

    print(f"Done! View replay at https://browserbase.com/sessions/{session.id}")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
