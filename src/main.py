"""
Orchestrateur principal du bot NBA Daily.

Ce module coordonne toutes les étapes de génération de la newsletter :
1. Récupération des scores NBA (nba_api)
2. Récupération des top performers (statistiques joueurs)
3. Récupération des actualités ESPN (RSS feed)
4. Récupération de la vidéo Top 10 Plays (YouTube)
5. Génération du texte de la newsletter (IA HuggingFace)
6. Rendu HTML de l'email
7. Envoi de l'email aux destinataires

Fonctionnement:
    - Par défaut, génère la newsletter pour les matchs de la veille
    - Peut être exécuté en mode dry-run (test sans envoi d'email)
    - Gère gracieusement les erreurs d'API (timeout, indisponibilité)
"""

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

# === CONFIGURATION DU LOGGING ===
# Configure l'affichage des logs avec timestamp, nom du module, niveau et message
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === CHARGEMENT DE LA CONFIGURATION ===
cfg = Config()

# === MAPPAGES DES NOMS D'ÉQUIPES ===
# Convertit les tricodes NBA (ex: "LAL") en noms complets (ex: "Lakers")
# Source: Liste officielle des 30 équipes NBA (saison 2024-2025)
TRICODE_TO_NAME = {
    'ATL': 'Hawks', 'BOS': 'Celtics', 'CLE': 'Cavaliers', 'NOP': 'Pelicans',
    'CHI': 'Bulls', 'DAL': 'Mavericks', 'MEM': 'Grizzlies', 'GSW': 'Warriors',
    'HOU': 'Rockets', 'LAC': 'Clippers', 'LAL': 'Lakers', 'MIA': 'Heat',
    'MIL': 'Bucks', 'MIN': 'Timberwolves', 'BRK': 'Nets', 'NYK': 'Knicks',
    'ORL': 'Magic', 'PHI': '76ers', 'PHX': 'Suns', 'POR': 'Trail Blazers',
    'SAC': 'Kings', 'SAS': 'Spurs', 'OKC': 'Thunder', 'TOR': 'Raptors',
    'UTA': 'Jazz', 'WAS': 'Wizards'
}

# Mapping inverse: nom complet → tricode (utilisé pour matcher les stats des joueurs)
NAME_TO_TRICODE = {v: k for k, v in TRICODE_TO_NAME.items()}


