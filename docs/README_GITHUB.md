# 🏀 NBA Daily Newsletter Bot

Automated NBA newsletter generator that fetches daily game results, generates sarcastic summaries using AI, and sends them via email every morning.

## ✨ Features

- 📊 Fetches NBA game results from BallDontLie API
- 🤖 Generates witty, sarcastic summaries using Mistral-7B via HuggingFace
- 📧 Sends HTML newsletter emails to multiple recipients
- ⏰ Runs automatically via GitHub Actions every day at 7:30 AM
- 📱 Responsive mobile-friendly HTML email templates
- 🎯 Highlights biggest wins, blowouts, and top performers

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- HuggingFace API token
- Gmail account with app password
- BallDontLie API key

### Setup

1. **Clone & Install**
```bash
git clone https://github.com/yourusername/nba_daily_bot.git
cd nba_daily_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. **Run Manually**
```bash
# Test (dry run, no email)
python run.py test

# Send once
python run.py once

# Start scheduler (runs daily at BOT_RUN_TIME)
python run.py schedule
```

## 🔧 Configuration

Environment variables (see `.env.example`):
- `MAIL_SMTP_HOST` - Gmail SMTP server
- `MAIL_SMTP_USER` - Your Gmail address
- `MAIL_SMTP_PASSWORD` - Gmail app password
- `NEWS_RECIPIENT` - Email recipient(s), comma-separated
- `HF_API_TOKEN` - HuggingFace API token
- `MODEL_ID` - LLM model to use (default: Mistral-7B)
- `BOT_RUN_TIME` - Scheduler time in 24h format (e.g., "07:30")
- `BALLDONTLIE_API_KEY` - BallDontLie API key
- `MAX_TOKENS` - Max tokens for LLM generation (default: 800)

## 📧 Multiple Recipients

Add multiple email recipients separated by commas:
```env
NEWS_RECIPIENT=email1@example.com,email2@example.com
```

## 🤖 LLM Models

Currently configured to use **Mistral-7B-Instruct-v0.2** via HuggingFace's OpenAI-compatible API:
```env
USE_HF_INF_API=True
MODEL_ID=mistralai/Mistral-7B-Instruct-v0.2:featherless-ai
```

## 🔄 GitHub Actions Automation

The bot runs automatically via GitHub Actions every day at 7:30 AM UTC. 

**Setup GitHub Secrets:**
Add these as repository secrets in GitHub Settings → Secrets and variables:
- `MAIL_SMTP_HOST`
- `MAIL_SMTP_PORT`
- `MAIL_SMTP_USER`
- `MAIL_SMTP_PASSWORD`
- `NEWS_RECIPIENT`
- `BALLDONTLIE_API_KEY`
- `HF_API_TOKEN`
- `MODEL_ID`
- `MAX_TOKENS`

## 📂 Project Structure

```
nba_daily_bot/
├── src/
│   ├── config.py          # Configuration management
│   ├── main.py            # Main bot logic
│   ├── scheduler.py       # APScheduler integration
│   ├── fetch/
│   │   ├── scores.py      # BallDontLie API
│   │   ├── news.py        # ESPN news scraping
│   │   └── players.py     # Player stats
│   ├── model/
│   │   └── hf_client.py   # HuggingFace LLM
│   └── send/
│       ├── mailer.py      # SMTP email
│       ├── render.py      # HTML rendering
│       └── newsletter_template.html
├── .github/workflows/
│   └── nba-daily.yml      # GitHub Actions
├── run.py                 # CLI entry point
└── requirements.txt       # Dependencies
```

## 📊 Sample Output

- **Newsletter**: HTML email with game summaries, scores, news
- **Summary**: 5-7 sentence AI-generated sarcastic recap
- **Tone**: Trashtalk Magazine - witty, entertaining, sharp

## 🛠️ Development

### Local Testing
```bash
# Dry run (generates HTML, no email)
python run.py test

# Send test email
python run.py once
```

### Logs
Check `run.py` execution logs for debugging.

## 📝 License

MIT

## 👨‍💻 Author

Justin Martin

---

**Questions?** Check the [README.md](README.md) or open an issue!
