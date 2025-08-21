from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, emit
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64, random, string
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"
socketio = SocketIO(app, cors_allowed_origins="*")

rooms = {}  # room_id -> {public_key, private_key, messages}

# Encrypt message
def encrypt_message(message, pub_key):
    cipher = PKCS1_OAEP.new(pub_key)
    return base64.b64encode(cipher.encrypt(message.encode())).decode()

# Home page
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        choice = request.form.get("choice")
        if choice == "host":
            return redirect(url_for("host"))
        elif choice == "join":
            return redirect(url_for("join"))
    return render_template("home.html")

# Host a room
@app.route("/host", methods=["GET", "POST"])
def host():
    if request.method == "POST":
        username = request.form.get("username").strip()
        if not username:
            return "Please enter a name", 400
        room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        key = RSA.generate(2048)
        rooms[room_id] = {"public_key": key.publickey(), "private_key": key, "messages": []}
        session["room_id"] = room_id
        session["username"] = username
        session["role"] = "host"
        return redirect(url_for("chat", room_id=room_id))
    return render_template("host.html")

# Join a room
@app.route("/join", methods=["GET", "POST"])
def join():
    if request.method == "POST":
        username = request.form.get("username").strip()
        room_id = request.form.get("room_id").upper()
        if not username:
            return "Please enter a name", 400
        if room_id not in rooms:
            return "Room not found", 404
        session["room_id"] = room_id
        session["username"] = username
        session["role"] = "guest"
        return redirect(url_for("chat", room_id=room_id))
    return render_template("join.html")

# Force username input if not set
@app.route("/<room_id>", methods=["GET", "POST"])
def chat(room_id):
    room_id = room_id.upper()
    if room_id not in rooms:
        return "Room not found", 404

    # Force username input if not in session
    if "username" not in session:
        if request.method == "POST":
            username = request.form.get("username").strip()
            if not username:
                return "Please enter a name", 400
            session["username"] = username
            session["room_id"] = room_id
            return redirect(url_for("chat", room_id=room_id))
        return render_template("enter_name.html", room_id=room_id)

    room = rooms[room_id]
    username = session["username"]
    session["room_id"] = room_id
    return render_template("chat.html",
                           messages=room["messages"],
                           room_id=room_id,
                           username=username,
                           server_ip="localhost",
                           server_port=5000)

# SocketIO events
@socketio.on('join')
def handle_join(data):
    room_id = data['room']
    username = data['username']
    join_room(room_id)
    emit('receive_message', {"role": "System", "msg": f"{username} joined the room.", "time": datetime.now().strftime("%H:%M")}, room=room_id)

@socketio.on('send_message')
def handle_send_message(data):
    room_id = data['room']
    username = data['username']
    msg = data['msg']
    room = rooms.get(room_id)
    if room:
        enc_msg = encrypt_message(msg, room['public_key'])
        timestamp = datetime.now().strftime("%H:%M")
        room['messages'].append({"role": username, "msg": msg, "enc": enc_msg, "time": timestamp})
        emit('receive_message', {"role": username, "msg": msg, "enc": enc_msg, "time": timestamp}, room=room_id)

@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username')
    room_id = session.get('room_id')
    if room_id and username:
        emit('receive_message', {"role": "System", "msg": f"{username} left the room.", "time": datetime.now().strftime("%H:%M")}, room=room_id)

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
