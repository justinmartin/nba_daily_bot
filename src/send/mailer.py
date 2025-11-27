
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.config import Config

logger = logging.getLogger(__name__)
cfg = Config()

def send_mail(html_body: str, subject: str):
    if not cfg.MAIL_SMTP_HOST or not cfg.MAIL_SMTP_USER or not cfg.MAIL_SMTP_PASSWORD:
        raise ValueError("❌ SMTP configuration incomplete: MAIL_SMTP_HOST, MAIL_SMTP_USER, or MAIL_SMTP_PASSWORD missing")
    
    if not cfg.NEWS_RECIPIENT:
        raise ValueError("❌ NEWS_RECIPIENT email address not configured")
    
    if not html_body or not subject:
        raise ValueError("❌ Email body and subject cannot be empty")
    
    try:
        recipients = [email.strip() for email in cfg.NEWS_RECIPIENT.split(",") if email.strip()]
        
        msg = MIMEMultipart("alternative")  # "alternative" = supporte HTML + texte brut
        msg["Subject"] = subject
        msg["From"] = cfg.MAIL_SMTP_USER
        msg["To"] = ", ".join(recipients)  # Affiche tous les destinataires dans l'en-tête
        
        msg.attach(MIMEText(html_body, "html"))

        logger.info(f"Connecting to SMTP server {cfg.MAIL_SMTP_HOST}:{cfg.MAIL_SMTP_PORT}")
        s = smtplib.SMTP(cfg.MAIL_SMTP_HOST, cfg.MAIL_SMTP_PORT)
        
        s.starttls()
        
        s.login(cfg.MAIL_SMTP_USER, cfg.MAIL_SMTP_PASSWORD)
        
        s.sendmail(cfg.MAIL_SMTP_USER, recipients, msg.as_string())
        
        s.quit()
        
        logger.info(f"✅ Email successfully sent to {', '.join(recipients)}")
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ SMTP Authentication failed: {e}")
        raise
    except smtplib.SMTPException as e:
        logger.error(f"❌ SMTP Error: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        raise
