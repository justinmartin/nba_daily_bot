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
    # HF Router chat/completions often requires provider suffix (ex: :featherless-ai)
    MODEL_ID = os.getenv("MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai")
    HF_PROVIDER = os.getenv("HF_PROVIDER", "featherless-ai")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 400))
    
    CACHE_PATH = os.getenv("CACHE_PATH", "./data/cache.db")
    
    BOT_RUN_TIME = os.getenv("BOT_RUN_TIME", "09:00")
    
    BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY", "")

