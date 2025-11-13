# 🚀 NBA Daily Bot - Quick Start Checklist

## ✅ What's Been Done

### Code Improvements
- [x] Fixed typos in config (HF_API_TOKEN)
- [x] Added comprehensive error handling
- [x] Implemented retry logic with exponential backoff
- [x] Replaced all print() with logging
- [x] Removed unused code (render_html function, Jinja2 imports)
- [x] Added data validation throughout
- [x] Added timeouts to all API calls
- [x] Safe key access with .get() everywhere

### New Features
- [x] APScheduler for daily automation
- [x] Background scheduler (run.py)
- [x] CLI modes (test/once/schedule)
- [x] Configurable run time (BOT_RUN_TIME)

### Documentation
- [x] Complete README.md (200+ lines)
- [x] IMPROVEMENTS.md (detailed changelog)
- [x] REFACTOR_SUMMARY.md (before/after)
- [x] Updated .env.example with comments
- [x] Added docstrings to all functions
- [x] Requirements.txt with versions

---

## 🎯 Next Steps for You

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
# Copy the template
cp .env.example .env

# Edit with your settings
nano .env
# or
code .env
```

**Required settings:**
- MAIL_SMTP_HOST (Gmail: smtp.gmail.com)
- MAIL_SMTP_USER (your email)
- MAIL_SMTP_PASSWORD (app password for Gmail)
- NEWS_RECIPIENT (where to send newsletter)

### Step 3: Test the Setup
```bash
# Test without sending email
python run.py test

# Check output in out/newsletter_YYYY-MM-DD.html
```

### Step 4: Send a Test Email
```bash
# Send one newsletter now
python run.py once
```

### Step 5: Set Up Scheduled Runs
```bash
# Run in background (keeps running)
python run.py schedule

# Or in production, use supervisor/systemd to keep it running
```

---

## 📋 Configuration Checklist

Before running in production:

- [ ] Create `.env` file from `.env.example`
- [ ] Verify MAIL_SMTP_HOST is correct for your email provider
- [ ] Verify MAIL_SMTP_USER is your email address
- [ ] Set MAIL_SMTP_PASSWORD (Gmail: use app-specific password)
- [ ] Set NEWS_RECIPIENT to where you want newsletters
- [ ] Test with `python run.py test`
- [ ] Review output in `out/` folder
- [ ] Test sending with `python run.py once`
- [ ] Check your inbox for the test email
- [ ] Deploy with `python run.py schedule`

---

## 🔍 Verification Commands

```bash
# Check all imports work
python -c "from src.main import run; print('✅ Imports work')"

# Check config loads
python -c "from src.config import Config; print('✅ Config loads')"

# Check logging works
python -c "import logging; logging.basicConfig(); logger = logging.getLogger(); logger.info('✅ Logging works')"

# Check scheduler works
python -c "from src.scheduler import schedule_bot; print('✅ Scheduler imports')"

# List all errors (if any)
python -m py_compile src/**/*.py
```

---

## 🆘 Troubleshooting

### ModuleNotFoundError
```bash
# Make sure you're in the right directory
cd /path/to/nba_daily_bot

# Reinstall dependencies
pip install -r requirements.txt
```

### SMTP Connection Error
```
Check:
- MAIL_SMTP_HOST is correct
- MAIL_SMTP_PORT is correct (usually 587)
- MAIL_SMTP_USER is your full email
- MAIL_SMTP_PASSWORD is correct (Gmail: use app password)
- Firewall isn't blocking port 587
```

### API Rate Limit
```
The bot now retries automatically!
- First attempt
- Wait 1 second, retry
- Wait 2 seconds, retry
- Wait 4 seconds, retry

If still fails, check balldontlie.io status
```

### Empty Newsletter
```
Check:
- There were NBA games yesterday
- Date is correct (it fetches yesterday's games)
- APIs are accessible
- Check logs for detailed errors
```

---

## 📊 Files Modified

### Modified
```
src/main.py              ← Logging, error handling, cleanup
src/config.py            ← Added BOT_RUN_TIME
src/fetch/scores.py      ← Retry logic, validation, logging
src/fetch/players.py     ← Safe key access, error handling
src/fetch/news.py        ← Error handling, logging
src/model/hf_client.py   ← Validation, error handling
src/send/mailer.py       ← Config validation, logging
src/send/render.py       ← Safe rendering, validation
requirements.txt         ← Added versions, added apscheduler
.env.example             ← Better comments, added BOT_RUN_TIME
```

### Created
```
src/scheduler.py         ← New scheduling module
run.py                   ← New CLI entry point
README.md                ← Complete documentation
IMPROVEMENTS.md          ← Detailed changelog
REFACTOR_SUMMARY.md      ← Before/after comparison
```

---

## 🎓 How to Use Each Mode

### Test Mode (Safe - No Email)
```bash
python run.py test

# What happens:
# 1. Fetches yesterday's NBA games
# 2. Gets top performers
# 3. Fetches latest news
# 4. Generates newsletter with AI
# 5. Saves HTML to out/newsletter_YYYY-MM-DD.html
# ❌ Does NOT send email
# ✅ Perfect for testing
```

### Once Mode (Production - Send Email)
```bash
python run.py once

# What happens:
# Same as test mode, but also:
# ✅ Sends email to NEWS_RECIPIENT
# Good for manual runs or cron jobs
```

### Schedule Mode (Always Running)
```bash
python run.py schedule

# What happens:
# ✅ Starts background scheduler
# ✅ Runs daily at BOT_RUN_TIME
# ✅ Keeps running until you stop it (Ctrl+C)
# ✅ Logs all activity
```

---

## 📈 Monitoring Logs

### Real-time logging
```bash
# While running, you'll see:
2024-11-13 09:00:00 - src.main - INFO - 🚀 Starting NBA Daily Bot
2024-11-13 09:00:01 - src.fetch.scores - INFO - ✅ Fetched 10 games
2024-11-13 09:00:05 - src.fetch.players - INFO - ✅ Fetched 50 top performers
...
```

### Log Levels
- **INFO** - Normal operations (good to see)
- **WARNING** - Non-critical issues (check if worried)
- **ERROR** - Failures that need attention (investigate)
- **DEBUG** - Detailed debugging (add to logging.basicConfig level=logging.DEBUG)

---

## 🎯 Success Criteria

After setup, you should be able to:

- [x] Run `python run.py test` and see HTML file in `out/`
- [x] Run `python run.py once` and receive email
- [x] Run `python run.py schedule` and see logs
- [x] Check logs for no ERRORs (WARNINGs are OK)
- [x] Newsletter has games, top performers, and news
- [x] Scheduler runs at configured time daily

**If all above work → You're good to deploy! 🚀**

---

## 🤝 Support

### Read These Files First
1. README.md - User guide and troubleshooting
2. IMPROVEMENTS.md - What was changed
3. REFACTOR_SUMMARY.md - Before/after comparison

### Check Logs
```bash
# When something goes wrong, check the logs
# They're very detailed now!
python run.py test 2>&1 | head -50
```

### Common Issues
See README.md section "Troubleshooting" for solutions to:
- API Errors
- SMTP Errors  
- Model Errors
- Empty Newsletter

---

## 🎉 You're All Set!

Your NBA Daily Bot is now:
- **Robust** - Handles errors gracefully
- **Reliable** - Retries on failures
- **Automated** - Runs on schedule
- **Observable** - Full logging
- **Professional** - Production-ready
- **Well-Documented** - Easy to understand

**Happy tracking! 🏀**
