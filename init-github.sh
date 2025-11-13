#!/bin/bash

echo "🚀 Initializing NBA Daily Bot GitHub repository..."
echo ""

# Initialize git repo locally
echo "📦 Initializing local git repository..."
git init

# Configure git
git config user.name "Justin Martin"
git config user.email "jusmartin16@gmail.com"

# Add all files
echo "📝 Adding all files..."
git add -A

# Initial commit
echo "💾 Creating initial commit..."
git commit -m "🎉 Initial commit: NBA Daily Bot with Mistral-7B + GitHub Actions

Complete NBA daily newsletter automation:
- AI-powered summaries using Mistral-7B-Instruct
- HuggingFace OpenAI-compatible API integration  
- Automated daily scheduling via GitHub Actions
- Multi-recipient email support
- Responsive HTML email templates
- Integration with BallDontLie and ESPN APIs"

echo ""
echo "✅ Local repository initialized!"
echo ""
echo "📝 Next steps to push to GitHub:"
echo ""
echo "1. Go to GitHub: https://github.com/new"
echo "2. Create new repository: 'nba_daily_bot'"
echo "3. Copy the commands below and run them:"
echo ""
echo "   git branch -M main"
echo "   git remote add origin https://github.com/YOUR_USERNAME/nba_daily_bot.git"
echo "   git push -u origin main"
echo ""
echo "4. After pushing, add these GitHub Secrets (Settings → Secrets):"
echo "   - MAIL_SMTP_HOST"
echo "   - MAIL_SMTP_PORT"
echo "   - MAIL_SMTP_USER"
echo "   - MAIL_SMTP_PASSWORD"
echo "   - NEWS_RECIPIENT"
echo "   - BALLDONTLIE_API_KEY"
echo "   - HF_API_TOKEN"
echo "   - MODEL_ID"
echo "   - MAX_TOKENS"
echo "   - TIMEZONE"
echo "   - BOT_RUN_TIME"
echo ""
echo "5. Enable GitHub Actions in repository settings"
echo ""
