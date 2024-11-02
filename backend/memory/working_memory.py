"""
The working memory stores the observations, actions, and the knowledge that an agent has at any point.

Think of the knowledge within the working memory as a map of knowledge that the agent has, where the keys are embeddings that store ideas that the agent has knowledge about, 
and the strings of sentences are just the bits of knowledge about that idea themselves.
"""


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
        self.observations = []  # History of observations and final outputs
        self.actions = []  # History of actions taken
        self.knowledge = {}
        self.variables = {} # These are variables that apply to extremely user-specific values within the agent's context. 
        # for example, if the agent is trying to book a flight, the variables could be the departure and arrival airports, the dates of the flight, etc.
        # if the agent is trying to find a restaurant, the variables could be the type of food, the price range, the location, etc.
        # if the agent is trying to send an email, the variables would be the email address.
    
    def store_observation(self, observation):
        """Store an observation or final output"""
        self.observations.append(observation)

    def store_action(self, action):
        """Store an action taken"""
        self.actions.append(action)

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


    def text_to_knowledge(self, text):
        """Parses a bunch of text into knowledge segments and then adds it to memory"""

        prompt = f"""
        You are an expert in information analysis and organization. Your task is to analyze a given text on any topic and break it down into distinct, self-contained segments. Each segment should focus on a single idea or concept related to the main topic of the text.

        Here is the text you need to analyze:

        <input_text>
        {text}
        </input_text>

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

    def print(self): 
        """Return a formatted string of the contents of working memory"""
        return f"""## Observations
        {self.observations if self.observations else "No observations recorded yet."}
        
        ## Actions Taken
        {self.actions if self.actions else "No actions taken yet."}
        
        ## Knowledge
        {[strings for strings in self.knowledge.values()] if self.knowledge else "No knowledge recorded or reasoned."}
        
        ## Variables
        {self.variables if self.variables else "No variables set yet."}
        """