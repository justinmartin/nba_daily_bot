import sys
import logging
from datetime import datetime, timedelta
from src.config import Config
from src.fetch.scores import get_games_by_date
from src.model.hf_client import generate
import os
from src.send.mailer import send_mail
from src.fetch.players import get_top_performers
from src.fetch.news import fetch_news
from src.send.render import render_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

cfg = Config()

def build_prompt(games, news, top_performers):
    """Build a detailed prompt that generates engaging, longer content."""
    
    if not games:
        return "Write a funny NBA recap."
    
    # Get the most dominant wins (top 3 for more detail)
    dominant = sorted(games, key=lambda g: abs(g.home_score - g.away_score), reverse=True)[:3]
    
    wins_desc = []
    for g in dominant:
        winner = g.away_team if g.away_score > g.home_score else g.home_team
        loser = g.home_team if g.away_score > g.home_score else g.away_team
        margin = abs(g.home_score - g.away_score)
        winner_score = g.away_score if g.away_score > g.home_score else g.home_score
        loser_score = g.home_score if g.away_score > g.home_score else g.away_score
        wins_desc.append(f"• {winner} demolished {loser} {winner_score}-{loser_score} (margin: {margin} points)")
    
    wins_text = "\n".join(wins_desc)
    
    # Get top news headlines
    news_headlines = "\n".join([f"• {n['title']}" for n in news[:3]]) if news else ""
    
    # Count close games vs blowouts
    close_games = sum(1 for g in games if abs(g.home_score - g.away_score) <= 5)
    blowouts = sum(1 for g in games if abs(g.home_score - g.away_score) > 15)
    
    # Build a DETAILED prompt that generates longer, more comprehensive content
    prompt = f"""You are a sports journalist writing for TRASHTALK MAGAZINE - a witty, sarcastic NBA news outlet.

TONIGHT'S BIGGEST WINS:
{wins_text}

GAME STATS:
- Total games: {len(games)}
- Blowouts (>15 pt margin): {blowouts}
- Close games (≤5 pt margin): {close_games}

TODAY'S TOP HEADLINES:
{news_headlines}

YOUR ASSIGNMENT:
You are an NBA journalists, like the French media 'Trashtalk''s journalists can do, write a 10 minutes newsletter summary that:
1. Highlights the biggest upsets and dominant performances
2. Roasts the losing teams with little humor
3. Hypes up the star performances
4. Includes sarcastic commentary on the day's trends
5. References at multiple of today's headlines
6. Uses vivid, entertaining language, staying professional
7. NO generic sports clichés or boring phrases, no emojis whatsoever
Do not hesitate to bounce back on the Headlines and tendencies of the day and in the NBA
Do not hesitate to add data and statistics to support your points.
Do not introduce yourself or the newsletter at the beginning, go straight to the point.

TONE: Profesional and Sharp, witty and serious, entertaining and factual, you love NBA drama, but you want to inform your readers first.
STYLE: Mix facts with a bit of personality, be bold and opinionated, but stay professional before all.
LENGTH: Make it substantial - give readers real insights with entertainment value

NOW WRITE:"""
    
    return prompt

def run(dry_run=False):
    """Main function to generate and send NBA daily newsletter."""
    try:
        # Get yesterday's date (NBA games played between ~6pm yesterday and ~7am today)
        target = (datetime.now() - timedelta(days=1)).date()
        logger.info(f"🚀 Starting NBA Daily Bot for {target}")
        
        # Fetch games
        logger.info("📊 Fetching games...")
        games = get_games_by_date(target)
        if not games:
            logger.warning("⚠️ No games found for this date")
        
        # Fetch top performers
        logger.info("🔥 Fetching top performers...")
        all_top_performers = []
        for game in games:
            try:
                # Extract date from game object
                game_date = datetime.fromisoformat(game.date.split('T')[0]).date() if 'T' in game.date else datetime.fromisoformat(game.date).date()
                performers = get_top_performers(game.id, target_date=game_date)
                all_top_performers.extend(performers)
            except Exception as e:
                logger.debug(f"⚠️ Error fetching performers for game {game.id}: {e}")
        
        # Fetch news
        logger.info("📰 Fetching news...")
        news = fetch_news(limit=5)
        
        # Build prompt and generate summary
        logger.info("🤖 Generating newsletter content...")
        prompt = build_prompt(games, news, all_top_performers)
        logger.debug(f"Prompt preview: {prompt[:300]}...")
        summary = generate(prompt, max_tokens=cfg.MAX_TOKENS)
        logger.info(f"📝 Generated summary length: {len(summary) if summary else 0} chars")
        if not summary or not summary.strip():
            logger.warning(f"⚠️ Summary is empty or whitespace: {repr(summary[:100] if summary else 'None')}")
        
        # Render HTML
        logger.info("🎨 Rendering newsletter HTML...")
        html = render_email(summary, news, all_top_performers, games)
        
        # Save to file
        os.makedirs("out", exist_ok=True)
        output_file = f"out/newsletter_{target}.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"✅ Newsletter saved to {output_file}")
        
        # Send email
        if not dry_run:
            try:
                logger.info("📧 Sending email...")
                send_mail(html, f"NBA Daily — {target}")
                logger.info(f"✅ Email sent to {cfg.NEWS_RECIPIENT}")
            except Exception as e:
                logger.error(f"❌ Failed to send email: {e}")
                raise
        else:
            logger.info("⏭️ Dry run mode - skipping email send")
        
        logger.info("✨ Newsletter generation completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Fatal error in newsletter generation: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    run(dry_run=True)