def build_prompt(games, news, top_performers):
    """
    Construit le prompt détaillé pour l'IA qui génère le texte de la newsletter.
    
    Ce prompt guide l'IA (HuggingFace) pour générer un résumé style "TrashTalk" :
    - Ton professionnel mais avec de la personnalité
    - Focus sur les faits et statistiques réelles
    - Humour et sarcasme mesurés
    - Pas de données inventées (uniquement celles fournies)
    
    Args:
        games (list[Game]): Liste des matchs de la soirée
        news (list[dict]): Actualités ESPN (title, link, published)
        top_performers (list[dict]): Stats des meilleurs joueurs (pts, reb, ast, etc.)
    
    Returns:
        str: Prompt complet prêt à être envoyé à l'IA
        
    Structure du prompt:
        1. Instructions de style et ton (guidelines)
        2. Données des plus gros écarts
        3. Statistiques globales (total matchs, close games, blowouts)
        4. Détails des matchs avec top performers
        5. Titres des actualités du jour
    """
    # === CAS SPÉCIAL: Aucun match joué ===
    if not games:
        return "❌ No games played today."
    
    # === ÉTAPE 1: Identifier les victoires dominantes (top 3 écarts) ===
    # Tri par écart de score décroissant pour trouver les "blowouts"
    dominant = sorted(games, key=lambda g: abs(g.home_score - g.away_score), reverse=True)[:3]
    
    wins_desc = []
    for g in dominant:
        # Détermine le gagnant et le perdant
        winner = g.away_team if g.away_score > g.home_score else g.home_team
        loser = g.home_team if g.away_score > g.home_score else g.away_team
        margin = abs(g.home_score - g.away_score)
        winner_score = g.away_score if g.away_score > g.home_score else g.home_score
        loser_score = g.home_score if g.away_score > g.home_score else g.away_score
        wins_desc.append(f"• {winner} demolished {loser} {winner_score}-{loser_score} (margin: {margin} points)")
    
    wins_text = "\n".join(wins_desc)
    
    # === ÉTAPE 2: Extraire les titres des actualités (top 5) ===
    news_headlines = "\n".join([f"• {n['title']}" for n in news[:5]]) if news else ""
    
    # === ÉTAPE 3: Calculer les statistiques de la soirée ===
    # Close games = écart ≤ 5 points (matchs serrés)
    close_games = sum(1 for g in games if abs(g.home_score - g.away_score) <= 5)
    # Blowouts = écart > 15 points (victoires écrasantes)
    blowouts = sum(1 for g in games if abs(g.home_score - g.away_score) > 15)
    
    # === ÉTAPE 4: Organiser les données des matchs avec performers ===
    performers_section = format_performers_for_prompt(organize_game_data(games, top_performers))
    
    # === ÉTAPE 5: Construire le prompt final pour l'IA ===
    prompt = f""" YOUR ASSIGNMENT:
You are an NBA journalists, with a style like the French media 'Trashtalk''s journalists can do, write a 10 minutes newsletter summary.
Please, and I insist, only use the information you are provided in the prompt, do not invent any data or facts no information is better than false information. Follow this rule and the following guidelines strictly:
1. Highlights the biggest upsets and dominant performances, without creating sections/titles whatsoever, without formatting either, only paragraphs.
2. Roasts the losing teams with little humor.
3. Hypes up the star performances (the ones provided in the match details, only).
4. Includes sarcastic commentary on the day's trends.
5. References at multiple of today's headlines, by reading them carefully.
6. Uses vivid, entertaining language, staying professional.
7. NO generic sports clichés or boring phrases, no emojis whatsoever.
8. Add detailed statistics and data from the games to support your points IF AND ONLY IF you have the data from the games and not old data. I'd rather have no data than false data.
9. Bounce back on the Headlines and tendencies of the day and in the NBA.
10. Reference the top performers data provided to add credibility and excitement to your coverage. Use real data from the games, not made-up figures or old ones. I'd rather have no data than false data.
11. Do not introduce yourself or the newsletter at the beginning, go straight to the point.
12. Do not write sections or format characters, my goal is to put the text directly in a newsletter that is sent automatically.
13. Do not put titles or sections in the newsletter, and do not conclude with a sign-off.

TONE: Profesional and Sharp, witty and serious, entertaining and factual, you love NBA drama, but you want to inform your readers first.
STYLE: Mix facts with a bit of personality, be bold and opinionated, but stay professional before all.
LENGTH: Make it substantial - give readers real insights with entertainment value

DATA : 
TONIGHT'S BIGGEST WINS:
{wins_text}

GAME STATS:
- Total games: {len(games)}
- Blowouts (>15 pt margin): {blowouts}
- Close games (≤5 pt margin): {close_games}

{performers_section}

TODAY'S TOP HEADLINES:
{news_headlines}

NOW WRITE:"""
    
    return prompt


