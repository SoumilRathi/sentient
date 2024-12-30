import os
import time
import json
import base64
from browserbase import Browserbase
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from helper_functions import use_claude, use_deepseek
from PIL import Image, ImageDraw, ImageFont
import io
import threading
from threading import Lock
load_dotenv()

BROWSERBASE_API_KEY = os.environ["BROWSERBASE_API_KEY"]
BROWSERBASE_PROJECT_ID = os.environ["BROWSERBASE_PROJECT_ID"]

bb = Browserbase(api_key=BROWSERBASE_API_KEY)



session = bb.sessions.create(
        project_id=BROWSERBASE_PROJECT_ID,
        proxies=True,
    )

debug_urls = bb.sessions.debug(session.id)
debug_connection_url = debug_urls.debugger_fullscreen_url

print("BROWSER VIEW URL: ", debug_connection_url)

cursor_location = {
    "x": 0,
    "y": 0,
}

current_browser_screenshot = None
is_latest_screenshot = False
did_page_change = True
last_page_image = None
current_element = None #this is the element the mouse is currently hovering over
active_element = None #this is the element that is currently focused on
is_input_field = None #is the current element an input field?

def get_browser_screenshot(page):
    
    print("\n\n\n\nGetting browser screenshot\n")

    start = time.time()

    # Take screenshot and encode as base64
    global did_page_change
    global last_page_image

    if did_page_change:
        screenshot_bytes = page.screenshot(timeout=120000)
        last_page_image = screenshot_bytes
    else:
        screenshot_bytes = last_page_image


    first = time.time()

    print("1: ", first - start)
    
    # Open screenshot and cursor image
    image = Image.open(io.BytesIO(screenshot_bytes))
    cursor = Image.open("browsing/images/cursor.png")

    second = time.time()

    print("2: ", second - first)
    
    # Resize cursor to be 3.5x smaller
    cursor_width = int(cursor.width / 7.5)
    cursor_height = int(cursor.height / 7.5)
    cursor = cursor.resize((cursor_width, cursor_height))
    
    # Calculate position to paste cursor (centered on cursor location)
    cursor_x = int(cursor_location["x"])
    cursor_y = int(cursor_location["y"])

    print("Cursor location: ", cursor_x, cursor_y)

    third = time.time()

    print("3: ", third - second)
    
    # Paste cursor onto screenshot
    image.paste(cursor, (cursor_x, cursor_y), cursor if cursor.mode == 'RGBA' else None)

    # Create drawing context and font
    draw = ImageDraw.Draw(image)
    try:
        # Use a smaller font size to match the reference image
        font = ImageFont.truetype("Arial", 12)
    except:
        font = ImageFont.load_default()

    width, height = image.size

    fourth = time.time()

    print("4: ", fourth - third)

    # Draw the axes labels (X and Y) in top left corner
    draw.text((0, 0), "Y", fill='black', font=font)
    draw.text((15, 0), "X", fill='black', font=font)

    # Draw vertical grid lines and labels every 50 pixels
    for x in range(0, width, 50):
        # Draw vertical line
        draw.line([(x, 0), (x, height)], fill='black', width=1)
        
        # Draw x-axis label at top
        if x > 0:  # Skip 0 since we have X/Y labels there
            draw.text((x, 0), str(x), fill='black', font=font)

    # Draw horizontal grid lines every 50 pixels
    for y in range(0, height, 50):
        # Draw horizontal line
        draw.line([(0, y), (width, y)], fill='black', width=1)
        
        # Draw y-axis label on left
        if y > 0:  # Skip 0 since we have X/Y labels there
            draw.text((0, y), str(y), fill='black', font=font)

    fifth = time.time()

    print("5: ", fifth - fourth)

    # Convert to bytes and encode as base64
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    screenshot_bytes = img_byte_arr.getvalue()
    # Save and encode
    image.save("screenshot.png")
    screenshot_base64 = base64.b64encode(screenshot_bytes).decode()

    end = time.time()

    print("Time taken for screenshot: ", end - fifth)

    print("Total time taken: ", end - start, "\n\n\n")

    return {"image": f"data:image/png;base64,{screenshot_base64}", "text": "Current browser screenshot"}


