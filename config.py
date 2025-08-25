# config.py
import os

APP_SECRET = "supersecretkey"
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads") # Use absolute path for safety
ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp",
    "mp4", "webm", "ogg", "mp3", "wav", "m4a",
    "pdf", "txt", "csv", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "zip", "rar"
}
MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25MB per file
FILE_TTL = 6 * 60 * 60  # 6 hours
