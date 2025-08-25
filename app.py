import eventlet
eventlet.monkey_patch()
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
import os

from routes import init_routes
from socket_events import init_socket_events
from config import APP_SECRET, UPLOAD_FOLDER

app = Flask(__name__)
app.config["SECRET_KEY"] = APP_SECRET
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

CORS(app, origins=["*"], supports_credentials=True)

socketio = SocketIO(app, 
                    cors_allowed_origins="*", 
                    async_mode='eventlet',
                    logger=True,
                    engineio_logger=True)

init_routes(app, socketio)
init_socket_events(socketio)

if __name__ == "__main__":
    print("Starting server on http://localhost:5000")
    # Ensure upload folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
