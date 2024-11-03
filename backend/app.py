from flask import Flask, request, jsonify, make_response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from agent import Agent
from memory.lt_memory import LongTermMemory
import os
import base64

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response

def agent_reply_handler(message, client_sid):
    """Callback function to handle agent replies"""
    print("AGENT REPLY HANDLER", message, client_sid)
    socketio.send({"message": message})
    print(f"Message emitted: {message}")

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('start')
def handle_start(data):
    selectedActions = data.get('selectedActions')
    behavior = data.get('behavior')
    agent.start(selectedActions, behavior)

@socketio.on('user_message')
def handle_message(data):
    text = data.get('text', '')
    received_images = data.get('images', [])
    selectedActions = data.get('selectedActions', [])
    behaviorText = data.get('behaviorText', '')
    images = []
    for image in received_images:
        images.append({"image": image, "text": text})
    
    # Process the message
    full_input = text if text else ""

    
    print("FULL INPUT", full_input)
    client_sid = request.sid
    agent.receive_input(full_input, client_sid, images=images, selectedActions=selectedActions, behaviorText=behaviorText)

@socketio.on('reset')
def handle_reset():
    agent.reset()

if __name__ == "__main__":
    agent = Agent()
    print("Agent is ready. Starting Flask server...")
    agent.reply_callback = agent_reply_handler
    print("Agent is ready. Starting SocketIO server...")
    socketio.run(app, port=7777)