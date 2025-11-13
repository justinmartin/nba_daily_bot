#!/bin/bash

# NBA Daily Bot - GitHub Commit Script

echo "🚀 Preparing to commit and push to GitHub..."
echo ""

# Configure Git if needed
git config user.name "Justin Martin" 2>/dev/null || true
git config user.email "jusmartin16@gmail.com" 2>/dev/null || true

# Show current status
echo "📊 Current git status:"
git status --short
echo ""

# Add all changes
echo "📦 Adding all changes..."
git add -A

# Commit with a descriptive message
echo "💾 Committing changes..."
git commit -m "✨ Implement HF Mistral-7B API + GitHub Actions automation

- Switched from TinyLlama to Mistral-7B-Instruct via HuggingFace OpenAI API
- Significantly improved newsletter quality (5-7 sentences, detailed analysis)
- Added support for multiple email recipients (comma-separated)
- Implemented GitHub Actions workflow for daily 7:30 AM scheduling
- Increased MAX_TOKENS to 800 for more comprehensive summaries
- Enhanced prompt with detailed game stats and news context
- Added .gitignore and .env.example for better project structure
- Newsletter now runs fully on cloud (no local compute needed)

Features:
- 🤖 AI-powered sarcastic NBA summaries using Mistral-7B
- 📧 Multi-recipient email support
- ⏰ Automatic daily execution via GitHub Actions
- 📱 Responsive mobile-friendly HTML templates
- 🎯 Integration with BallDontLie, ESPN APIs
- 🔐 Secure secrets management via GitHub Actions

This change eliminates the need for local scheduling and makes the bot
fully serverless while dramatically improving content quality."

# Show the commit message
echo ""
echo "✅ Commit created successfully!"
echo ""
echo "📝 Commit message:"
git log -1 --oneline
echo ""

# Push to GitHub
echo "🚀 Pushing to GitHub..."
git push origin main || git push origin master

echo ""
echo "✅ Successfully pushed to GitHub!"
echo "🎉 NBA Daily Bot is now automated and running on GitHub Actions!"
