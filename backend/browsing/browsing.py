import os
import time
import json
import base64
from browserbase import Browserbase
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from helper_functions import use_claude

load_dotenv()

BROWSERBASE_API_KEY = os.environ["BROWSERBASE_API_KEY"]
BROWSERBASE_PROJECT_ID = os.environ["BROWSERBASE_PROJECT_ID"]

bb = Browserbase(api_key=BROWSERBASE_API_KEY)

class BrowsingAgent:
    def __init__(self, callback):
        self.playwright = None
        self.browser = None
        self.page = None
        self.browser_view_callback = callback
        self.client_sid = None
        self.actions = []
        self.current_screenshot = None
        self.cursor_location = {
            "x": 0,
            "y": 0
        }

    def start_session(self):
        # Create session with proxies and stealth mode settings
        session = bb.sessions.create(
            project_id=BROWSERBASE_PROJECT_ID,
            proxies=True,
        )
        debug_urls = bb.sessions.debug(session.id)
        debug_connection_url = debug_urls.debugger_fullscreen_url

        self.browser_view_callback(debug_connection_url)
        print("BROWSER VIEW URL: ", debug_connection_url)

        chromium = self.playwright.chromium
        self.browser = chromium.connect_over_cdp(session.connect_url)
        context = self.browser.contexts[0]
        self.page = context.pages[0]

        # Set longer timeout for proxy connections
        self.page.set_default_navigation_timeout(60000)


    def get_browser_screenshot(self):

        # Take screenshot and encode as base64
        screenshot_bytes = self.page.screenshot()

        # Create PIL Image from screenshot bytes
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Open screenshot and cursor image
        image = Image.open(io.BytesIO(screenshot_bytes))
        cursor = Image.open("browsing/images/cursor.png")
        
        # Resize cursor to be 3.5x smaller
        cursor_width = int(cursor.width / 7.5)
        cursor_height = int(cursor.height / 7.5)
        cursor = cursor.resize((cursor_width, cursor_height))
        
        # Calculate position to paste cursor (centered on cursor location)
        cursor_x = int(self.cursor_location["x"])
        cursor_y = int(self.cursor_location["y"])

        print("Cursor location: ", cursor_x, cursor_y)
        
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

        # Convert to bytes and encode as base64
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        screenshot_bytes = img_byte_arr.getvalue()
        # Save and encode
        image.save("screenshot.png")
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode()

        return {"image": f"data:image/png;base64,{screenshot_base64}", "text": "Current browser screenshot"}

    def pick_action(self, task):
        prompt = f"""
        You are a browsing agent. You have been given a main task to complete. 
        You also have information about the current state of the browser. 
        You have also been given a list of available actions.  
        You also have a history of actions you have taken, and observations you have made during this course.
        Your job is to pick the next action to take. 

        # Instructions
        
        1. When you want to click on something to highlight it, ensure that the tip of the cursor is inside the element you want to click on.
        2. The screenshot you have been provided with the image is the most updated state of the browser. If you have taken an action that is not reflected in the screenshot, something went wrong.

        # Current Browser State

        Current URL: {self.page.url}
        Current Page Title: {self.page.title}

        # Task
        {task}
        
        # Actions available to you
        
        ## Browser Actions
        1. open <URL> -> Open a new tab with the given URL.
        2. close -> Close the current tab.
        3. switch <TAB_INDEX> -> Switch to the tab at the given index.
        4. back -> Go back to the previous page.
        5. forward -> Go forward to the next page.
        6. refresh -> Refresh the current page.
        7. wait <x> -> Wait for x seconds. Please note that this can never ever be longer than 10 seconds - no loading after 10 seconds probably means something's wrong. Default to 5.

        ## Control Actions
        1. move <row_number> <column_number> -> Move the mouse cursor to the given coordinates.
        2. click -> Click the mouse.
        3. scroll <amount> -> Scroll the page by the given amount. Please note that your mouse should be above the scrollable element when you do this. This amount can be negative or positive.

        ## Data Actions
        1. enter "TEXT" -> Enter the given text into the current input field. Only take this action if you have currently focused on an input field.
        2. delete <x> -> Delete the last x characters typed.
        3. key <KEY> -> Press the given key.

        ## System Actions
        1. finish -> Finish the current task. This will end the decision loop, and return control back to the user. This should be used when you think you have completed the task, or when you are sure that you cannot continue the task further. Typically, you can use this action after you have styled the code and think that it is close enough to the desired output.
        2. give control -> Temporarily give control back to the user. This is when there are certain things that you cannot do. Definitely enter this if you have to enter a password anywhere, 
        
        # Actions taken previously
        {self.actions}

        Ensure that you output your final action in the following format:
        <final>
        [action here]
        """

        print("PROMPT: ", prompt)
        
        try:
            screenshot = self.get_browser_screenshot()
            response = use_claude(prompt, images=[screenshot], sonnet=True)
        except Exception as e:
            print("ERROR GETTING BROWSER SCREENSHOT: ", e)
            response = use_claude(prompt)
    

        print("RESPONSE: ", response)

        response = response.split("<final>")[1].split("</final>")[0].strip()
        return response

    def execute_action(self, action):
        self.actions.append(action)

        if action.startswith("open"):
            print("Opening URL: ", action.split(" ")[1])
            self.page.goto(action.split(" ")[1], timeout=60000, wait_until="domcontentloaded")
            print("we're done!")
        elif action.startswith("close"):
            self.page.close()
        elif action.startswith("switch"):
            self.page.switch_to_tab(int(action.split(" ")[1]))
        elif action.startswith("back"):
            self.page.go_back()
        elif action.startswith("forward"):
            self.page.go_forward()
        elif action.startswith("refresh"):
            self.page.reload()
        elif action.startswith("move"):
            row = (action.split(" ")[1])
            column = (action.split(" ")[2])

            # Clean x and y coordinates of any non-numeric characters except minus sign
            row = int(''.join(c for c in row if c.isdigit() or c == '-'))
            column = int(''.join(c for c in column if c.isdigit() or c == '-'))

            self.page.mouse.move(row, column)
            self.cursor_location = {
                "x": row,
                "y": column
            }
        elif action.startswith("click"):
            self.page.mouse.down()
            self.page.mouse.up()
        elif action.startswith("scroll"):
            self.page.mouse.wheel(int(action.split(" ")[1]))
        elif action.startswith("enter"):
            text = action[6:].strip()
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
                for char in text:
                    self.page.keyboard.press(char)
        elif action.startswith("delete"):
            self.page.keyboard.press("Backspace", count=int(action.split(" ")[1]))
        elif action.startswith("key"):
            self.page.keyboard.press(action.split(" ")[1])
        elif action.startswith("wait"):
            time.sleep(int(action.split(" ")[1]))
        elif action.startswith("finish"):
            return True
        
        return False
        
    def browse(self, task):
        print("BrowsingAgent browsing for task: ", task)

        with sync_playwright() as playwright:
            self.playwright = playwright
            self.start_session()

            
           

            while True:

                action = self.pick_action(task)
                
                print("BrowsingAgent picked action: ", action)
                
                done = self.execute_action(action)
                if done:
                    break
                

if __name__ == "__main__":
    task = "open doordash and order me a Taco Bell burrito!"
    browsing_agent = BrowsingAgent()
    browsing_agent.browse(task)