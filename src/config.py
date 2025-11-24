"""
Configuration du bot NBA Daily.

Ce module charge toutes les variables d'environnement depuis le fichier .env
et les rend accessibles via la classe Config.

Variables requises (.env):
    - MAIL_SMTP_HOST: Serveur SMTP (ex: smtp.gmail.com)
    - MAIL_SMTP_PORT: Port SMTP (587 pour TLS, 465 pour SSL)
    - MAIL_SMTP_USER: Email d'envoi
    - MAIL_SMTP_PASSWORD: Mot de passe SMTP ou App Password
    - NEWS_RECIPIENT: Email(s) destinataire(s) (séparés par virgule si plusieurs)
    - HF_API_TOKEN: Token d'API HuggingFace pour génération de texte
    
Variables optionnelles:
    - TIMEZONE: Fuseau horaire (défaut: Europe/Paris)
    - USE_HF_INF_API: true/false pour utiliser l'API HF au lieu du modèle local
    - MODEL_ID: ID du modèle HuggingFace (défaut: EleutherAI/gpt-neo-125M)
    - MAX_TOKENS: Nombre max de tokens générés (défaut: 400)
    - BOT_RUN_TIME: Heure d'exécution quotidienne au format HH:MM (défaut: 09:00)
"""

import os
from dotenv import load_dotenv

# === ÉTAPE 1: Charger le fichier .env ===
# load_dotenv() lit le fichier .env à la racine du projet
# et injecte toutes les variables dans os.environ
load_dotenv()


class Config:
    """
    Configuration centralisée pour le bot NBA Daily.
    
    Toutes les valeurs sont chargées depuis les variables d'environnement (.env).
    Les valeurs par défaut sont utilisées si la variable n'est pas définie.
    """
    
    # === CONFIGURATION GÉNÉRALE ===
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Paris")
    
    # === CONFIGURATION EMAIL (SMTP) ===
    # Serveur SMTP pour envoyer les emails
    MAIL_SMTP_HOST = os.getenv("MAIL_SMTP_HOST")
    # Port SMTP (587 = TLS, 465 = SSL)
    MAIL_SMTP_PORT = int(os.getenv("MAIL_SMTP_PORT", 587))
    # Email utilisé pour l'envoi
    MAIL_SMTP_USER = os.getenv("MAIL_SMTP_USER")
    # Mot de passe SMTP ou App Password (Gmail, Outlook, etc.)
    MAIL_SMTP_PASSWORD = os.getenv("MAIL_SMTP_PASSWORD")
    # Email(s) qui recevront la newsletter (séparés par virgule si plusieurs)
    NEWS_RECIPIENT = os.getenv("NEWS_RECIPIENT")
    
    # === CONFIGURATION HUGGINGFACE (IA) ===
    # true = utiliser l'API HuggingFace, false = modèle local
    USE_HF_INF_API = os.getenv("USE_HF_INF_API", "false").lower() == "true"
    # Token d'authentification HuggingFace (obligatoire si USE_HF_INF_API=true)
    HF_API_TOKEN = os.getenv("HF_API_TOKEN")
    # ID du modèle HuggingFace à utiliser pour la génération de texte
    MODEL_ID = os.getenv("MODEL_ID", "EleutherAI/gpt-neo-125M")
    # Nombre maximum de tokens à générer (400 tokens ≈ 300 mots)
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 400))
    
    # === CONFIGURATION CACHE ET DONNÉES ===
    # Chemin vers le fichier de cache SQLite (non utilisé actuellement)
    CACHE_PATH = os.getenv("CACHE_PATH", "./data/cache.db")
    
    # === CONFIGURATION PLANIFICATION ===
    # Heure quotidienne d'exécution du bot au format HH:MM (24h)
    # Exemple: "09:00" = 9h du matin
    BOT_RUN_TIME = os.getenv("BOT_RUN_TIME", "09:00")
    
    # === CONFIGURATION API EXTERNE ===
    # Clé API pour balldontlie.io (non utilisée actuellement, on utilise nba_api)
    BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY", "")

