import socket
import threading
import rsa
import hashlib
import os

BUFFER_SIZE = 4096
DEFAULT_PORT = 9999

def generate_keys():
    public_key, private_key = rsa.newkeys(2048)
    return public_key, private_key

def get_local_ip():
    """Get the local IP address dynamically, with fallback to manual input."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        print("Could not determine local IP automatically.")
        return input("Enter your local IP address manually: ")

def host_chat(port=DEFAULT_PORT):
    """Host a chat session as the server."""
    public_key, private_key = generate_keys()
    local_ip = get_local_ip()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((local_ip, port))
        server.listen(1)
        print(f"Hosting chat on {local_ip}:{port}. Waiting for connection...")

        client, addr = server.accept()
        print(f"Connected to {addr}")

        # Exchange public keys (use PKCS#1 format for compatibility)
        client.send(public_key.save_pkcs1())
        partner_public_key = rsa.PublicKey.load_pkcs1(client.recv(BUFFER_SIZE))

        # Fingerprint confirmation
        print(f"Partner's public key fingerprint: "
              f"{hashlib.sha256(partner_public_key.save_pkcs1()).hexdigest()}")

        return client, public_key, private_key, partner_public_key
    except Exception as e:
        print(f"Hosting failed: {e}")
        raise

def join_chat(host_ip, port=DEFAULT_PORT):
    """Join a chat session as the client."""
    public_key, private_key = generate_keys()

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((host_ip, port))
        print(f"Connected to {host_ip}:{port}")

        # Exchange public keys (use PKCS#1 format for compatibility)
        partner_public_key = rsa.PublicKey.load_pkcs1(client.recv(BUFFER_SIZE))
        client.send(public_key.save_pkcs1())

        # Fingerprint confirmation
        print(f"Partner's public key fingerprint: "
              f"{hashlib.sha256(partner_public_key.save_pkcs1()).hexdigest()}")

        return client, public_key, private_key, partner_public_key
    except Exception as e:
        print(f"Connection failed: {e}")
        raise

def send_messages(client, partner_public_key):
    """Thread function to send encrypted messages."""
    try:
        while True:
            message = input("You: ")
            if message.lower() == "exit":
                client.close()
                os._exit(0)  # Kill all threads

            encrypted_msg = rsa.encrypt(message.encode(), partner_public_key)
            client.send(encrypted_msg)
    except Exception as e:
        print(f"Send error: {e}")

def receive_messages(client, private_key):
    """Thread function to receive and decrypt messages."""
    try:
        while True:
            encrypted_msg = client.recv(BUFFER_SIZE)
            if not encrypted_msg:
                print("Connection closed by partner.")
                os._exit(0)

            decrypted_msg = rsa.decrypt(encrypted_msg, private_key).decode()
            print(f"Partner: {decrypted_msg}")
    except Exception as e:
        print(f"Receive error: {e}")

def main():
    print("Encrypted Chat Application")
    choice = input("Do you want to host (1) or connect (2)? ")

    try:
        if choice == "1":
            port = int(input(f"Enter port (default {DEFAULT_PORT}): ") or DEFAULT_PORT)
            client, _, private_key, partner_public_key = host_chat(port)
        elif choice == "2":
            host_ip = input("Enter host IP: ")
            port = int(input(f"Enter port (default {DEFAULT_PORT}): ") or DEFAULT_PORT)
            client, _, private_key, partner_public_key = join_chat(host_ip, port)
        else:
            print("Invalid choice. Exiting.")
            return

        # Start threads for sending and receiving
        threading.Thread(target=send_messages, args=(client, partner_public_key), daemon=True).start()
        threading.Thread(target=receive_messages, args=(client, private_key), daemon=True).start()

        # Keep main thread alive
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

