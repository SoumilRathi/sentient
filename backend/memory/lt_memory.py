"this file is effectively the wrapper for using mongodb as the long term memory directly"

import datetime
from sentence_transformers import SentenceTransformer
from numpy import dot
from numpy.linalg import norm
# from mongodb import client

model = SentenceTransformer('all-mpnet-base-v2')
class LongTermMemory:
    def __init__(self):
        """Initialize long-term memory as dictionaries of sentences"""
        self.episodic = [];
        self.semantic = [];
        self.procedural = [];
    
    def store_memory(self):
        """Store a memory in the appropriate category"""

        # db = client.long_term_memory
        # coll = db.semantic_memory

        
        segment = "Hey my name is Soumil"

        segment_embedding = model.encode(segment);

        segment_embedding = segment_embedding.tolist();

        # result = coll.insert_one({
        #     'text': segment,
        #     'embedding': segment_embedding
        # })

        # print(result);


    def retrieve_memory(self, query):
        """Retrieve a memory from long term memory based on the similarity score to the memory request"""

        # db = client.long_term_memory
        # coll = db.semantic_memory

        segment_embedding = model.encode(query);

        segment_embedding = segment_embedding.tolist();

        resultsList = [];

        # results = coll.aggregate([
        #     {
        #         "$vectorSearch": {
        #             "index": "embedding",
        #             "path": "embedding",
        #             "queryVector": segment_embedding,
        #             "limit": 6,
        #             "numCandidates": 41,
        #             "minScore": 0.8
        #         }
        #     }
        # ])

        # for result in results:
        #     resultsList.append(result['text']);

        # return resultsList;


