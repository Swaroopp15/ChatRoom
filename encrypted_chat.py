import socket
import threading
import rsa
import hashlib
import os
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox

BUFFER_SIZE = 4096
DEFAULT_PORT = 9999

def generate_keys():
    return rsa.newkeys(2048)

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return simpledialog.askstring("IP Required", "Enter your local IP address:")

def host_chat(port=DEFAULT_PORT):
    public_key, private_key = generate_keys()
    local_ip = get_local_ip()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind((local_ip, port))
    server.listen(1)
    append_message(f"Hosting chat on {local_ip}:{port}...\n")

    client, addr = server.accept()
    append_message(f"Connected to {addr}\n")

    # Exchange keys
    client.send(public_key.save_pkcs1())
    partner_public_key = rsa.PublicKey.load_pkcs1(client.recv(BUFFER_SIZE))

    append_message(f"Partner's key fingerprint: {hashlib.sha256(partner_public_key.save_pkcs1()).hexdigest()}\n")

    return client, public_key, private_key, partner_public_key

def join_chat(host_ip, port=DEFAULT_PORT):
    public_key, private_key = generate_keys()

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host_ip, port))
    append_message(f"Connected to {host_ip}:{port}\n")

    partner_public_key = rsa.PublicKey.load_pkcs1(client.recv(BUFFER_SIZE))
    client.send(public_key.save_pkcs1())

    append_message(f"Partner's key fingerprint: {hashlib.sha256(partner_public_key.save_pkcs1()).hexdigest()}\n")

    return client, public_key, private_key, partner_public_key

def send_message():
    message = entry.get()
    if not message:
        return
    entry.delete(0, tk.END)
    try:
        encrypted_msg = rsa.encrypt(message.encode(), partner_public_key)
        client.send(encrypted_msg)
        append_message(f"You: {message}\n")
    except Exception as e:
        append_message(f"Send error: {e}\n")

def receive_messages():
    try:
        while True:
            encrypted_msg = client.recv(BUFFER_SIZE)
            if not encrypted_msg:
                append_message("Connection closed by partner.\n")
                break
            decrypted_msg = rsa.decrypt(encrypted_msg, private_key).decode()
            append_message(f"Partner: {decrypted_msg}\n")
    except Exception as e:
        append_message(f"Receive error: {e}\n")

def append_message(msg):
    chat_area.config(state=tk.NORMAL)
    chat_area.insert(tk.END, msg)
    chat_area.config(state=tk.DISABLED)
    chat_area.yview(tk.END)

def start_chat():
    global client, private_key, partner_public_key

    choice = simpledialog.askstring("Choice", "Host (1) or Connect (2)?")
    try:
        if choice == "1":
            port = simpledialog.askinteger("Port", f"Enter port (default {DEFAULT_PORT}):") or DEFAULT_PORT
            client, _, private_key, partner_public_key = host_chat(port)
        elif choice == "2":
            host_ip = simpledialog.askstring("Host IP", "Enter host IP:")
            port = simpledialog.askinteger("Port", f"Enter port (default {DEFAULT_PORT}):") or DEFAULT_PORT
            client, _, private_key, partner_public_key = join_chat(host_ip, port)
        else:
            messagebox.showerror("Error", "Invalid choice")
            return

        threading.Thread(target=receive_messages, daemon=True).start()
    except Exception as e:
        messagebox.showerror("Error", str(e))

# ---------------- Tkinter UI ---------------- #
root = tk.Tk()
root.title("🔒 Encrypted Chat")

chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, state=tk.DISABLED, width=50, height=20)
chat_area.pack(padx=10, pady=10)

entry = tk.Entry(root, width=40)
entry.pack(side=tk.LEFT, padx=10, pady=5)

send_btn = tk.Button(root, text="Send", command=send_message)
send_btn.pack(side=tk.RIGHT, padx=10, pady=5)

# Start chat setup
start_chat()

root.mainloop()
