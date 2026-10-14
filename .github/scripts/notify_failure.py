"""Mail d'alerte quand le workflow échoue (bibliothèque standard uniquement :
fonctionne même si l'installation des dépendances a planté)."""
import os
import smtplib
from email.mime.text import MIMEText

run_url = f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
msg = MIMEText(
    "Le run quotidien du NBA Daily Bot a échoué, aucune newsletter n'a été envoyée.\n\n"
    f"Logs : {run_url}\n",
    "plain", "utf-8",
)
msg["Subject"] = "❌ NBA Daily : échec du run"
msg["From"] = os.environ["MAIL_SMTP_USER"]
msg["To"] = os.environ["NEWS_RECIPIENT"]

with smtplib.SMTP(os.environ.get("MAIL_SMTP_HOST") or "smtp.gmail.com", int(os.environ.get("MAIL_SMTP_PORT") or 587)) as server:
    server.starttls()
    server.login(os.environ["MAIL_SMTP_USER"], os.environ["MAIL_SMTP_PASSWORD"])
    server.sendmail(msg["From"], [r.strip() for r in msg["To"].split(",")], msg.as_string())
print(f"Alerte envoyée à {msg['To']}")
