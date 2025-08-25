# routes.py
import os
import uuid
import eventlet
from werkzeug.utils import secure_filename
from flask import request, jsonify, send_from_directory, abort

from utils import random_room_id, allowed_file, now_time, delete_file
from storage import rooms
from config import UPLOAD_FOLDER, FILE_TTL

# Register routes on the given app and socketio instances
def init_routes(app, socketio):

    @app.route("/api/host", methods=["POST"])
    def api_host():
        """Create a new room and register the host user"""
        data = request.get_json()
        username = (data.get("username") or "").strip()
        if not username:
            return jsonify({"error": "Please enter a name"}), 400

        # Generate unique room ID
        room_id = random_room_id()
        while room_id in rooms:
            room_id = random_room_id()

        # Initialize room with a set of users
        rooms[room_id] = {"users": set()}
        rooms[room_id]["users"].add(username)

        return jsonify({"roomId": room_id, "username": username}), 200

    @app.route("/api/join", methods=["POST"])
    def api_join():
        """Join an existing room with a unique username"""
        data = request.get_json()
        username = (data.get("username") or "").strip()
        room_id = (data.get("roomId") or "").strip().upper()

        if not username:
            return jsonify({"error": "Please enter a name"}), 400
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404

        # Check if username already exists in this room
        if username in rooms[room_id]["users"]:
            return jsonify({"error": "Username already taken"}), 409  # Conflict

        rooms[room_id]["users"].add(username)
        return jsonify({"roomId": room_id, "username": username}), 200

    @app.route("/api/room/<room_id>/exists")
    def room_exists(room_id):
        """Check if a room exists"""
        room_id = room_id.upper()
        if room_id in rooms:
            return jsonify({"exists": True}), 200
        return jsonify({"exists": False}), 404

    @app.route("/uploads/<path:filename>")
    def serve_upload(filename):
        """Serve uploaded media files"""
        full_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.isfile(full_path):
            abort(404)
        return send_from_directory(UPLOAD_FOLDER, filename)

    @app.route("/upload", methods=["POST"])
    def upload():
        """Upload media to a room and broadcast to users"""
        room_id = (request.form.get("room") or "").strip().upper()
        username = (request.form.get("username") or "").strip()

        if not room_id or room_id not in rooms:
            return jsonify({"error": "Invalid room"}), 400
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400

        orig_name = secure_filename(file.filename)
        ext = orig_name.rsplit(".", 1)[1].lower()
        unique = f"{uuid.uuid4().hex}.{ext}"
        path = os.path.join(UPLOAD_FOLDER, unique)
        file.save(path)

        # Schedule file deletion after TTL
        eventlet.spawn_after(FILE_TTL, delete_file, path)

        payload = {
            "username": username,
            "name": orig_name,
            "url": f"http://localhost:5000/uploads/{unique}",
            "ext": ext,
            "time": now_time()
        }

        # Emit event to all users in the room
        socketio.emit("receive_media", payload, room=room_id)

        return jsonify({"ok": True, "url": payload["url"]}), 200
