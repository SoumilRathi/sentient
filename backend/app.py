from flask import Flask, request, jsonify, make_response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from agent import Agent

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*",  async_mode='threading')



def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response




@app.route('/send_message', methods=['POST', 'OPTIONS'])
def send_message():
    if request.method == 'OPTIONS':
        response = _build_cors_preflight_response();
        return response, 200
    
    data = request.json
    if 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    user_input = data['message']
    agent.receive_input(user_input)

    response = jsonify({"status": "Message received"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response, 200


# Modified Agent class method to handle responses
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

@socketio.on('user_message')
def handle_message(data):
    message = data.get('message')
    if message:
        client_sid = request.sid
        agent.receive_input(message, client_sid)
    else:
        emit('error', {'message': 'No message provided'})


@socketio.on('reset')
def handle_reset():
    print("Reset received from client.")  # Debugging print statement
    agent.reset()  # Ensure that agent.reset() is valid and works without issues
    print("Agent reset.")


# Run the chat agent
if __name__ == "__main__":
    agent = Agent()
    print("Agent is ready. Starting Flask server...")
    agent.reply_callback = agent_reply_handler
    print("Agent is ready. Starting SocketIO server...")
    agent.long_term_memory.store_memory("semantic", "Taco Bell is the best mexican restaurant in Champaign")
    socketio.run(app, debug=True, port=7777)