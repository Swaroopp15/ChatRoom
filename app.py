import os
import uuid
import string
import random
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort
from flask_socketio import SocketIO, join_room, emit
from werkzeug.utils import secure_filename

# ------------------------------
# Config
# ------------------------------
APP_SECRET = "supersecretkey"
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp",
    "mp4", "webm", "ogg", "mp3", "wav", "m4a",
    "pdf", "txt", "csv", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "zip", "rar"
}
MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25MB per file
FILE_TTL = 6 * 60 * 60  # 6 hours

# ------------------------------
# App
# ------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = APP_SECRET
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory only (no persistence)
rooms = {}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------------------
# Helpers
# ------------------------------
def random_room_id(n=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def now_time():
    return datetime.now().strftime("%H:%M")

# ------------------------------
# Background cleanup thread
# ------------------------------
def cleanup_files():
    while True:
        now = time.time()
        for f in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, f)
            if os.path.isfile(path):
                if now - os.path.getmtime(path) > FILE_TTL:
                    try:
                        os.remove(path)
                        print(f"[CLEANUP] Deleted expired file: {path}")
                    except Exception as e:
                        print(f"[CLEANUP ERROR] {e}")
        time.sleep(3600)  # run every hour

threading.Thread(target=cleanup_files, daemon=True).start()

# ------------------------------
# Routes
# ------------------------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        choice = request.form.get("choice")
        if choice == "host":
            return redirect(url_for("host"))
        elif choice == "join":
            return redirect(url_for("join"))
    return render_template("home.html")

@app.route("/host", methods=["GET", "POST"])
def host():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        if not username:
            return "Please enter a name", 400
        room_id = random_room_id()
        rooms[room_id] = {"users": set()}
        session["room_id"] = room_id
        session["username"] = username
        session["role"] = "host"
        return redirect(url_for("chat", room_id=room_id))
    return render_template("enter_name.html")

@app.route("/join", methods=["GET", "POST"])
def join():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        room_id = (request.form.get("room_id") or "").strip().upper()
        if not username:
            return "Please enter a name", 400
        if room_id not in rooms:
            return "Room not found", 404
        session["room_id"] = room_id
        session["username"] = username
        session["role"] = "guest"
        return redirect(url_for("chat", room_id=room_id))
    return render_template("join.html")

@app.route("/<room_id>", methods=["GET", "POST"])
def chat(room_id):
    room_id = room_id.upper()
    if room_id not in rooms:
        return "Room not found", 404

    if "username" not in session or session.get("room_id") != room_id:
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            if not username:
                return "Please enter a name", 400
            session["username"] = username
            session["room_id"] = room_id
            return redirect(url_for("chat", room_id=room_id))
        return render_template("enter_name.html", room_id=room_id)

    return render_template("chat.html",
                           room_id=room_id,
                           username=session["username"])

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    full_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.isfile(full_path):
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/upload", methods=["POST"])
def upload():
    room_id = (request.form.get("room") or "").strip().upper()
    username = (request.form.get("username") or "").strip()
    if not room_id or room_id not in rooms:
        return "Invalid room", 400
    if "file" not in request.files:
        return "No file part", 400
    file = request.files["file"]
    if not file or file.filename == "":
        return "No selected file", 400
    if not allowed_file(file.filename):
        return "File type not allowed", 400

    orig_name = secure_filename(file.filename)
    ext = orig_name.rsplit(".", 1)[1].lower()
    unique = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], unique)
    file.save(path)

    payload = {
        "username": username,
        "name": orig_name,
        "url": url_for("serve_upload", filename=unique),
        "ext": ext,
        "time": now_time()
    }
    socketio.emit("receive_media", payload, room=room_id)
    return {"ok": True, "url": payload["url"]}, 200

# ------------------------------
# Socket.IO events
# ------------------------------
@socketio.on("join")
def on_join(data):
    room_id = (data.get("room") or "").upper()
    username = (data.get("username") or "").strip()
    if not room_id or not username or room_id not in rooms:
        return

    join_room(room_id)
    rooms[room_id]["users"].add(username)

    emit("receive_message", {
        "role": "System",
        "msg": f"{username} joined the room.",
        "time": now_time()
    }, room=room_id)

    emit("update_users", sorted(list(rooms[room_id]["users"])), room=room_id)

@socketio.on("send_message")
def on_send_message(data):
    room_id = (data.get("room") or "").upper()
    username = (data.get("username") or "").strip()
    msg = (data.get("msg") or "").strip()
    if not room_id or not username or room_id not in rooms or not msg:
        return

    emit("receive_message", {
        "role": username,
        "msg": msg,
        "time": now_time()
    }, room=room_id)

@socketio.on("typing")
def on_typing(data):
    room_id = (data.get("room") or "").upper()
    username = (data.get("username") or "").strip()
    if not room_id or not username or room_id not in rooms:
        return
    emit("show_typing", {"by": username}, room=room_id, include_self=False)

@socketio.on("stop_typing")
def on_stop_typing(data):
    room_id = (data.get("room") or "").upper()
    if not room_id or room_id not in rooms:
        return
    emit("hide_typing", {}, room=room_id)

@socketio.on("disconnect")
def on_disconnect():
    room_id = session.get("room_id")
    username = session.get("username")

    if room_id and username and room_id in rooms:
        rooms[room_id]["users"].discard(username)

        emit("receive_message", {
            "role": "System",
            "msg": f"{username} left the room.",
            "time": now_time()
        }, room=room_id)

        emit("update_users", sorted(list(rooms[room_id]["users"])), room=room_id)

        if not rooms[room_id]["users"]:
            del rooms[room_id]

# ------------------------------
# Main
# ------------------------------
if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
