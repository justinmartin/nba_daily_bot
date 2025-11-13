import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Paris")
    MAIL_SMTP_HOST = os.getenv("MAIL_SMTP_HOST")
    MAIL_SMTP_PORT = int(os.getenv("MAIL_SMTP_PORT", 587))
    MAIL_SMTP_USER = os.getenv("MAIL_SMTP_USER")
    MAIL_SMTP_PASSWORD = os.getenv("MAIL_SMTP_PASSWORD")
    NEWS_RECIPIENT = os.getenv("NEWS_RECIPIENT")
    USE_HF_INF_API = os.getenv("USE_HF_INF_API", "false").lower() == "true"
    HF_API_TOKEN = os.getenv("HF_API_TOKEN")
    MODEL_ID = os.getenv("MODEL_ID", "EleutherAI/gpt-neo-125M")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 400))
    CACHE_PATH = os.getenv("CACHE_PATH", "./data/cache.db")
    BOT_RUN_TIME = os.getenv("BOT_RUN_TIME", "09:00")  # Format: HH:MM (24-hour)
    BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY", "")