with sync_playwright() as playwright:
    chromium = playwright.chromium
    browser = chromium.connect_over_cdp(session.connect_url)
    context = browser.contexts[0]
    page = context.pages[0]

    # Set longer timeout for proxy connections
    page.set_default_navigation_timeout(120000)

    global opened_page
    opened_page = "None"

    goal = "Go to the Plus section of Cambridge Dictionary, find Image quizzes and do an easy quiz about Animals and tell me your final score"

    def operate_on_goal(goal):
        "Recursively picks tactical actions to operate on the goal"

        final = False

        global opened_page


        actions_history = []

        while not final:
            prompt =  f"""
            You are an intelligent browser agent that can operate a browser to achieve the overall task that the user has given you.

You are in turn commanding a second agent that can take actions on the browser. Your job is to concisely tell them exactly what has to be done from a particular page. These effectively mean opening a page or deciding the goal for this page

If no page is currently open, you will have to open a particular page. If you choose to do so, you have to format it by saying "OPEN:[website_url]" because your second agent doesn't have access to opening pages. Ensure that you just output the base website url, nothing else. Also ensure that you give the full url, including the protocol (https://)

If a page IS already open, you have to tell your subagent precisely what has to be done on that page. You only get one chance to decide the goal for your subagent, after which they will take over and conduct actions to complete your command. 

Instructions:
1. Try to avoid signing up/in unless specifically asked to do so. 


Output the page goal in natural language, as if telling the subagent what the goal is. Don't try to output specific actions, instead output the overall goal from this page. Be concise; single sentence

You have access to your current history as well as the information you currently possess. If the task is finished, please just output FINISH instead.

# INFORMATION
## Action History
{actions_history if len(actions_history) > 0 else "No actions yet"}
## Current browser information
### Opened page: {opened_page}
## Knowledge
No knowledge yet
Task: {goal}
            """

            # screenshot = get_browser_screenshot(page)
            response = use_claude(prompt, sonnet=True);

            print("Response: ", response)

            if response.startswith("OPEN:"):
                response = response.split(" ")[0]
                url = response[5:].strip()
                page.goto(url)
                opened_page = url
                actions_history.append(f"Opened page: {opened_page}")
            else:
                tactical_action = response
                actions_history.append(tactical_action)

                if tactical_action == "FINISH":
                    final = True
                
                else:
                    print("Tactical action: ", tactical_action)
                    operate_on_tactical_action(tactical_action)


        return response

    def operate_on_tactical_action(action):
        "Recursively picks specific actions to operate on the tactical action"

        action_history = []
        final = False

        while not final:

            global opened_page
            prompt = f"""
You are a browser agent who has been commanded to carry out a task on a particular browser page.

Your job is to command another agent, who will physically carry out specific actions on the browser to complete your order. 

Specific actions are element-level actions, which means everything to do with a particular element on the page. The action should be such that any interaction to do with the particular element should be covered by your action. Eg. A full search, a selection, etc. 

ENSURE that a single one of your actions does not require interaction with more than one element. That will be the next action.

Instructions:
1. If you see a popup (for example, a cookie consent popup), you should first try to close it by clicking on the close button. If you cannot find the close button, you should try to scroll the page to make it go away. If that doesn't work, you should try to click anywhere else on the page to make it go away.
2. Try to avoid signing up/in unless specifically asked to do so. 

Your job, given the overall task to complete on the page, is to give an order for an element-level action to your sub-agent. 

If done with the task, output FINISH

Output the next command to the detailed agent in natural language; be concise; only output the command

# INFORMATION

## Action History
{action_history if len(action_history) > 0 else "No actions yet"}

## Current browser information
### Opened page: {opened_page}

## Knowledge
No knowledge yet

Task: {action}
        """

            global is_latest_screenshot
            global current_browser_screenshot
            if is_latest_screenshot:
                screenshot = current_browser_screenshot
            else:
                screenshot = get_browser_screenshot(page)
                is_latest_screenshot = True
                current_browser_screenshot = screenshot

            response = use_claude(prompt, images=[screenshot], sonnet=True)

            print("Specific action response: ", response)

            if response == "FINISH":
                final = True
            else:
                action_history.append(response)

                operate_on_specific_action(response)

    def operate_on_specific_action(action):
        "Recursively picks detailed actions to operate on the specific action"

        action_history = []

        global active_element
        final = False
        global opened_page

        while not final:

            prompt = f"""
            You are a browser agent who has been commanded to carry out a task on a particular browser page.
Your job is to divide your overall goal and take physical actions on the browser.
# Specific Browser Instructions
1. For any element, try describing it by its label, text, or placeholder, if visible. If not, describe it well by what it is.
2. If you want to enter text in a specific box / scroll a specific section, you should ensure it is active first by moving the mouse and clicking there. Assume any action in your history as successful
3. If a page should have a particular element, but you cannot find it, you can try scrolling down to see if it exists.
# Available Actions
1. Click -> Clicks the mouse at the current cursor location. 
2. Enter "Text" -> Enters the given text into the current input field. Only take this action if you have currently focused on an input field. Note that this does not automatically submit / press enter. You will have to do that separately
3. MouseDown -> Presses the mouse button down
4. MouseUp -> Releases the mouse button
5. MouseMove "Element" -> Moves the mouse to the given element 
6. Scroll "Amount" -> Scrolls the page by the given amount. Please note that your mouse should be above the scrollable element when you do this. This amount can be negative or positive.
7. KeyDown <KEY> -> Presses the given key 
8. Wait -> Waits for 3 seconds for the page to load. If you just clicked something that would lead to a page change, select this action before picking anything else.
9. FINISH (only do this if the task is finished)
Just output the immediate next action; explanation unnecessary. 
Format your output as follows:
<final>
[action here]
</final>
# INFORMATION
## Action History
{action_history if len(action_history) > 0 else "No actions yet"}
## Current browser information
### Active Element
{active_element if active_element is not None else "None"}
### Opened page:{opened_page}
## Knowledge
No knowledge yet
Task: {action}
        """

            global is_latest_screenshot
            global current_browser_screenshot
            if is_latest_screenshot:
                screenshot = current_browser_screenshot
            else:
                screenshot = get_browser_screenshot(page)
                is_latest_screenshot = True
                current_browser_screenshot = screenshot

            response = use_claude(prompt, images=[screenshot], sonnet=True)

            response = response.split("<final>")[1].split("</final>")[0].strip()

            action_history.append(response)

            if response == "FINISH":
                final = True
            else:
                execute_detailed_action(response)

            print("Detailed action chosen: ", response)

    def execute_detailed_action(action):
        "Executes the detailed action on the browser"

        print("Executing detailed action: ", action)

        global current_element
        global active_element
        global did_page_change
        global cursor_location
        global is_latest_screenshot

        if (action.startswith("MouseMove")):
            
            element_to_move_to = action[10:].strip()
            if element_to_move_to.startswith('"'):
                element_to_move_to = element_to_move_to[1:]
            if element_to_move_to.endswith('"'):
                element_to_move_to = element_to_move_to[:-1]

            # try to find the element in more direct ways first. 

            print("Element to move to: ", element_to_move_to)
            # to find the element, we can give the entire html of the page to an LLM and ask it to output the element that matches it

            element = locate_element(element_to_move_to, page)

            print("Element found: ", element)

            bbox = element.bounding_box()

            print("Bounding box: ", bbox)

            cursor_location = {
                "x": bbox['x'] + bbox['width'] / 2,
                "y": bbox['y'] + bbox['height'] / 2
            }

            current_element = element_to_move_to

            print("Cursor location: ", cursor_location)

            page.mouse.move(cursor_location["x"], cursor_location["y"])

            did_page_change = False
            is_latest_screenshot = False

        elif (action.startswith("Click")):
            page.mouse.down()
            page.mouse.up()

            active_element = current_element
            
            did_page_change = True
            is_latest_screenshot = False


        elif (action.startswith("Enter")):
            text = action[6:].strip()
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
            page.keyboard.type(text)

            did_page_change = False
            is_latest_screenshot = True

        elif (action.startswith("KeyDown")):
            key = action[8:].strip().replace("<", "").replace(">", "")
            if key == "ENTER":
                key = "Enter"
            page.keyboard.press(key)

            if key == "Enter" :
                did_page_change = True
                is_latest_screenshot = False

        elif (action.startswith("Wait")):
            time.sleep(3)
            did_page_change = True
            is_latest_screenshot = False



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


    operate_on_goal(goal)