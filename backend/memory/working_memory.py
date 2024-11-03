"""
The working memory stores the observations, actions, and the knowledge that an agent has at any point.

Think of the knowledge within the working memory as a map of knowledge that the agent has, where the keys are embeddings that store ideas that the agent has knowledge about, 
and the strings of sentences are just the bits of knowledge about that idea themselves.
"""

import threading
import time
import datetime
from sentence_transformers import SentenceTransformer
from numpy import dot
from numpy.linalg import norm
# from mongodb import client
from consts import IDENTITY_THRESHOLD, SIMILARITY_THRESHOLD
from helper_functions import use_claude
import json;
model = SentenceTransformer('all-mpnet-base-v2')

class WorkingMemory:
    def __init__(self):
        """Initialize working memory with different categories"""
        self.basic_information = {
            "datetime": datetime.datetime.now().isoformat()
        }
        self.observations = []  # History of observations and final outputs
        self.actions = []  # History of actions taken
        self.knowledge = {}
        self.variables = {} # These are variables that apply to extremely user-specific values within the agent's context. 
        # for example, if the agent is trying to book a flight, the variables could be the departure and arrival airports, the dates of the flight, etc.
        # if the agent is trying to find a restaurant, the variables could be the type of food, the price range, the location, etc.
        # if the agent is trying to send an email, the variables would be the email address.
        self.conversation_history = []
        
        # Start a background thread to update datetime every minute
        self.update_thread = threading.Thread(target=self._update_datetime, daemon=True)
        self.update_thread.start()
        
    def _update_datetime(self):
        """Update datetime every minute in a background thread"""
        while True:
            self.basic_information["datetime"] = datetime.datetime.now().isoformat()
            time.sleep(60)  # Sleep for 60 seconds
    def store_observation(self, observation):
        """Store an observation or final output"""
        self.observations.append(observation)

    def store_action(self, action):
        """Store an action taken"""
        self.actions.append(action)

    def store_conversation_history(self, conversation_history):
        """Store a conversation history"""
        self.conversation_history.append(conversation_history)

    def retrieve_all(self):
        """Retrieve all contents of working memory"""
        return {
            'observations': self.observations,
            'actions': self.actions,
            'knowledge': self.knowledge
        }

    def clear(self):
        """Clear working memory"""
        self.observations = []
        self.actions = []
        self.knowledge = {}


    def store_knowledge(self, knowledge_segment):
        """Store knowledge"""

        # Extract phrase and sentences from knowledge segment
        print("KNOWLEDGE SEGMENT: ",knowledge_segment)
        phrase = knowledge_segment["title"]
        sentences = knowledge_segment['content']
        
        # Get embedding for the phrase
        phrase_embedding = model.encode(phrase)
        
        # Check if any existing knowledge matches above identity threshold
        found_match = False
        for existing_phrase in self.knowledge:
            existing_embedding = model.encode(existing_phrase)
            similarity = dot(phrase_embedding, existing_embedding)/(norm(phrase_embedding)*norm(existing_embedding))
            
            if similarity >= IDENTITY_THRESHOLD:
                # Add sentences to existing matching phrase
                self.knowledge[existing_phrase].extend(sentences)
                found_match = True
                break
                
        if not found_match:
            # Create new entry if no match found
            self.knowledge[phrase] = sentences


    def text_to_knowledge(self, text, query=None):
        """Parses a bunch of text into knowledge segments and then adds it to memory"""

        prompt = f"""
        You are an expert in information analysis and organization. Your task is to analyze a given text on any topic and break it down into distinct, self-contained segments. Each segment should focus on a single idea or concept related to the main topic of the text.

        Here is the text you need to analyze:

        <input_text>
        {text}
        </input_text>

        { 
            f"""When segmenting the text, please segment the knowledge relevant to the original search query: 
            <query>
            {query}
            </query>""" if query else ""
        }

        In case the previous observations prove to be useful, you can use them to help you analyze the text.

        <observations>
        {self.observations if self.observations else "No observations recorded yet."}
        </observations>

        Please follow these steps to complete the task:

        1. Carefully read through the entire text.
        2. Identify distinct ideas or concepts related to the main topic.
        3. For each identified idea:
        a. Create a segment that fully explains that idea.
        b. Ensure the segment is self-contained and doesn't reference other topics.
        c. The segment can be multiple sentences long, but should remain focused on the single idea.
        4. Compile all segments into a list.
        5. Convert the list into a JSON object with segment titles as keys and arrays of sentences as values.

        Before providing your final output, wrap your thought process inside <analysis> tags. In this section:
        - List and number the main topics or ideas you've identified in the text.
        - Identify and list key terms or concepts from the text.
        - Consider how ideas are interconnected and how you plan to separate them.
        - Draft a rough outline of segments.
        - Explain how you plan to create self-contained segments for each topic.
        - Describe any potential challenges you foresee in segmentation and how you'll address them.
        - Verify that each segment is truly self-contained and focused on a single idea.

        Your final output must strictly adhere to the following JSON format:

        {{
            "Segment Title 1": [
                "Sentence 1 focusing on the idea of Segment 1",
                "Sentence 2 focusing on the idea of Segment 1"
            ],
            "Segment Title 2": [
                "Sentence 1 focusing on the idea of Segment 2",
                "Sentence 2 focusing on the idea of Segment 2"
            ]
        }}

        Ensure that your JSON is valid and that each segment contains every relevant piece of information from the original text, leaving nothing out. The segments should collectively capture all the main ideas mentioned in the original text, regardless of the topic.
        """

        print("PROMPT: ",prompt)


        response = use_claude(prompt)

        print("RESPONSE: ",response)

        # Extract the JSON content from the response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        json_content = response[json_start:json_end]

        # Parse the JSON content
        output = json.loads(json_content)

        # Iterate through each segment title and its sentences
        for segment_title, sentences in output.items():
            # Create a JSON object for this segment
            segment_obj = {
                "title": segment_title,
                "content": sentences
            }
            
            # Store the segment in memory
            self.store_knowledge(segment_obj)


    def get_variable(self, variable_name):
        """Get a variable"""
        if variable_name in self.variables:
            return self.variables[variable_name]
        else:
            # check to see if it meets the identify threshold
            phrase_embedding = model.encode(variable_name)
            best_match = None
            highest_similarity = IDENTITY_THRESHOLD
            for variable_key in self.variables:
                existing_embedding = model.encode(variable_key)
                similarity = dot(phrase_embedding, existing_embedding)/(norm(phrase_embedding)*norm(existing_embedding))
                if similarity >= IDENTITY_THRESHOLD and similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match = variable_key
            return self.variables[best_match] if best_match else None

    def set_variable(self, variable_name, variable_value):
        """Set a variable"""
        if variable_name in self.variables:
            self.variables[variable_name] = variable_value
        else:
            # check to see if it meets the identify threshold
            phrase_embedding = model.encode(variable_name)
            best_match = None
            highest_similarity = IDENTITY_THRESHOLD
            for variable_key in self.variables:
                existing_embedding = model.encode(variable_key)
                similarity = dot(phrase_embedding, existing_embedding)/(norm(phrase_embedding)*norm(existing_embedding))
                if similarity >= IDENTITY_THRESHOLD and similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match = variable_key
            
            if best_match:
                self.variables[best_match] = variable_value
            else:
                self.variables[variable_name] = variable_value
    
    def get_related_variables(self, phrase):
        """Get related variables"""
        phrase_embedding = model.encode(phrase)
        related_variables = []
        for variable in self.variables:
            variable_embedding = model.encode(variable)
            similarity = dot(phrase_embedding, variable_embedding)/(norm(phrase_embedding)*norm(variable_embedding))
            if similarity >= SIMILARITY_THRESHOLD:
                related_variables.append(variable)
        return related_variables


    def get_variables_from_input(self):
        """This function will be called after each input, to extract important variables that the user may have provided. The variables are entirely dependent on the user, so it can be assumed that they can fully be extracted from the input"""
        
        all_input_text = ""
        # Get last 10 conversation history entries
        recent_history = self.conversation_history[-10:] if len(self.conversation_history) > 10 else self.conversation_history
        
        # Build input text from conversation history
        for entry in recent_history:
            if entry["from"] == "user":
                all_input_text += f"User: {entry['message']}\n"
            else:
                all_input_text += f"Agent: {entry['message']}\n"

        # this way the all input text is effectively the entire history of the conversation

        prompt = f"""

        You are an advanced AI assistant specializing in information extraction and organization. Your task is to analyze a given text, typically a conversation history, and identify distinct user-specific variables along with their values. These variables should relate to personal information that needs to be remembered for future interactions.

        Here is the text you need to analyze:

        <input_text>
        {all_input_text}
        </input_text>

        Please follow these steps to complete the task:

        1. Carefully read through the entire input text.

        2. Conduct an analysis of the text, focusing on identifying user-specific variables. Wrap your analysis inside <analysis> tags. In your analysis:
        a. List all names mentioned in the text.
        b. Identify potential variables related to the user's personal information.
        c. For each potential variable, note its value, the surrounding context, and its frequency in the text.
        d. Categorize each variable (e.g., personal information, preferences, numerical data).
        e. Cross-reference identified variables with common personal information categories (e.g., name, age, location, occupation).
        f. Evaluate the relevance and consistency of each variable to the user's personal information.
        g. Perform a second pass to check for any missed variables, especially short names or nicknames.
        h. Compile a final list of relevant user-specific variables and their values.

        3. Convert the final list into a JSON object, with variable names as keys and their values as values.

        4. Return the JSON object.

        Your analysis should follow this structure:

        <analysis>
        Names mentioned in the text:
        [List all names]

        1. Potential variable: [variable name]
        Value: [corresponding value]
        Category: [category of the variable]
        Context: [surrounding text or reasoning for identification]
        Frequency: [how often the variable appears in the text]
        Relevance: [explanation of why this is relevant user-specific information]
        Consistency: [note if the value is consistent throughout the text]

        2. Potential variable: [another variable name]
        Value: [corresponding value]
        Category: [category of the variable]
        Context: [surrounding text or reasoning for identification]
        Frequency: [how often the variable appears in the text]
        Relevance: [explanation of why this is relevant user-specific information]
        Consistency: [note if the value is consistent throughout the text]

        [Continue for all identified variables]

        Cross-reference with common personal information categories:
        [List how identified variables match with common categories]

        Second pass for missed variables:
        [List any additional variables found, following the same structure]

        Final list of relevant user-specific variables and values:
        - [variable1]: [value1]
        - [variable2]: [value2]
        [etc.]
        </analysis>

        After completing your analysis, provide the final output in the following JSON format:

        {{
        "variable1": "value1",
        "variable2": "value2",
        ...
        }}

        Remember, only include variables that are specifically related to the user's personal information and are important for future interactions. Do not include random or irrelevant variables.
        """

        print("PROMPT: ",prompt)

        response = use_claude(prompt)

        print("RESPONSE: ",response)


    def reason(self, query):
        """Reason about the current working memory"""
        prompt = f"""
        You already have a working memory that contains a lot of knowledge and information you have about the current task. 

        Your task is to use the knowledge and information in the working memory to reason about the current query.

        Here is the query:
        <query>
        {query}
        </query>

        Here is the working memory:

        <working_memory>
        {self.print()}
        </working_memory>

        Instructions:
        1. Please attempt to generate new knowledge about the current query based on the working memory.
        2. Ensure that you do not make up any information that is not already given to you. Your task is to only use the information already present in the working memory and generating new knowledge/information based on that.
        
        Return your thoughts and the new knowledge you have generated in <reasoning> tags.

        Give a name/heading to the new knowledge you have generated, and then provide the new knowledge.

        Your final output must strictly adhere to the following format:

        <final>
        "Heading for the new knowledge"
        "Sentence 1 regarding the new knowledge",
        "Sentence 2 regarding the new knowledge"
        ...
        </final>
        """


        response = use_claude(prompt)


        # Extract the content between <final> tags
        try:
            # Find content between <final> tags
            final_start = response.find("<final>") + len("<final>")
            final_end = response.find("</final>")
            final_content = response[final_start:final_end].strip().split("\n")

            # First line is the title, rest are content
            title = final_content[0].strip().strip('"')
            content = [line.strip().strip('"').strip(',') for line in final_content[1:]]
            content = [line for line in content if line] # Remove empty lines

            # Store the knowledge
            self.store_knowledge({
                "title": title,
                "content": content
            })

            return {title, content}

        except Exception as e:
            print(f"Error parsing reasoning response: {e}")
            return None

    def print(self): 
        """Return a formatted string of the contents of working memory"""
        return f"""
        ## Basic Information
        {"\n".join([f"### {key}\n{value}" for key, value in self.basic_information.items()]) if self.basic_information else "No basic information recorded yet."}
        
        ## Observations
        {self.observations if self.observations else "No observations recorded yet."}
        
        ## Actions Taken
        {self.actions if self.actions else "No actions taken yet."}
        
        ## Knowledge
        {[strings for strings in self.knowledge.values()] if self.knowledge else "No knowledge recorded or reasoned."}
        
        ## User-Specific Variables
        {self.variables if self.variables else "No variables set yet."}
        """