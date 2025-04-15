# app.py
from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room, send

# Configuration
SECRET_KEY = 'your_secret_key!' # Change this in production!
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
# Initialize Flask-SocketIO, using eventlet for async mode
# You might need to install eventlet: pip install eventlet
socketio = SocketIO(app, async_mode='eventlet')

# Store users: session ID -> nickname
# In a real app, use a database or more robust storage
users = {}

# --- HTTP Routes ---

@app.route('/')
def index():
    """Serve the index page."""
    # Renders the HTML file from the 'templates' folder
    return render_template('index.html')

# --- SocketIO Event Handlers ---

@socketio.on('connect')
def handle_connect():
    """Handles new WebSocket connections."""
    print(f"Client connected: {request.sid}")
    # Note: We don't know the nickname yet. We'll ask for it.
    emit('request_nickname') # Ask the newly connected client for their nickname


@socketio.on('set_nickname')
def handle_set_nickname(nickname):
    """Associates a nickname with the client's session ID."""
    sid = request.sid
    if nickname and sid not in users:
        users[sid] = nickname
        print(f"Nickname set: {nickname} for SID {sid}")
        # Broadcast to OTHERS that a user joined
        emit('user_join', {'nickname': nickname}, broadcast=True, include_self=False)
        # Send the current user list to the newly joined user
        emit('user_list', {'users': list(users.values())})
        # Send confirmation back to the sender
        emit('nickname_accepted', {'nickname': nickname})
        # Send user list update to everyone else too
        emit('user_list', {'users': list(users.values())}, broadcast=True, include_self=False)

    elif nickname:
         # Handle case where nickname might already be taken or user tries to set again
         # For simplicity, we'll just acknowledge if they are already known
         if users.get(sid) == nickname:
             emit('nickname_accepted', {'nickname': nickname}) # Acknowledge existing
             emit('user_list', {'users': list(users.values())}) # Send user list again
         else:
             # Maybe send an error if nickname is taken by someone else (more complex check needed)
             print(f"Attempt to set nickname '{nickname}' failed or duplicate for SID {sid}")
             # You might want to emit an error back to the client here

    else:
        print(f"Invalid nickname attempt by SID {sid}")
        # You might want to emit an error back to the client here


@socketio.on('send_message')
def handle_send_message(data):
    """Handles receiving messages from a client and broadcasting them."""
    sid = request.sid
    nickname = users.get(sid) # Get nickname associated with the sender's session ID
    message_text = data.get('message')

    if nickname and message_text:
        print(f"Message from {nickname} ({sid}): {message_text}")
        # Broadcast the message to ALL connected clients, including the sender
        emit('new_message', {
            'nickname': nickname,
            'message': message_text
        }, broadcast=True)
    elif not nickname:
        print(f"Message received from unknown user (SID: {sid}): {message_text}")
        emit('error', {'message': 'Please set your nickname before sending messages.'})
    else:
        # Empty message ignored silently or handle as needed
        pass


@socketio.on('disconnect')
def handle_disconnect():
    """Handles client disconnections."""
    sid = request.sid
    nickname = users.pop(sid, None) # Remove user and get their nickname
    if nickname:
        print(f"Client disconnected: {nickname} ({sid})")
        # Broadcast to OTHERS that a user left
        emit('user_leave', {'nickname': nickname}, broadcast=True)
        # Update user list for everyone remaining
        emit('user_list', {'users': list(users.values())}, broadcast=True)
    else:
        print(f"Client disconnected: Unknown user ({sid})")

# --- Main Execution ---

if __name__ == '__main__':
    print("Starting Flask-SocketIO server...")
    # Use socketio.run to start the server correctly with WebSocket support
    # host='0.0.0.0' makes it accessible on your local network
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    # Debug=True is helpful for development, turn off for production