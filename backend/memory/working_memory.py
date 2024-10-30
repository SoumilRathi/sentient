"""
Basically there are types of things that we will store in the working memory. First is obviously the history of observations and final outputs within
         a particular episode. This should be an array of the messages, since the only observations rn are messages. 
            Generalize this for the final platform.
         
        Another thing is the history of actions that we have taken. This can just be an array of sentences lmao. 

        And the final thing is the retrieved long term memory. 
            This should be stored in an interesting way. This can be divided into 3 categories: 
                - Episodic: Past experiences as sentences
                - Semantic: General world knowledge as sentences
                - Procedural: Procedural rules or sentences


                But the thing is, each of those should be represented as a map, with each time someone retrieves a memory, 
                the request gets stored as the key and the retrieved memory gets stored as the value.
"""


class WorkingMemory:
    def __init__(self):
        """Initialize working memory with different categories"""
        self.observations = []  # History of observations and final outputs
        self.actions = []  # History of actions taken
        self.retrieved_memory = {
            'episodic': {},
            'semantic': {},
            'procedural': {}
        }
        self.knowledge = []
    
    def store_observation(self, observation):
        """Store an observation or final output"""
        self.observations.append(observation)

    def store_action(self, action):
        """Store an action taken"""
        self.actions.append(action)

    def store_retrieved_memory(self, memory_type, request, memory):
        """Store a retrieved memory with its request"""
        if memory_type in self.retrieved_memory:
            self.retrieved_memory[memory_type][request] = memory
        else:
            raise ValueError("Invalid memory type. Must be 'episodic', 'semantic', or 'procedural'.")

    def retrieve_all(self):
        """Retrieve all contents of working memory"""
        return {
            'observations': self.observations,
            'actions': self.actions,
            'retrieved_memory': self.retrieved_memory
        }

    def clear(self):
        """Clear working memory"""
        self.observations = []
        self.actions = []
        self.retrieved_memory = {
            'episodic': {},
            'semantic': {},
            'procedural': {}
        }

    def store_knowledge(self, knowledge):
        """Store knowledge"""
        self.knowledge.append(knowledge)

    def print(self): 
        """Return a formatted string of the contents of working memory"""
        return f"""## Observations
        {self.observations if self.observations else "No observations recorded yet."}

        ## Retrieved Memory
        {"".join([f"### {memory_type.capitalize()} Memory\n" + 
                  ("".join([f"#### {request}\n{memory if memory else 'No related memories found.'}\n" 
                            for request, memory in memories.items()]) 
                   if memories else "No memories retrieved yet.\n")
                  for memory_type, memories in self.retrieved_memory.items()])}

        ## Actions Taken
        {self.actions if self.actions else "No actions taken yet."}
        
        ## Knowledge
        {self.knowledge if self.knowledge else "No knowledge recorded or reasoned."}
        """
