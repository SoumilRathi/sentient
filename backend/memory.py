from helper_functions import print_conversation, use_claude, use_gemini, use_gpt, get_ordinal_suffix
from sentence_transformers import SentenceTransformer
import json
import os
import time
import numpy as np   
from numpy import dot
from numpy.linalg import norm
from datetime import datetime
from db import supabase
import ast

os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Force CPU usage
model = SentenceTransformer('all-mpnet-base-v2', device='cpu')


class Memory:

    def __init__(self, system=None, user_id=None):
        self.system = system
        self.nodes = []
        self.adj_matrix = []
        self.activations = [] # stores a list of the currently active nodes
        self.user_id = user_id


        # get the nodes and adj_matrix so far
        nodes = supabase.table('nodes').select('*').eq('user_id', user_id).execute().data
        adj_matrix = supabase.table('users').select('adj_matrix').eq('user_id', user_id).execute().data[0]['adj_matrix']
        if nodes:
            self.nodes = nodes
        if adj_matrix:
            self.adj_matrix = adj_matrix

        # print("Nodes: ", self.nodes)
        # print("Adj Matrix: ", self.adj_matrix)

         

    def find_or_add_node(self, knowledge):
        "This function takes in a piece of knowledge and either finds the node that already represents it or creates a new node"

        segment_embedding = model.encode(knowledge)
        segment_embedding = segment_embedding.tolist()

        

        similar_nodes = []
        for i, node in enumerate(self.nodes):
            if node['knowledge'] == knowledge:
                return i
            
            embedding = node['embedding']
            try:
                embedding = json.loads(embedding)
            except:
                pass
            
            node_embedding = np.array(embedding, dtype=np.float64)
            similarity = np.dot(segment_embedding, node_embedding) / (np.linalg.norm(segment_embedding) * np.linalg.norm(node_embedding))
            
            if similarity > 0.6:
                return i

            if similarity > 0.35:
                similar_nodes.append(i)

        for row in self.adj_matrix:
            row.append(0)
        self.adj_matrix.append([0] * (len(self.nodes) + 1))

        new_node = {"knowledge": knowledge, "embedding": segment_embedding, "user_id": self.user_id}

        data = supabase.table('nodes').insert(new_node).execute()
        new_node['id'] = data.data[0]['id']
        new_node['created_at'] = data.data[0]['created_at']
        self.nodes.append(new_node)

        for i, node in enumerate(self.nodes[:-1]):
            embedding = node['embedding']
            try:
                embedding = json.loads(embedding)
            except:
                pass
            node_embedding = np.array(embedding, dtype=np.float64)
            similarity = np.dot(np.array(segment_embedding), node_embedding) / (norm(np.array(segment_embedding)) * norm(node_embedding))
            self.adj_matrix[i][-1] = self.adj_matrix[-1][i] = similarity

        self.activations.append({
            "node": len(self.nodes) - 1,
            "activation": 1
        })

        return len(self.nodes) - 1
    
    def process_conversation(self):
        prompt = f"""
        You are the memory management system for an overall personal assistant. Analyze the past conversation and 
        information received to decide what should be specifically remembered.        
        
        Conversation:
        {print_conversation(self.system.conversation)}

        Memory:
        {self.system.print_all_memory()}

        # Instructions
        1. Look through the conversation and memory to find facts and personality traits about the user that could be useful for later tasks.
        1.1. You don't need to write down anything if there's nothing relevant, feel free to leave the array empty.
        
        2. Make sure you store it to things that will be extremely important in the future as well, not just one-time things.
        
        3. Don't note things related to a job the user wants one, or a one-time thing. These memories should be limited to aspects of personality or persistent facts about the user.
            3.1. Is the detail important to store, or a one time job that they wanted one? If it is a one time job, don't store it in memory. Otherwise, if it is a consistent fact, store it in memory.
            3.2. You can store tasks and actions about the user if it is a long term action the user is taking, not if it is a one time request. Eg. If they are taking a journey, building a company, etc. these things can be stored as they are relatively permanent.
        
        4. Memory is very expensive to store, so this is for important details ONLY—please store concrete facts, not platonic interactions. 
        4.1. If you already have similar memories, no need to repeat them or store similar memories. If your new memory will not make a significant difference to decisions, there's no reason to store it.
        4.2. DO NOT store every job the user gets done. Store explicit facts about their personality that you did not already know.
        4.3. Only store essential information—things which would be extremely relevant or important to future tasks. A single task, reminder, or timing is not relevant enough to store. Don't be retarded and store every little thing that happens.

        Please ensure that the characteristic or memory you are storing is a major one, not a minor aspect of personality. Again, it is VERY EXPENSIVE to store memory, so try to limit it to important details.

        Each memory should be a single sentence about the user or their tasks/goals.

        Output format:
        {{
            "memories": ["memory 1", "memory 2", ...]
        }}

        Go through the instructions step by step, outputting your thoughts, and then output your final decision in a perfect JSON format.
        """

        response = use_gemini(prompt)
        print("Memory Decider Output: ", response)
        response = json.loads(response[response.find('{'):response.rfind('}')+1])

        for memory in response['memories']:
            self.find_or_add_node(memory)
        
        for i in range(len(self.activations)):
            for j in range(i + 1, len(self.activations)):
                node1, node2 = self.activations[i]['node'], self.activations[j]['node']
                activation_product = float(self.activations[i]['activation']) * float(self.activations[j]['activation'])
                if self.adj_matrix[node1][node2] == 0:
                    self.adj_matrix[node1][node2] = self.adj_matrix[node2][node1] = activation_product * 0.25
                else:
                    self.adj_matrix[node1][node2] += activation_product * 0.25 * self.adj_matrix[node1][node2]
                    self.adj_matrix[node2][node1] += activation_product * 0.25 * self.adj_matrix[node2][node1]
        print("Adj Matrix: ", self.adj_matrix)
        supabase.table('users').update({
            'adj_matrix': self.adj_matrix
        }).eq('user_id', self.system.user_id).execute()

    def activate_nodes(self, input): 
        """
        Activates nodes most relevant to the input. Uses maximum activation amount and BFS with weights.
        """
        if not self.nodes:
            self.activations = []
            return

        # Convert input to embedding once
        input_embedding = np.array(model.encode(input))
        # Ensure node embeddings are properly formatted
        node_embeddings = []
        for node in self.nodes:
            embedding = node['embedding']
            try:
                embedding = json.loads(embedding)
            except:
                pass
            node['embedding'] = embedding
            node_embeddings.append(embedding)

        node_embeddings = np.array(node_embeddings)
        
        # Reshape input embedding to match node embeddings
        input_embedding = input_embedding.reshape(1, -1)
        
        # Vectorized similarity calculation
        similarities = np.dot(node_embeddings, input_embedding.T).flatten() / (
            np.linalg.norm(node_embeddings, axis=1) * np.linalg.norm(input_embedding)
        )
        
        # Initialize activated nodes using vectorized operations
        activated_indices = np.where(similarities > 0.25)[0]
        activated_nodes = [{"node": i, "activation": similarities[i]} for i in activated_indices]

        # Initialize activated nodes using word matching
        input_words = set(input.lower().split())
        for i, node in enumerate(self.nodes):
            node_words = set(node['knowledge'].lower().split())
            if input_words.intersection(node_words):
                new_activation = 0.25
                existing_node = next((n for n in activated_nodes if n['node'] == i), None)
                if existing_node:
                    existing_node['activation'] = max(existing_node['activation'], new_activation)
                else:
                    activated_nodes.append({"node": i, "activation": new_activation})
        
        # Add exact matches with activation 1
        for i, node in enumerate(self.nodes):
            if node['knowledge'] == input:
                activated_nodes.append({"node": i, "activation": 1.0})
        
        if not activated_nodes:
            self.activations = []
            return
            
        # Use sets for O(1) lookups
        visited = set()
        activation_dict = {node['node']: node for node in activated_nodes}
        total_activation = sum(node['activation'] for node in activated_nodes)
        
        # Sort once initially
        to_visit = sorted(activated_nodes, key=lambda x: x['activation'], reverse=True)

        print("Activated nodes: ", activated_nodes)

        threshold = 2

        if len(to_visit) == 0:
            to_visit.append(self.activations[0])
            total_activation = self.activations[0]['activation']
            visited.add(self.activations[0]['node'])

        while to_visit and total_activation < threshold:
            current = to_visit.pop(0)
            if current['node'] in visited:
                continue
            
            visited.add(current['node'])
            
            connections = np.array([i for i, val in enumerate(self.adj_matrix[current['node']]) if val > 0])
            strengths = np.array([self.adj_matrix[current['node']][i] for i in connections])
            sorted_indices = np.argsort(strengths)[::-1]
            connections = connections[sorted_indices]
            strengths = strengths[sorted_indices]
            
            for connected_node, strength in zip(connections, strengths):
                if connected_node in visited or connected_node in activation_dict:
                    continue
                
                new_activation = current['activation'] * strength
                activation_dict[connected_node] = {"node": connected_node, "activation": new_activation}
                to_visit.append(activation_dict[connected_node])
                total_activation += new_activation
            
            to_visit.sort(key=lambda x: x['activation'], reverse=True)
            
            if total_activation >= threshold:
                break
        
        self.activations = list(activation_dict.values())

    def print(self):
        """Prints the memory"""
        # Implementation needed
        txt = "Here's the relevant pieces of memory, along with their importance from a scale of 0 to 100 and the time they were created:"
        for node in sorted(self.activations, key=lambda x: x['activation'], reverse=True):
            created_at = datetime.fromisoformat(self.nodes[node['node']]['created_at'])
            ordinal_day = f"{created_at.day}{get_ordinal_suffix(created_at.day)}"
            formatted_date = f"{ordinal_day} {created_at.strftime('%b')}"
            activation_percentage = node['activation'] * 50
            txt += f"\n{self.nodes[node['node']]['knowledge']} - {activation_percentage:.2f} - {formatted_date}"
        if len(self.activations) == 0:
            txt += "\nNo activated pieces of memory yet"
        return txt

    


if __name__ == "__main__":
    memory = Memory(user_id="2b01c7fd-252b-4ab4-8071-9b0fd1919f81")
    memory.activate_nodes("email")
    print(memory.print())
