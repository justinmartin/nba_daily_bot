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
    
    # Build performers section
    performers_section = format_performers_for_prompt(organize_game_data(games, top_performers))
    
    # Build a DETAILED prompt that generates longer, more comprehensive content
    prompt = f"""You are a sports journalist writing for TRASHTALK MAGAZINE - a witty, sarcastic NBA news outlet.

TONIGHT'S BIGGEST WINS:
{wins_text}

GAME STATS:
- Total games: {len(games)}
- Blowouts (>15 pt margin): {blowouts}
- Close games (≤5 pt margin): {close_games}

{performers_section}

TODAY'S TOP HEADLINES:
{news_headlines}

YOUR ASSIGNMENT:
You are an NBA journalists, with a style like the French media 'Trashtalk''s journalists can do, write a 10 minutes newsletter summary that:
1. Highlights the biggest upsets and dominant performances
2. Roasts the losing teams with little humor
3. Hypes up the star performances (especially the ones provided in the match details)
4. Includes sarcastic commentary on the day's trends
5. References at multiple of today's headlines
6. Uses vivid, entertaining language, staying professional
7. NO generic sports clichés or boring phrases, no emojis whatsoever
8. Add detailed statistics and data from the games to support your points IF AND ONLY IF you have the data from the games and not old data. I'd rather have no data than false data.
Do not hesitate to bounce back on the Headlines and tendencies of the day and in the NBA
Do not hesitate to reference the top performers data provided to add credibility and excitement to your coverage. Use real data from the games, not made-up figures or old ones. I'd rather have no data than false data.
Do not introduce yourself or the newsletter at the beginning, go straight to the point.
Do not write sections or format characters, my goal is to put the text directly in a newsletter that is sent automatically.
Do not put titles or sections in the newsletter, and do not conclude with a sign-off.

TONE: Profesional and Sharp, witty and serious, entertaining and factual, you love NBA drama, but you want to inform your readers first.
STYLE: Mix facts with a bit of personality, be bold and opinionated, but stay professional before all.
LENGTH: Make it substantial - give readers real insights with entertainment value

NOW WRITE:"""
    
    return prompt

def organize_game_data(games, all_performers):
    """
    Organize game data with top performers grouped by match.
    Returns list of dicts with: winner, loser, scores, records, and their top performers.
    """
    organized_games = []
    
    for game in games:
        # Determine winner and loser
        is_home_winner = game.home_score > game.away_score
        winner_name = game.home_team if is_home_winner else game.away_team
        loser_name = game.away_team if is_home_winner else game.home_team
        winner_score = game.home_score if is_home_winner else game.away_score
        loser_score = game.away_score if is_home_winner else game.home_score
        
        # Get records (handle None values)
        if is_home_winner:
            winner_record = f"{game.home_wins}-{game.home_losses}" if (game.home_wins and game.home_losses) else "?"
            loser_record = f"{game.away_wins}-{game.away_losses}" if (game.away_wins and game.away_losses) else "?"
        else:
            winner_record = f"{game.away_wins}-{game.away_losses}" if (game.away_wins and game.away_losses) else "?"
            loser_record = f"{game.home_wins}-{game.home_losses}" if (game.home_wins and game.home_losses) else "?"
        
        # Get top performers for this game (filter by team)
        winner_performers = [p for p in all_performers if p['team'] == winner_name][:3]
        loser_performers = [p for p in all_performers if p['team'] == loser_name][:1]
        
        # Sort by points to ensure we get the best
        winner_performers = sorted(winner_performers, key=lambda x: x.get('pts', 0), reverse=True)[:3]
        loser_performers = sorted(loser_performers, key=lambda x: x.get('pts', 0), reverse=True)[:1]
        
        game_data = {
            "id": game.id,
            "date": game.date,
            "winner": winner_name,
            "loser": loser_name,
            "winner_score": winner_score,
            "loser_score": loser_score,
            "margin": abs(winner_score - loser_score),
            "winner_record": winner_record,
            "loser_record": loser_record,
            "winner_top_performers": winner_performers,
            "loser_top_performers": loser_performers
        }
        organized_games.append(game_data)
    
    return organized_games

def format_performers_for_prompt(organized_games):
    """Format organized game data with performers for the LLM prompt."""
    if not organized_games:
        return ""
    
    performers_text = "MATCH DETAILS WITH TOP PERFORMERS:\n"
    
    for game in organized_games:
        performers_text += f"\n• {game['winner']} {game['winner_score']} - {game['loser']} {game['loser_score']}\n"
        
        if game['winner_top_performers']:
            performers_text += "  🏆 Winner's stars:\n"
            for p in game['winner_top_performers']:
                stats = f"{p.get('pts', 0)}pts, {p.get('reb', 0)}reb, {p.get('ast', 0)}ast"
                performers_text += f"    - {p['name']}: {stats}\n"
        
        if game['loser_top_performers']:
            performers_text += "  Leading loser:\n"
            for p in game['loser_top_performers']:
                stats = f"{p.get('pts', 0)}pts, {p.get('reb', 0)}reb, {p.get('ast', 0)}ast"
                performers_text += f"    - {p['name']}: {stats}\n"
    
    return performers_text

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
        
        # Organize game data with performers
        logger.info("📊 Organizing game data with top performers...")
        organized_games = organize_game_data(games, all_top_performers)
        
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
        html = render_email(summary, news, all_top_performers, games, organized_games)
        
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
