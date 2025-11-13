# 🏀 NBA Daily Bot

An automated newsletter bot that generates daily NBA summaries using AI and sends them via email.

## Features

✅ **Automated Daily Newsletter** - Fetches NBA games, scores, and top performers from yesterday  
✅ **AI-Powered Content** - Uses transformer models (GPT-Neo) to generate engaging summaries in French  
✅ **RSS News Integration** - Includes latest NBA news from ESPN  
✅ **Beautiful HTML Email** - Professional email template with player statistics table  
✅ **Scheduled Execution** - Background scheduler for automatic daily runs  
✅ **Robust Error Handling** - Retry logic, validation, and comprehensive logging  
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
MODEL_ID=EleutherAI/gpt-neo-125M       # Transformer model ID
MAX_TOKENS=400

# Scheduler
BOT_RUN_TIME=09:00                     # Daily run time (HH:MM, 24-hour format)
TIMEZONE=Europe/Paris

# Other
CACHE_PATH=./data/cache.db
```

### 3. Run the Bot

**Test mode (dry run - no email sending):**
```bash
python -m src.main
```

**Production mode (actually sends email):**
```python
# In src/main.py, change:
# if __name__ == "__main__":
#     run(dry_run=True)  # change to False
```

**Scheduled mode (runs daily automatically):**
```bash
python -m src.scheduler
```

## Usage

### Manual Execution

```python
from src.main import run

# Test without sending email
run(dry_run=True)

# Send email
run(dry_run=False)
```

### Automated Scheduling

Run the scheduler to execute the bot daily at the configured time:

```bash
python -m src.scheduler
```

The scheduler will run in the background and execute the newsletter generation at the specified time each day.

## Configuration Details

### SMTP Providers

#### Gmail
```env
MAIL_SMTP_HOST=smtp.gmail.com
MAIL_SMTP_PORT=587
MAIL_SMTP_USER=your-email@gmail.com
MAIL_SMTP_PASSWORD=your-app-specific-password
```
⚠️ Use [App Passwords](https://support.google.com/accounts/answer/185833) instead of your regular password.

#### Outlook
```env
MAIL_SMTP_HOST=smtp-mail.outlook.com
MAIL_SMTP_PORT=587
```

#### Custom Server
```env
MAIL_SMTP_HOST=your-smtp-server.com
MAIL_SMTP_PORT=587
```

### AI Models

#### Local Model (Default)
```env
USE_HF_INF_API=false
MODEL_ID=EleutherAI/gpt-neo-125M
```
- Runs on your machine (CPU/GPU)
- Free but requires compute
- First run downloads the model (~2.5GB)

#### HuggingFace Inference API
```env
USE_HF_INF_API=true
HF_API_TOKEN=hf_xxxxx
MODEL_ID=EleutherAI/gpt-neo-125M
```
- Runs on HuggingFace servers
- Requires API token (get from https://huggingface.co/settings/tokens)
- Paid service but no local compute needed

## Improvements Made

### Error Handling & Validation ✅
- Validates SMTP configuration before sending
- Checks for missing data (None values, empty arrays)
- Safe key access with `.get()` in dictionaries
- Proper exception handling with detailed error messages

### Retry Logic ✅
- Implements exponential backoff for API calls
- Retries on rate limits (HTTP 429) and server errors
- Configurable retry strategy

### Logging ✅
- Replaced all `print()` statements with proper logging
- Different log levels (INFO, WARNING, ERROR, DEBUG)
- Structured log messages with timestamps

### Code Quality ✅
- Removed unused imports (Jinja2)
- Removed dead code (`render_html()` function)
- Added docstrings to all functions
- Better type hints and comments

### Automation ✅
- Added APScheduler for background task execution
- Configurable daily run time via environment variable
- Graceful shutdown handling

## Logging

The bot outputs structured logs with levels:

```
INFO    - Normal operations (fetching, rendering, sending)
WARNING - Non-critical issues (missing data, skipped items)
ERROR   - Critical failures that need attention
DEBUG   - Detailed information for troubleshooting
```

Example output:
```
2024-11-13 09:00:00 - src.main - INFO - 🚀 Starting NBA Daily Bot for 2024-11-12
2024-11-13 09:00:01 - src.fetch.scores - INFO - ✅ Fetched 10 games for 2024-11-12
2024-11-13 09:00:05 - src.fetch.players - INFO - ✅ Fetched 50 top performers
2024-11-13 09:00:06 - src.fetch.news - INFO - ✅ Fetched 5 NBA news articles from ESPN
2024-11-13 09:00:15 - src.main - INFO - 📧 Email sent to recipient@example.com
2024-11-13 09:00:15 - src.main - INFO - ✨ Newsletter generation completed successfully!
```

## Troubleshooting

### API Errors
- Check internet connection
- Verify API endpoints are accessible
- Check rate limits at balldontlie.io

### SMTP Errors
- Verify SMTP credentials
- Check SMTP host and port are correct
- For Gmail: Use app-specific password, not regular password
- Check firewall/network restrictions

### Model Errors
- For local model: Ensure transformers and torch are installed
- First run will download the model (large download)
- For Inference API: Verify HF_API_TOKEN is valid

### Empty Newsletter
- Verify there were NBA games yesterday
- Check API connectivity
- Review logs for detailed error messages

## Data Sources

- **Games & Statistics**: [BallDontLie API](https://balldontlie.io/)
- **News**: [ESPN RSS Feed](https://www.espn.com/espn/rss/nba/news)
- **AI Model**: [HuggingFace Transformers](https://huggingface.co/)

## License

MIT License - Feel free to use and modify!

## Future Enhancements

- [ ] Cache API responses to avoid repeated calls
- [ ] Support multiple languages
- [ ] Customize newsletter sections
- [ ] Web dashboard for monitoring
- [ ] Database storage of newsletters
- [ ] SMS notifications
- [ ] Slack/Discord integration