def organize_game_data(games, all_performers):
    """
    Organise les données des matchs avec leurs top performers respectifs.
    
    Pour chaque match, cette fonction :
    1. Identifie le gagnant et le perdant
    2. Récupère le bilan (wins-losses) de chaque équipe
    3. Associe les meilleurs joueurs à leur équipe
    4. Déduplique les joueurs (parfois listés plusieurs fois)
    5. Trie les performers par points marqués
    
    Args:
        games (list[Game]): Liste des matchs avec scores
        all_performers (list[dict]): Tous les top performers de la soirée
                                     (chaque dict contient: name, team, pts, reb, ast, etc.)
    
    Returns:
        list[dict]: Liste de dictionnaires avec structure:
            {
                'id': str,                        # ID du match
                'date': str,                      # Date du match
                'winner': str,                    # Nom de l'équipe gagnante
                'loser': str,                     # Nom de l'équipe perdante
                'winner_score': int,              # Score du gagnant
                'loser_score': int,               # Score du perdant
                'margin': int,                    # Écart de points
                'winner_record': str,             # Bilan gagnant (ex: "15-3")
                'loser_record': str,              # Bilan perdant (ex: "8-10")
                'winner_top_performers': list,    # Top 3 joueurs du gagnant
                'loser_top_performers': list      # Meilleur joueur du perdant
            }
    
    Exemple:
        >>> games = [Game(id="123", home_team="Lakers", away_team="Celtics", ...)]
        >>> performers = [{'name': 'LeBron James', 'team': 'LAL', 'pts': 30, ...}]
        >>> organize_game_data(games, performers)
        [{'winner': 'Lakers', 'loser': 'Celtics', 'winner_score': 110, ...}]
    """
    organized_games = []
    
    for game in games:
        # === ÉTAPE 1: Déterminer le gagnant et le perdant ===
        is_home_winner = game.home_score > game.away_score
        winner_name = game.home_team if is_home_winner else game.away_team
        loser_name = game.away_team if is_home_winner else game.home_team
        winner_score = game.home_score if is_home_winner else game.away_score
        loser_score = game.away_score if is_home_winner else game.home_score
        
        # === ÉTAPE 2: Récupérer les bilans (gère les valeurs None) ===
        if is_home_winner:
            winner_record = f"{game.home_wins}-{game.home_losses}" if (game.home_wins and game.home_losses) else "?"
            loser_record = f"{game.away_wins}-{game.away_losses}" if (game.away_wins and game.away_losses) else "?"
        else:
            winner_record = f"{game.away_wins}-{game.away_losses}" if (game.away_wins and game.away_losses) else "?"
            loser_record = f"{game.home_wins}-{game.home_losses}" if (game.home_wins and game.home_losses) else "?"
        
        # === ÉTAPE 3: Convertir les noms d'équipe en tricodes ===
        # Les performers utilisent des tricodes ("LAL"), les games utilisent des noms complets ("Lakers")
        winner_tricode = NAME_TO_TRICODE.get(winner_name, winner_name)
        loser_tricode = NAME_TO_TRICODE.get(loser_name, loser_name)
        
        # === ÉTAPE 4: Filtrer les top performers pour ce match ===
        # Dédupliquer par nom de joueur (parfois un joueur apparaît plusieurs fois)
        winner_perf_dict = {}
        for p in all_performers:
            if p['team'] == winner_tricode and p['name'] not in winner_perf_dict:
                winner_perf_dict[p['name']] = p
        # Top 3 scoreurs de l'équipe gagnante
        winner_performers = sorted(winner_perf_dict.values(), key=lambda x: x.get('pts', 0), reverse=True)[:3]
        
        loser_perf_dict = {}
        for p in all_performers:
            if p['team'] == loser_tricode and p['name'] not in loser_perf_dict:
                loser_perf_dict[p['name']] = p
        # Meilleur scoreur de l'équipe perdante (1 seul)
        loser_performers = sorted(loser_perf_dict.values(), key=lambda x: x.get('pts', 0), reverse=True)[:1]
        
        # === ÉTAPE 5: Construire le dictionnaire du match ===
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
    """
    Formate les données des matchs et performers pour le prompt de l'IA.
    
    Génère une section texte lisible par l'IA avec:
    - Score du match avec bilans des équipes
    - Top 3 joueurs de l'équipe gagnante (stats complètes)
    - Meilleur joueur de l'équipe perdante
    
    Args:
        organized_games (list[dict]): Matchs organisés avec leurs performers
                                      (retour de organize_game_data)
    
    Returns:
        str: Texte formaté pour le prompt, par exemple:
             "MATCH DETAILS WITH TOP PERFORMERS:
             
             • Lakers (15-3) 110 - 95 Celtics (12-6) | Margin: 15pts
               🏆 Winner's stars:
                 - LeBron James (Lakers): 30pts, 8reb, 7ast, FG:55%
                 - Anthony Davis (Lakers): 25pts, 12reb, 3ast, FG:60%, 3blk
               🔥 Leading loser:
                 - Jayson Tatum (Celtics): 28pts, 6reb, 5ast, FG:48%"
    
    Format:
        Chaque ligne est optimisée pour être comprise par l'IA et contient
        uniquement des données vérifiées (pas de valeurs inventées).
    """
    if not organized_games:
        return ""
    
    performers_text = "MATCH DETAILS WITH TOP PERFORMERS:\n"
    
    for game in organized_games:
        # === Ligne de score du match ===
        performers_text += f"\n• {game['winner']} ({game['winner_record']}) {game['winner_score']} - {game['loser_score']} {game['loser']} ({game['loser_record']}) | Margin: {game['margin']}pts\n"
        
        # === Top performers de l'équipe GAGNANTE ===
        if game['winner_top_performers']:
            performers_text += "  🏆 Winner's stars:\n"
            for p in game['winner_top_performers']:
                # Convertit le tricode en nom complet (ex: "LAL" → "Lakers")
                team_display = TRICODE_TO_NAME.get(p.get('team'), p.get('team', 'N/A'))
                
                # Stats de base: points, rebonds, passes, % au tir
                stats = f"{p.get('pts', 0)}pts, {p.get('reb', 0)}reb, {p.get('ast', 0)}ast, FG:{p.get('fg_pct', 'N/A')}%"
                
                # Stats défensives optionnelles (contres et interceptions)
                blk_stl = []
                if p.get('blk'):
                    blk_stl.append(f"{p.get('blk')}blk")
                if p.get('stl'):
                    blk_stl.append(f"{p.get('stl')}stl")
                if blk_stl:
                    stats += f", {', '.join(blk_stl)}"
                
                performers_text += f"    - {p['name']} ({team_display}): {stats}\n"
        
        # === Meilleur performer de l'équipe PERDANTE ===
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
    """
    Fonction principale pour générer et envoyer la newsletter NBA quotidienne.
    
    Workflow complet:
        1. Calcule la date cible (veille = matchs de la nuit dernière)
        2. Récupère les scores NBA via nba_api
        3. Récupère les top performers de chaque match
        4. Récupère les actualités ESPN
        5. Récupère la vidéo YouTube Top 10 Plays
        6. Génère le texte de la newsletter via IA
        7. Rend le HTML de l'email
        8. Sauvegarde dans out/newsletter_YYYY-MM-DD.html
        9. Envoie l'email (sauf si dry_run=True)
    
    Args:
        dry_run (bool): Si True, génère la newsletter mais n'envoie pas l'email.
                       Utile pour tester sans spammer les destinataires.
    
    Returns:
        None
    
    Gestion des erreurs:
        - Timeout API nba_api: sort gracieusement sans envoyer d'email
        - Aucun match trouvé: sort sans envoyer d'email
        - Erreur d'envoi email: log l'erreur et lève l'exception
        - Autres erreurs: log avec traceback complet
    
    Comportement:
        - Exit code 0 même en cas d'erreur (pour GitHub Actions)
        - Logs détaillés à chaque étape
        - Tolérant aux erreurs (continue même si YouTube/news fail)
    """
    try:
        # === ÉTAPE 1: Calculer la date cible ===
        # Les matchs NBA se jouent le soir (18h-23h)
        # On récupère donc les matchs de la VEILLE pour la newsletter du matin
        target = (datetime.now() - timedelta(days=1)).date()
        logger.info(f"🚀 Starting NBA Daily Bot for {target}")
        
        # === ÉTAPE 2: Récupérer les scores avec gestion d'erreur ===
        logger.info("📊 Fetching games...")
        try:
            games = get_games_by_date(target)
        except Exception as e:
            # L'API stats.nba.com peut timeout ou être indisponible
            # On sort gracieusement pour éviter de crasher GitHub Actions
            logger.error(f"❌ Failed to fetch games due to API timeout/error: {e}")
            logger.warning("⚠️ Skipping newsletter - stats.nba.com is unavailable")
            return  # Exit code 0 (pas d'email envoyé, mais pas d'erreur non plus)
        
        # === ÉTAPE 3: Vérifier si des matchs ont été joués ===
        if not games:
            logger.warning("⚠️ No games found for this date - skipping newsletter")
            logger.info("✨ No newsletter to send today (no games played)")
            return  # Pas de matchs = pas de newsletter
        
        # === ÉTAPE 4: Récupérer les top performers de chaque match ===
        logger.info("🔥 Fetching top performers...")
        all_top_performers = []
        
        for game in games:
            try:
                # get_top_performers retourne les 5 meilleurs joueurs du match
                performers = get_top_performers(game.id, limit=5, target_date=game.date)
                all_top_performers.extend(performers)
            except Exception as e:
                # Si un match échoue, on continue avec les autres
                # (pas critique, on peut générer la newsletter sans les stats détaillées)
                logger.debug(f"⚠️ Error fetching performers for game {game.id}: {e}")
        
        # === ÉTAPE 5: Récupérer les actualités ESPN ===
        logger.info("📰 Fetching news...")
        news = fetch_news(limit=5)  # Top 5 headlines du jour
        
        # === ÉTAPE 6: Récupérer la vidéo Top 10 Plays ===
        logger.info("🎬 Fetching Top 10 Plays video...")
        top_10_video = get_top_10_plays_video(target_date=target)
        
        # === ÉTAPE 7: Organiser les données des matchs ===
        logger.info("📊 Organizing game data with top performers...")
        organized_games = organize_game_data(games, all_top_performers)
        
        # === ÉTAPE 8: Générer le texte de la newsletter via IA ===
        logger.info("🤖 Generating newsletter content...")
        prompt = build_prompt(games, news, all_top_performers)
        logger.debug(f"Prompt preview: {prompt[:300]}...")
        
        # Appel à l'IA HuggingFace (ou modèle local selon config)
        summary = generate(prompt, max_tokens=cfg.MAX_TOKENS)
        logger.info(f"📝 Generated summary length: {len(summary) if summary else 0} chars")
        
        # Vérification: le texte généré ne doit pas être vide
        if not summary or not summary.strip():
            logger.warning(f"⚠️ Summary is empty or whitespace: {repr(summary[:100] if summary else 'None')}")
        
        # === ÉTAPE 9: Rendre le HTML de l'email ===
        logger.info("🎨 Rendering newsletter HTML...")
        html = render_email(summary, news, all_top_performers, games, organized_games, top_10_video)
        
        # === ÉTAPE 10: Sauvegarder dans un fichier ===
        os.makedirs("out", exist_ok=True)  # Crée le dossier out/ si inexistant
        output_file = f"out/newsletter_{target}.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"✅ Newsletter saved to {output_file}")
        
        # === ÉTAPE 11: Envoyer l'email (sauf si dry_run) ===
        if not dry_run:
            try:
                logger.info("📧 Sending email...")
                send_mail(html, f"NBA Daily — {target}")
                logger.info(f"✅ Email sent to {cfg.NEWS_RECIPIENT}")
            except Exception as e:
                logger.error(f"❌ Failed to send email: {e}")
                raise  # On remonte l'erreur pour signaler le problème
        else:
            logger.info("⏭️ Dry run mode - skipping email send")
        
        logger.info("✨ Newsletter generation completed successfully!")
        
    except Exception as e:
        # Erreur critique (autre que timeout API)
        # On log avec traceback complet pour debug
        logger.error(f"❌ Fatal error in newsletter generation: {e}", exc_info=True)
        raise  # On remonte l'exception

if __name__ == "__main__":
    run(dry_run=True)
