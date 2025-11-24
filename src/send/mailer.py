"""
Module d'envoi d'emails via SMTP.

Ce module gère l'envoi des newsletters NBA Daily par email en utilisant
le protocole SMTP (Simple Mail Transfer Protocol) avec TLS.

Fonctionnalités:
    - Envoi multi-destinataires (séparés par virgule dans .env)
    - Support Gmail, Outlook, et autres serveurs SMTP
    - Validation stricte de la configuration
    - Gestion détaillée des erreurs d'authentification et d'envoi
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.config import Config

logger = logging.getLogger(__name__)
cfg = Config()


def send_mail(html_body: str, subject: str):
    """
    Envoie un email HTML via SMTP avec validation et gestion d'erreurs.
    
    Args:
        html_body (str): Contenu HTML de l'email (corps du message)
        subject (str): Sujet de l'email (ex: "NBA Daily — 2025-11-23")
    
    Raises:
        ValueError: Si la configuration SMTP est incomplète ou invalide
        smtplib.SMTPAuthenticationError: Si l'authentification échoue
        smtplib.SMTPException: En cas d'erreur SMTP générale
        Exception: Pour toute autre erreur d'envoi
    
    Configuration requise (.env):
        - MAIL_SMTP_HOST: Serveur SMTP (ex: smtp.gmail.com)
        - MAIL_SMTP_PORT: Port SMTP (587 pour TLS)
        - MAIL_SMTP_USER: Email d'envoi
        - MAIL_SMTP_PASSWORD: Mot de passe ou App Password
        - NEWS_RECIPIENT: Email(s) destinataire(s), séparés par virgule
    
    Exemple:
        >>> send_mail("<h1>Test</h1>", "Test Email")
        # Envoie un email HTML à tous les destinataires configurés
    
    Notes:
        - Utilise TLS (Transport Layer Security) pour sécuriser la connexion
        - Gmail nécessite un "App Password" si 2FA activé
        - Supporte plusieurs destinataires: "user1@mail.com, user2@mail.com"
    """
    # === ÉTAPE 1: Valider la configuration SMTP ===
    if not cfg.MAIL_SMTP_HOST or not cfg.MAIL_SMTP_USER or not cfg.MAIL_SMTP_PASSWORD:
        raise ValueError("❌ SMTP configuration incomplete: MAIL_SMTP_HOST, MAIL_SMTP_USER, or MAIL_SMTP_PASSWORD missing")
    
    if not cfg.NEWS_RECIPIENT:
        raise ValueError("❌ NEWS_RECIPIENT email address not configured")
    
    if not html_body or not subject:
        raise ValueError("❌ Email body and subject cannot be empty")
    
    try:
        # === ÉTAPE 2: Parser les destinataires (support multi-email) ===
        # Format: "user1@mail.com, user2@mail.com" → ['user1@mail.com', 'user2@mail.com']
        recipients = [email.strip() for email in cfg.NEWS_RECIPIENT.split(",") if email.strip()]
        
        # === ÉTAPE 3: Créer le message email (format MIME) ===
        msg = MIMEMultipart("alternative")  # "alternative" = supporte HTML + texte brut
        msg["Subject"] = subject
        msg["From"] = cfg.MAIL_SMTP_USER
        msg["To"] = ", ".join(recipients)  # Affiche tous les destinataires dans l'en-tête
        
        # Attacher le corps HTML au message
        msg.attach(MIMEText(html_body, "html"))

        # === ÉTAPE 4: Se connecter au serveur SMTP ===
        logger.info(f"Connecting to SMTP server {cfg.MAIL_SMTP_HOST}:{cfg.MAIL_SMTP_PORT}")
        s = smtplib.SMTP(cfg.MAIL_SMTP_HOST, cfg.MAIL_SMTP_PORT)
        
        # === ÉTAPE 5: Démarrer TLS (chiffrement) ===
        # Obligatoire pour Gmail, Outlook, etc.
        s.starttls()
        
        # === ÉTAPE 6: S'authentifier avec les identifiants ===
        s.login(cfg.MAIL_SMTP_USER, cfg.MAIL_SMTP_PASSWORD)
        
        # === ÉTAPE 7: Envoyer l'email ===
        s.sendmail(cfg.MAIL_SMTP_USER, recipients, msg.as_string())
        
        # === ÉTAPE 8: Fermer la connexion ===
        s.quit()
        
        logger.info(f"✅ Email successfully sent to {', '.join(recipients)}")
        
    except smtplib.SMTPAuthenticationError as e:
        # Erreur d'authentification (mauvais mot de passe, 2FA non configuré, etc.)
        logger.error(f"❌ SMTP Authentication failed: {e}")
        raise
    except smtplib.SMTPException as e:
        # Autres erreurs SMTP (serveur indisponible, quota dépassé, etc.)
        logger.error(f"❌ SMTP Error: {e}")
        raise
    except Exception as e:
        # Erreur générique (réseau, timeout, etc.)
        logger.error(f"❌ Failed to send email: {e}")
        raise
