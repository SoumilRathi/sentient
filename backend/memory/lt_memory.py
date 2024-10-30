import datetime
from sentence_transformers import SentenceTransformer
from numpy import dot
from numpy.linalg import norm


model = SentenceTransformer('all-mpnet-base-v2')
class LongTermMemory:
    def __init__(self):
        """Initialize long-term memory as dictionaries of sentences"""
        self.episodic = [];
        self.semantic = [];
        self.procedural = [];
    
    def store_memory(self, memory_type, memory):
        """Store a memory in the appropriate category"""
        if memory_type == 'episodic':
            self.episodic.append({
                "memory": memory,
                "timestamp": datetime.now()
            })
        elif memory_type == 'semantic':
            self.semantic.append({
                "memory": memory,
                "embedding": model.encode(memory)
            })

            # print("MEMORY STORED IN SEMANTIC MEMORY");

            # print(self.semantic);
        elif memory_type == 'procedural':
            self.procedural.append(memory)
        else:
            raise ValueError("Invalid memory type. Must be 'episodic', 'semantic', or 'procedural'.")


    def retrieve_memory(self, memory_type, memory_request):
        """Retrieve a memory from long term memory"""

        if memory_type == "semantic":

            # Get the embedding of the memory request
            memory_request_embedding = model.encode(memory_request)

            # Create a dictionary to store the similarity scores for each memory
            similarity_scores = {}

            # Calculate the similarity scores for each memory in the semantic memory
            for memory in self.semantic:
                cos_sim = (memory_request_embedding @ memory["embedding"].T) / (norm(memory_request_embedding)*norm(memory["embedding"]))
                similarity_scores[memory["memory"]] = cos_sim

            # Filter the memories with similarity scores greater than or equal to 0.5
            filtered_memories = {memory: score for memory, score in similarity_scores.items() if score >= 0.5}

            # Get the top 5 memories with the highest similarity scores
            top_memories = sorted(filtered_memories.items(), key=lambda x: x[1], reverse=True)[:5]

            # Return the top memories
            return top_memories
        
        else:
            return []

        




