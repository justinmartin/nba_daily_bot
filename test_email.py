#!/usr/bin/env python3
"""Test script pour vérifier l'envoi d'email."""

from src.config import Config
from src.send.mailer import send_mail

cfg = Config()
print('📧 Testing email configuration...')
print(f'SMTP Host: {cfg.MAIL_SMTP_HOST}')
print(f'SMTP Port: {cfg.MAIL_SMTP_PORT}')
print(f'SMTP User: {cfg.MAIL_SMTP_USER}')
print(f'Recipient: {cfg.NEWS_RECIPIENT}')

# Test avec un petit HTML
html = '<h1>Test Email NBA Bot</h1><p>Si tu reçois cet email, la config SMTP marche !</p>'

try:
    send_mail(html, 'Test NBA Daily Bot')
    print('✅ Email envoyé avec succès !')
    print('📬 Vérifie ta boîte mail !')
except Exception as e:
    print(f'❌ Erreur: {e}')
    import traceback
    traceback.print_exc()
