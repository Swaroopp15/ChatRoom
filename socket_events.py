# socket_events.py
from flask import request
from flask_socketio import join_room, emit, disconnect

from storage import rooms, user_socket_map
from utils import now_time

# We define a function that takes the socketio instance and registers events on it.
def init_socket_events(socketio):

    @socketio.on("connect")
    def on_connect():
        print("Client connected:", request.sid)

    @socketio.on("disconnect")
    def on_disconnect():
        print("Client disconnected:", request.sid)
        if request.sid in user_socket_map:
            username = user_socket_map[request.sid]["username"]
            room_id = user_socket_map[request.sid]["room"]
            
            if room_id in rooms and username in rooms[room_id]["users"]:
                rooms[room_id]["users"].remove(username)
                emit("receive_message", {
                    "role": "System",
                    "msg": f"{username} left the room.",
                    "time": now_time()
                }, room=room_id)
                emit("update_users", sorted(list(rooms[room_id]["users"])), room=room_id)
                
                if not rooms[room_id]["users"]:
                    del rooms[room_id]
            
            del user_socket_map[request.sid]

    @socketio.on("join")
    def on_join(data):
        room_id = (data.get("room") or "").upper()
        username = (data.get("username") or "").strip()
        if not room_id or not username:
            return
        
        if room_id not in rooms:
            rooms[room_id] = {"users": set()}
        
        join_room(room_id)
        rooms[room_id]["users"].add(username)
        user_socket_map[request.sid] = {"username": username, "room": room_id}

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
        if not room_id or not username or not msg:
            return

        emit("receive_message", {
            "role": username,
            "msg": msg,
            "time": now_time()
        }, room=room_id, include_self=False)

    @socketio.on("typing")
    def on_typing(data):
        room_id = (data.get("room") or "").upper()
        username = (data.get("username") or "").strip()
        if not room_id or not username:
            return
        emit("show_typing", {"by": username}, room=room_id, include_self=False)

    @socketio.on("stop_typing")
    def on_stop_typing(data):
        room_id = (data.get("room") or "").upper()
        if not room_id:
            return
        emit("hide_typing", {}, room=room_id)
