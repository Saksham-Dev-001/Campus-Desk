"""CampusDesk configuration. All secrets from environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

class Config:
    # --- Core ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
    # Fix for Heroku/Neon/Supabase/Railway which give postgres:// but SQLAlchemy needs postgresql://
    _db_url = os.environ.get("DATABASE_URL", "sqlite:///" + str(BASE_DIR / "campusdesk.db"))
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    APP_NAME = "CampusDesk"
    APP_VERSION = "2.6"
    TEAM = "Team Anonymous"
    DEMO_MODE = os.environ.get("DEMO_MODE", "0") == "1"
    TEMPLATES_AUTO_RELOAD = True

    # --- Uploads ---
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "25"))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = {
        "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx",
        "txt", "md", "csv", "png", "jpg", "jpeg", "webp", "gif", "zip",
    }

    # --- Sessions ---
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 days

    # --- Storage ---
    # STORAGE_PROVIDER = "telegram" (server cloud storage)
    STORAGE_PROVIDER = os.environ.get("STORAGE_PROVIDER", "telegram").lower()

    # --- Telegram (topic-based storage in ONE supergroup) ---
    #   1. Create a supergroup with forum topics enabled
    #   2. Create one topic per branch (CSE, CS, AIML, DS, ...)
    #   3. Add your bot as group admin
    #   4. Set TELEGRAM_STORAGE_CHAT_ID to the supergroup's negative chat id
    #   5. Set TELEGRAM_TOPICS to a JSON map of branch code → topic id
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_STORAGE_CHAT_ID = os.environ.get("TELEGRAM_STORAGE_CHAT_ID", "")
    TELEGRAM_TOPICS = os.environ.get("TELEGRAM_TOPICS", "{}")
    TELEGRAM_API_BASE = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org")
