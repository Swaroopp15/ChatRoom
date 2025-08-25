# utils.py
import os
import string
import random
from datetime import datetime
from werkzeug.utils import secure_filename

from config import ALLOWED_EXTENSIONS

def random_room_id(n=6):
    """Generates a random, unique room ID."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

def allowed_file(filename: str) -> bool:
    """Checks if a file extension is in the allowed set."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def now_time():
    """Returns the current time in H:M format."""
    return datetime.now().strftime("%H:%M")

def delete_file(path):
    """Deletes a file from the uploads folder."""
    try:
        os.remove(path)
        print(f"File deleted: {path}")
    except OSError as e:
        print(f"Error deleting file {path}: {e}")
