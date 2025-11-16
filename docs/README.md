# 🏀 NBA Daily Bot

An automated newsletter bot that generates daily NBA summaries using AI and sends them via email.

## Features

✅ **Automated Daily Newsletter** - Fetches NBA games, scores, and top performers from yesterday  
✅ **AI-Powered Content** - Uses transformer models (Mistral 7b from HF) to generate summaries.
✅ **News Integration** - Includes latest NBA news from ESPN  
✅ **HTML Email** - Email template with player statistics table  
✅ **Scheduled Execution** - Background scheduler for automatic daily runs  
✅ **Email Integration** - SMTP support for any email provider  

## Architecture

```
src/
├── main.py              # Main orchestration logic
├── config.py            # Configuration management
├── scheduler.py         # APScheduler for daily automation
├── fetch/
│   ├── scores.py        # Fetch NBA game scores
│   ├── players.py       # Fetch top performers stats
│   └── news.py          # Fetch ESPN RSS news
├── model/
│   └── hf_client.py     # HuggingFace model interface
├── send/
│   ├── mailer.py        # Email sending
│   └── render.py        # HTML rendering
└── render/
    └── newsletter_template.html  # Email template
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Email Configuration
MAIL_SMTP_HOST=smtp.gmail.com          # Your SMTP server
MAIL_SMTP_PORT=587
MAIL_SMTP_USER=your-email@gmail.com
MAIL_SMTP_PASSWORD=your-app-password   # Use app-specific password for Gmail
NEWS_RECIPIENT=recipient@example.com

# AI Model Configuration
USE_HF_INF_API=false                   # Use local model (true for API)
HF_API_TOKEN=your-hf-token             # Only needed if using Inference API
MODEL_ID=model_chosen_on_HF       # Transformer model ID
MAX_TOKENS=2000

# Scheduler
BOT_RUN_TIME=07:15                     # Daily run time (HH:MM, 24-hour format)
TIMEZONE=Europe/Paris

# Other
CACHE_PATH=./data/cache.db
```

## Data Sources

- **Games & Statistics**: [BallDontLie API](https://balldontlie.io/)
- **News**: [ESPN RSS Feed](https://www.espn.com/espn/rss/nba/news)
- **AI Model**: [HuggingFace Transformers](https://huggingface.co/)
