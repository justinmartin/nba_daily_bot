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
from src.fetch.youtube import get_top_10_plays_video
from src.send.render import render_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

cfg = Config()

# Team tricode to full name mapping
TRICODE_TO_NAME = {
    'ATL': 'Hawks', 'BOS': 'Celtics', 'CLE': 'Cavaliers', 'NOP': 'Pelicans',
    'CHI': 'Bulls', 'DAL': 'Mavericks', 'MEM': 'Grizzlies', 'GSW': 'Warriors',
    'HOU': 'Rockets', 'LAC': 'Clippers', 'LAL': 'Lakers', 'MIA': 'Heat',
    'MIL': 'Bucks', 'MIN': 'Timberwolves', 'BRK': 'Nets', 'NYK': 'Knicks',
    'ORL': 'Magic', 'PHI': '76ers', 'PHX': 'Suns', 'POR': 'Trail Blazers',
    'SAC': 'Kings', 'SAS': 'Spurs', 'OKC': 'Thunder', 'TOR': 'Raptors',
    'UTA': 'Jazz', 'WAS': 'Wizards'
}

# Full name to tricode mapping (reverse)
NAME_TO_TRICODE = {v: k for k, v in TRICODE_TO_NAME.items()}

def build_prompt(games, news, top_performers):
    """Build a detailed prompt that generates engaging, longer content."""
    
    if not games:
        return "❌ No games played today."
    
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
    
    # Build news section with summaries if available
    news_section = []
    for n in news[:5]:
        title = n.get('title', 'No title')
        if 'summary' in n and n['summary']:
            # Include article summary for context
            news_section.append(f"• {title}\n  Context: {n['summary']}")
        else:
            news_section.append(f"• {title}")
    
    news_headlines = "\n\n".join(news_section) if news_section else ""
    
    # Count close games vs blowouts
    close_games = sum(1 for g in games if abs(g.home_score - g.away_score) <= 5)
    blowouts = sum(1 for g in games if abs(g.home_score - g.away_score) > 15)
    
    # Build performers section
    performers_section = format_performers_for_prompt(organize_game_data(games, top_performers))
    
    # Build a DETAILED prompt that generates longer, more comprehensive content
    prompt = f""" YOUR ASSIGNMENT:
You are an NBA journalist, with a style like the French media 'Trashtalk''s journalists can do, write a 10 minutes newsletter summary.
Please, and I insist, only use the information you are provided in the prompt, do not invent any data or facts no information is better than false information. Follow this rule and the following guidelines strictly:
1. Highlights the biggest upsets and dominant performances, without creating sections/titles whatsoever, without formatting either, only paragraphs.
2. Roasts the losing teams with little humor.
3. Hypes up the star performances (the ones provided in the match details, only).
4. Includes sarcastic commentary on the day's trends.
5. References at multiple of today's headlines, by reading them carefully.
6. Uses vivid, entertaining language, staying professional.
7. NO generic sports clichés or boring phrases, no emojis whatsoever.
8. CRITICAL: DO NOT copy-paste the statistics I give you in bullet points or formatted lists. The detailed stats will be shown in separate tables below your text. Instead, WEAVE the stats naturally into your narrative when relevant (e.g., "LeBron dominated with a near triple-double" instead of "LeBron James: 28pts, 7reb, 9ast").
9. Bounce back on the Headlines and tendencies of the day and in the NBA.
10. Reference the top performers naturally in your storytelling, but don't list their stats in the same format I gave you.
11. Do not introduce yourself or the newsletter at the beginning, go straight to the point.
12. Do not write sections or format characters, my goal is to put the text directly in a newsletter that is sent automatically.
13. Do not put titles or sections in the newsletter, and do not conclude with a sign-off.
14. REMEMBER: Your job is to write an ENGAGING NARRATIVE SUMMARY. The raw stats tables are automatically added below - focus on analysis, context, and storytelling, not on reformatting the data I gave you.

TONE: Professional and Sharp, witty and serious, entertaining and factual, you love NBA drama, but you want to inform your readers first.
STYLE: Mix facts with a bit of personality, be bold and opinionated, but stay professional before all. Write stories, not stat sheets.
LENGTH: Make it substantial - give readers real insights with entertainment value

DATA (use for context, don't copy the format): 
TONIGHT'S BIGGEST WINS:
{wins_text}

GAME STATS:
- Total games: {len(games)}
- Blowouts (>15 pt margin): {blowouts}
- Close games (≤5 pt margin): {close_games}

{performers_section}

TODAY'S TOP HEADLINES:
{news_headlines}

NOW WRITE YOUR NARRATIVE SUMMARY (remember: stats tables will appear below, so tell the STORY):"""
    
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
        
        # Get team tricodes for matching with performers
        winner_tricode = NAME_TO_TRICODE.get(winner_name, winner_name)
        loser_tricode = NAME_TO_TRICODE.get(loser_name, loser_name)
        
        # Get top performers for this game (filter by team tricode)
        # Use list comprehension with deduplication by player name
        winner_perf_dict = {}
        for p in all_performers:
            if p['team'] == winner_tricode and p['name'] not in winner_perf_dict:
                winner_perf_dict[p['name']] = p
        winner_performers = sorted(winner_perf_dict.values(), key=lambda x: x.get('pts', 0), reverse=True)[:3]
        
        loser_perf_dict = {}
        for p in all_performers:
            if p['team'] == loser_tricode and p['name'] not in loser_perf_dict:
                loser_perf_dict[p['name']] = p
        loser_performers = sorted(loser_perf_dict.values(), key=lambda x: x.get('pts', 0), reverse=True)[:1]
        
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
        performers_text += f"\n• {game['winner']} ({game['winner_record']}) {game['winner_score']} - {game['loser_score']} {game['loser']} ({game['loser_record']}) | Margin: {game['margin']}pts\n"
        
        if game['winner_top_performers']:
            performers_text += "  🏆 Winner's stars:\n"
            for p in game['winner_top_performers']:
                team_display = TRICODE_TO_NAME.get(p.get('team'), p.get('team', 'N/A'))
                stats = f"{p.get('pts', 0)}pts, {p.get('reb', 0)}reb, {p.get('ast', 0)}ast, FG:{p.get('fg_pct', 'N/A')}%"
                blk_stl = []
                if p.get('blk'):
                    blk_stl.append(f"{p.get('blk')}blk")
                if p.get('stl'):
                    blk_stl.append(f"{p.get('stl')}stl")
                if blk_stl:
                    stats += f", {', '.join(blk_stl)}"
                performers_text += f"    - {p['name']} ({team_display}): {stats}\n"
        
        if game['loser_top_performers']:
            performers_text += "  🔥 Leading loser:\n"
            for p in game['loser_top_performers']:
                team_display = TRICODE_TO_NAME.get(p.get('team'), p.get('team', 'N/A'))
                stats = f"{p.get('pts', 0)}pts, {p.get('reb', 0)}reb, {p.get('ast', 0)}ast, FG:{p.get('fg_pct', 'N/A')}%"
                blk_stl = []
                if p.get('blk'):
                    blk_stl.append(f"{p.get('blk')}blk")
                if p.get('stl'):
                    blk_stl.append(f"{p.get('stl')}stl")
                if blk_stl:
                    stats += f", {', '.join(blk_stl)}"
                performers_text += f"    - {p['name']} ({team_display}): {stats}\n"
    
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
        
        # Fetch top performers for each game
        logger.info("🔥 Fetching top performers...")
        all_top_performers = []
        
        for game in games:
            try:
                # Get top performers for THIS game
                performers = get_top_performers(game.id, limit=5, target_date=game.date)
                all_top_performers.extend(performers)
            except Exception as e:
                logger.debug(f"⚠️ Error fetching performers for game {game.id}: {e}")
        
        # Fetch news
        logger.info("📰 Fetching news...")
        news = fetch_news(limit=5)
        
        # Fetch Top 10 Plays video
        logger.info("🎬 Fetching Top 10 Plays video...")
        top_10_video = get_top_10_plays_video(target_date=target)
        
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
        html = render_email(summary, news, all_top_performers, games, organized_games, top_10_video)
        
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
