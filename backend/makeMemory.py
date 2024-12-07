# from firebase import db
from firebase_admin import firestore
from mongodb import client
import json
from helper_functions import use_claude
from sentence_transformers import SentenceTransformer
from numpy import dot
from numpy.linalg import norm
from listOfFiles import files

model = SentenceTransformer('all-mpnet-base-v2')




def makeMemory(text):
    "The idea here is that it's a helper function that I'll write text to, it'll get claude to convert it to individual segments, and then it'll store each segment individually on firebase ig"


    prompt = f"""
    You are an expert in CSS and technical writing. Your task is to analyze a given text about CSS best practices and break it down into distinct, self-contained segments. Each segment should focus on a single idea or concept related to CSS best practices.

Here is the text you need to analyze:

<css_text>
{text}
</css_text>

Please follow these steps to complete the task:

1. Carefully read through the entire text.
2. Identify distinct ideas or concepts related to CSS best practices.
3. For each identified idea:
   a. Create a segment that fully explains that idea.
   b. Ensure the segment is self-contained and doesn't reference other topics.
   c. The segment can be multiple sentences long, but should remain focused on the single idea.
4. Compile all segments into a list.
5. Convert the list into a JSON object with a key of "segments" and an array of strings as the value.

Before providing your final output, wrap your thought process inside <thinking> tags. In this section:
- List and number the main CSS best practices you've identified in the text.
- Explain how you plan to create self-contained segments for each practice.
- Describe any potential challenges you foresee in segmentation and how you'll address them.
- Verify that each segment is truly self-contained and focused on a single idea.

Your final output must strictly adhere to the following JSON format:

{{
    "segments": [
        "Segment 1 content focusing on idea A.",
        "Segment 2 content focusing on idea B.",
        "Segment 3 content focusing on idea C."
    ]
}}

Ensure that your JSON is valid and that each segment contains every relevant piece of information from the original text, leaving nothing out. The segments should collectively capture all the CSS best practices mentioned in the original text.
    """


    response = use_claude(prompt);

    # Extract the JSON content from the response
    json_start = response.find('{')
    json_end = response.rfind('}') + 1
    json_content = response[json_start:json_end]

    # Parse the JSON content
    output = json.loads(json_content)
   

    knowledge = output['segments'];

    for segment in knowledge:

        segment_embedding = model.encode(segment);

        segment_embedding = segment_embedding.tolist();

        print(len(segment_embedding));

        return;

        # result = coll.insert_one({
        #     'text': segment,
        #     'embedding': segment_embedding
        # })

text = "Use the CSS property background-color to change the color of the background of an element."



print("ALL DONE!")