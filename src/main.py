
import sys
import logging
from datetime import datetime, timedelta
from src.config import Config
from src.fetch.scores import get_games_by_date
from src.fetch.schedule import get_upcoming_games
from src.model.hf_client import generate
import os
from src.send.mailer import send_mail
from src.fetch.players import get_top_performers
from src.fetch.news import fetch_news
from src.fetch.youtube import get_top_10_plays_video
from src.send.render import render_email, perf_details
from src.send.perf_card import perf_card_png, match_header_png
from src.fetch import extras

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

cfg = Config()

TRICODE_TO_NAME = {
    'ATL': 'Hawks', 'BOS': 'Celtics', 'BRK': 'Nets', 'CHA': 'Hornets',
    'CHI': 'Bulls', 'CLE': 'Cavaliers', 'DAL': 'Mavericks', 'DEN': 'Nuggets',
    'DET': 'Pistons', 'GSW': 'Warriors', 'HOU': 'Rockets', 'IND': 'Pacers',
    'LAC': 'Clippers', 'LAL': 'Lakers', 'MEM': 'Grizzlies', 'MIA': 'Heat',
    'MIL': 'Bucks', 'MIN': 'Timberwolves', 'NOP': 'Pelicans', 'NYK': 'Knicks',
    'OKC': 'Thunder', 'ORL': 'Magic', 'PHI': '76ers', 'PHX': 'Suns',
    'POR': 'Trail Blazers', 'SAC': 'Kings', 'SAS': 'Spurs', 'TOR': 'Raptors',
    'UTA': 'Jazz', 'WAS': 'Wizards',
    'UTAH': 'Jazz', 'NY': 'Knicks', 'SA': 'Spurs', 'NO': 'Pelicans',
    'BKN': 'Nets', 'GS': 'Warriors', 'WSH': 'Wizards'
}

NAME_TO_TRICODE = {v: k for k, v in TRICODE_TO_NAME.items()}

def build_prompt(games, news, top_performers):
    if not games:
        return "❌ No games played today."
    
    dominant = sorted(games, key=lambda g: abs(g.home_score - g.away_score), reverse=True)[:3]
    
    wins_desc = []
    for g in dominant:
        winner = g.away_team if g.away_score > g.home_score else g.home_team
        loser = g.home_team if g.away_score > g.home_score else g.away_team
        margin = abs(g.home_score - g.away_score)
        winner_score = g.away_score if g.away_score > g.home_score else g.home_score
        loser_score = g.home_score if g.away_score > g.home_score else g.away_score
        wins_desc.append(f"• {winner} bat {loser} {winner_score}-{loser_score} (écart : {margin} pts)")
    
    wins_text = "\n".join(wins_desc)
    
    news_section = []
    for n in news[:8]:
        source = n.get('source', 'News')
        title = n.get('title', 'No title')
        summary = n.get('summary', '')
        if summary:
            news_section.append(f"• [{source}] {title}\n  {summary[:220].strip()}")
        else:
            news_section.append(f"• [{source}] {title}")
    news_headlines = "\n\n".join(news_section) if news_section else ""
    
    close_games = sum(1 for g in games if abs(g.home_score - g.away_score) <= 5)
    blowouts = sum(1 for g in games if abs(g.home_score - g.away_score) > 15)
    
    all_games_summary = []
    for g in games:
        away_record = f"({g.away_wins}-{g.away_losses})" if g.away_wins is not None else ""
        home_record = f"({g.home_wins}-{g.home_losses})" if g.home_wins is not None else ""
        margin = abs(g.away_score - g.home_score)
        all_games_summary.append(f"• {g.away_team} {away_record} {g.away_score} - {g.home_score} {g.home_team} {home_record} | Margin: {margin}pts")
    games_summary_text = "\n".join(all_games_summary)
    
    performers_section = format_performers_for_prompt(organize_game_data(games, top_performers))
    
    prompt = f"""TA MISSION :
Tu es journaliste NBA, avec le style des rédacteurs de Trashtalk (le média basket français) : drôle, piquant, mais toujours informé. Rédige EN FRANÇAIS le récap de la nuit NBA pour une newsletter du matin.

RÈGLES (à respecter strictement) :
1. Écris uniquement en français. Les termes basket courants (game-winner, triple-double, clutch, run…) sont permis, comme chez Trashtalk.
2. N'utilise QUE les informations des DONNÉES ci-dessous. Ne cite jamais un joueur absent des données, n'affirme jamais de mémoire l'équipe, l'âge, le contrat, un transfert, une blessure ou la salle d'un joueur : les effectifs changent chaque saison et ta mémoire est périmée. Mieux vaut ne rien dire que dire faux.
3. Statistiques : uniquement celles fournies, sans arrondir à ta façon ni en inventer.
4. Mets en avant les gros cartons, les surprises et les performances individuelles des données ; chambre gentiment les perdants, sans méchanceté.
5. Reprends 2 ou 3 actus NBA des TITRES DU JOUR quand elles sont liées aux matchs ; ignore tout ce qui ne concerne pas la NBA.
6. Pas de titres, pas de sections, pas de listes, pas de mise en forme, pas d'emojis : uniquement des paragraphes de texte brut, séparés par une ligne vide.
7. Pas d'introduction (« Bonjour », « Bienvenue ») ni de signature : entre directement dans le vif.
8. Longueur : 4 à 6 paragraphes, du plus marquant au plus anecdotique.

TON : vif, imagé, opinions assumées, mais l'info d'abord. Pas de clichés sportifs creux.

DONNÉES :
PLUS GROS ÉCARTS DE LA NUIT :
{wins_text}

STATS DE LA SOIRÉE :
- Matchs : {len(games)}
- Cartons (écart > 15 pts) : {blowouts}
- Matchs serrés (écart ≤ 5 pts) : {close_games}

TOUS LES MATCHS :
{games_summary_text}

{performers_section}

TITRES DU JOUR :
{news_headlines}

ÉCRIS LE RÉCAP :"""
    
    return prompt

def organize_game_data(games, all_performers):
    organized_games = []
    
    for game in games:
        is_home_winner = game.home_score > game.away_score
        winner_name = game.home_team if is_home_winner else game.away_team
        loser_name = game.away_team if is_home_winner else game.home_team
        winner_score = game.home_score if is_home_winner else game.away_score
        loser_score = game.away_score if is_home_winner else game.home_score
        
        if is_home_winner:
            winner_record = f"{game.home_wins}-{game.home_losses}" if (game.home_wins is not None and game.home_losses is not None) else ""
            loser_record = f"{game.away_wins}-{game.away_losses}" if (game.away_wins is not None and game.away_losses is not None) else ""
        else:
            winner_record = f"{game.away_wins}-{game.away_losses}" if (game.away_wins is not None and game.away_losses is not None) else ""
            loser_record = f"{game.home_wins}-{game.home_losses}" if (game.home_wins is not None and game.home_losses is not None) else ""
        
        winner_tricode = NAME_TO_TRICODE.get(winner_name, winner_name)
        loser_tricode = NAME_TO_TRICODE.get(loser_name, loser_name)
        
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
        
        home_record = f"{game.home_wins}-{game.home_losses}" if (game.home_wins is not None and game.home_losses is not None) else ""
        away_record = f"{game.away_wins}-{game.away_losses}" if (game.away_wins is not None and game.away_losses is not None) else ""
        game_data = {
            "id": game.id,
            "date": game.date,
            # L'affiche telle qu'elle est : extérieur à gauche, domicile à droite
            "away": game.away_team, "home": game.home_team,
            "away_score": game.away_score, "home_score": game.home_score,
            "away_record": away_record, "home_record": home_record,
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
    if not organized_games:
        return ""
    
    performers_text = "MATCH DETAILS WITH TOP PERFORMERS:\n"
    
    for game in organized_games:
        performers_text += f"\n• {game['winner']} ({game['winner_record']}) {game['winner_score']} - {game['loser_score']} {game['loser']} ({game['loser_record']}) | Margin: {game['margin']}pts\n"
        
        if game['winner_top_performers']:
            performers_text += "  🏆 Winner's stars:\n"
            for p in game['winner_top_performers']:
                team_tricode = p.get('team', 'N/A')
                team_display = TRICODE_TO_NAME.get(team_tricode, team_tricode)
                
                stats = f"{p.get('pts', 0)}pts, {p.get('reb', 0)}reb, {p.get('ast', 0)}ast, FG:{p.get('fg_pct', 'N/A')}%"
                
                blk_stl = []
                if p.get('blk'):
                    blk_stl.append(f"{p.get('blk')}blk")
                if p.get('stl'):
                    blk_stl.append(f"{p.get('stl')}stl")
                if blk_stl:
                    stats += f", {', '.join(blk_stl)}"
                
                performers_text += f"    - {p['name']} ({team_tricode} - {team_display}): {stats}\n"
        
        if game['loser_top_performers']:
            performers_text += "  🔥 Leading loser:\n"
            for p in game['loser_top_performers']:
                team_tricode = p.get('team', 'N/A')
                team_display = TRICODE_TO_NAME.get(team_tricode, team_tricode)
                stats = f"{p.get('pts', 0)}pts, {p.get('reb', 0)}reb, {p.get('ast', 0)}ast, FG:{p.get('fg_pct', 'N/A')}%"
                blk_stl = []
                if p.get('blk'):
                    blk_stl.append(f"{p.get('blk')}blk")
                if p.get('stl'):
                    blk_stl.append(f"{p.get('stl')}stl")
                if blk_stl:
                    stats += f", {', '.join(blk_stl)}"
                performers_text += f"    - {p['name']} ({team_tricode} - {team_display}): {stats}\n"
    
    return performers_text

def send_schedule_only(target, dry_run=False):
    """Pas de match la veille : si des matchs sont prévus ce soir (reprise de saison,
    lendemain de break), envoie un mail court avec le programme et les news.
    Sinon (vraie intersaison), n'envoie rien."""
    today = datetime.now().date()
    try:
        upcoming = get_upcoming_games(today)
    except Exception as e:
        logger.warning(f"⚠️ Failed to fetch upcoming games: {e}")
        upcoming = []

    if not upcoming:
        logger.info("✨ No games last night and none tonight - no newsletter (off-season)")
        return

    logger.info(f"📅 No games last night, {len(upcoming)} tonight - sending schedule-only newsletter")
    news = fetch_news(include_content=False)
    summary = (
        f"Pas de match cette nuit. {len(upcoming)} match(s) au programme ce soir : "
        "retrouvez les horaires et diffuseurs ci-dessous, ainsi que les dernières news."
    )
    html = render_email(summary, news, upcoming_games=upcoming, teams=extras.get_teams())

    os.makedirs("out", exist_ok=True)
    output_file = f"out/newsletter_{target}_schedule.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"✅ Newsletter saved to {output_file}")

    if dry_run:
        logger.info("⏭️ Dry run mode - skipping email send")
        return
    send_mail(html, f"NBA Daily — Programme du {today}")
    logger.info(f"✅ Email sent to {cfg.NEWS_RECIPIENT}")

def run(dry_run=False):
    try:
        
        target = (datetime.now() - timedelta(days=1)).date()
        logger.info(f"🚀 Starting NBA Daily Bot for {target}")
        
        logger.info("📊 Fetching games...")
        try:
            games = get_games_by_date(target)
        except Exception as e:
            logger.error(f"❌ Failed to fetch games due to API timeout/error: {e}")
            logger.warning("⚠️ Skipping newsletter - stats.nba.com is unavailable")
            return  # Exit code 0 (pas d'email envoyé, mais pas d'erreur non plus)
        
        if not games:
            logger.warning("⚠️ No games found for this date")
            send_schedule_only(target, dry_run)  # Intersaison / jours off : programme du soir si matchs
            return
        
        logger.info("🔥 Fetching top performers...")
        all_top_performers = []
        
        from datetime import datetime as dt
        game_date_obj = dt.strptime(games[0].date, '%Y-%m-%d').date() if games else target
        
        try:
            logger.info(f"Fetching all top performers for {game_date_obj}...")
            all_top_performers = get_top_performers('', limit=50, target_date=game_date_obj)
            logger.info(f"✅ Found {len(all_top_performers)} total performers")
        except Exception as e:
            logger.error(f"⚠️ Failed to fetch top performers: {e}")
            all_top_performers = []
        
        logger.info("📰 Fetching news...")
        news = fetch_news(include_content=False)  # 3 Trashtalk + 5 Athletic RSS items
        
        logger.info("🎬 Fetching Top 10 Plays video...")
        top_10_video = get_top_10_plays_video(target_date=target)
        
        logger.info("� Fetching upcoming games schedule...")
        today = datetime.now().date()
        try:
            upcoming = get_upcoming_games(today)
            logger.info(f"✅ Found {len(upcoming)} upcoming games for today")
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch upcoming games: {e}")
            upcoming = []
        
        logger.info("�📊 Organizing game data with top performers...")
        organized_games = organize_game_data(games, all_top_performers)
        
        logger.info("🤖 Generating newsletter content...")
        prompt = build_prompt(games, news, all_top_performers)
        logger.debug(f"Prompt preview: {prompt[:300]}...")
        
        try:
            summary = generate(prompt, max_tokens=cfg.MAX_TOKENS)
        except Exception as e:
            # Pas de résumé (plus de crédits, modèle indisponible…) : on envoie quand même scores, stats et news
            logger.error(f"❌ AI summary unavailable, sending the newsletter without it: {e}")
            print(f"::warning::Résumé IA indisponible : {str(e)[:200]}")
            reason = "plus de crédits pour le modèle d'IA" if "credits" in str(e).lower() else "le service d'IA n'a pas répondu"
            summary = f"Pas de récap rédigé aujourd'hui ({reason}). Les scores, les meilleurs joueurs et les actus sont juste en dessous."
        logger.info(f"📝 Generated summary length: {len(summary) if summary else 0} chars")
        
        if not summary or not summary.strip():
            logger.warning(f"⚠️ Summary is empty or whitespace: {repr(summary[:100] if summary else 'None')}")
        
        # Habillage des matchs : logos et couleurs, résumé Trashtalk (sinon ESPN), vidéo YouTube de la NBA
        logger.info("🎬 Fetching recaps, videos and team colors...")
        teams = extras.get_teams()
        tt = extras.night_items(extras.trashtalk_items(30), game_date_obj)
        links = {}
        for g in organized_games:
            url = extras.trashtalk_for_game(tt, g['winner'], g['loser'], g['winner_score'], g['loser_score'])
            links[g['id']] = {'kind': 'trashtalk', 'url': url} if url else {'kind': 'espn', 'url': extras.espn_recap(g['id'])}
        try:
            videos, nightly_video = extras.highlight_videos(games, game_date_obj)
        except Exception as e:
            logger.warning(f"⚠️ Videos unavailable: {e}")
            videos, nightly_video = {}, None

        # La perf de la nuit, dessinée en image (logo en filigrane, rendu identique dans toutes les messageries)
        perf_png = None
        if all_top_performers:
            best = max(all_top_performers, key=lambda p: p.get('pts', 0))
            t = teams.get(best.get('team')) or {}
            if t:
                perf_png = perf_card_png(best.get('name', ''), perf_details(best), int(best.get('pts', 0)), t['color'], t['abbr'])

        # Le haut de chaque carte de match, dessiné en image (logos en filigrane)
        images = {"perf": perf_png} if perf_png else {}
        for i, g in enumerate(organized_games):
            ta, th = teams.get(g['away']), teams.get(g['home'])
            if ta and th:
                png = match_header_png({**ta, 'name': g['away'], 'record': g.get('away_record'), 'score': g['away_score']},
                                       {**th, 'name': g['home'], 'record': g.get('home_record'), 'score': g['home_score']})
                if png:
                    images[f"m{i}"] = png
        header_imgs = {g['id']: f"cid:m{i}" for i, g in enumerate(organized_games) if f"m{i}" in images}

        logger.info("🎨 Rendering newsletter HTML...")
        html = render_email(summary, news, all_top_performers, games, organized_games, top_10_video, upcoming,
                            teams=teams, links=links, videos=videos, nightly_video=nightly_video, tt_nightly=extras.trashtalk_nightly(tt),
                            perf_img="cid:perf" if perf_png else None, header_imgs=header_imgs)
        
        os.makedirs("out", exist_ok=True)  # Crée le dossier out/ si inexistant
        output_file = f"out/newsletter_{target}.html"
        with open(output_file, "w", encoding="utf-8") as f:
            # Aperçu local : les images à côté du fichier
            preview = html
            for cid in images:
                preview = preview.replace(f'"cid:{cid}"', f'"{cid}_{target}.png"')
            f.write(preview)
        for cid, png in images.items():
            with open(f"out/{cid}_{target}.png", "wb") as f:
                f.write(png)
        logger.info(f"✅ Newsletter saved to {output_file}")
        
        if not dry_run:
            try:
                logger.info("📧 Sending email...")
                send_mail(html, f"NBA Daily — {target}", images=images or None)
                logger.info(f"✅ Email sent to {cfg.NEWS_RECIPIENT}")
            except Exception as e:
                logger.error(f"❌ Failed to send email: {e}")
                raise  # On remonte l'erreur pour signaler le problème
        else:
            logger.info("⏭️ Dry run mode - skipping email send")
        
        logger.info("✨ Newsletter generation completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Fatal error in newsletter generation: {e}", exc_info=True)
        raise  # On remonte l'exception

if __name__ == "__main__":
    run(dry_run=True)
