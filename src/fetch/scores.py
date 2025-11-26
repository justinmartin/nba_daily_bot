"""
NBA Scores Fetcher via nba_api.

Ce module récupère les scores et statistiques des matchs NBA pour une date donnée
en utilisant l'API officielle stats.nba.com via la bibliothèque nba_api.
"""

from dataclasses import dataclass
import logging
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class Game:
    """
    Représente un match NBA avec tous ses détails.
    
    Attributes:
        id (str): ID unique du match (ex: "0022500145")
        date (str): Date du match format "YYYY-MM-DD"
        home_team (str): Nom de l'équipe à domicile (ex: "Lakers")
        away_team (str): Nom de l'équipe visiteuse (ex: "Celtics")
        home_score (int): Score de l'équipe à domicile
        away_score (int): Score de l'équipe visiteuse
        home_wins (int, optional): Nombre de victoires de l'équipe à domicile
        home_losses (int, optional): Nombre de défaites de l'équipe à domicile
        away_wins (int, optional): Nombre de victoires de l'équipe visiteuse
        away_losses (int, optional): Nombre de défaites de l'équipe visiteuse
    """
    id: str
    date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    home_wins: int = None
    home_losses: int = None
    away_wins: int = None
    away_losses: int = None


# Mapping des IDs d'équipes NBA vers leurs noms
# Source: stats.nba.com official team IDs
TEAM_MAP = {
    1610612737: "Hawks", 1610612738: "Celtics", 1610612739: "Cavaliers", 1610612740: "Pelicans",
    1610612741: "Bulls", 1610612742: "Mavericks", 1610612743: "Grizzlies", 1610612744: "Warriors",
    1610612745: "Rockets", 1610612746: "Clippers", 1610612747: "Lakers", 1610612748: "Heat",
    1610612749: "Bucks", 1610612750: "Timberwolves", 1610612751: "Nets", 1610612752: "Knicks",
    1610612753: "Magic", 1610612754: "76ers", 1610612755: "76ers", 1610612756: "Suns",
    1610612757: "Trail Blazers", 1610612758: "Kings", 1610612759: "Spurs", 1610612760: "Thunder",
    1610612761: "Raptors", 1610612762: "Jazz", 1610612763: "Grizzlies", 1610612764: "Wizards",
    1610612765: "Hawks", 1610612766: "Hornets"
}


def get_games_by_date(d: date):
    """
    Récupère tous les matchs NBA pour une date donnée.
    
    Processus:
    1. Appelle ScoreboardV2 de l'API NBA pour avoir la liste des matchs
    2. Pour chaque match, récupère les détails via BoxScoreSummaryV3
    3. Extrait scores, records (W-L), et infos des équipes
    4. Utilise retry logic pour gérer les timeouts de l'API
    
    Args:
        d (date): Date des matchs à récupérer (format Python date)
    
    Returns:
        list[Game]: Liste d'objets Game avec tous les détails
                    Liste vide si aucun match ou erreur
    
    Gestion des erreurs:
        - Retry jusqu'à 5 fois avec 10s d'attente entre tentatives
        - Timeout de 60s par requête (l'API NBA peut être TRÈS lente)
        - Si API indisponible: retourne [] (pas de crash)
    
    Note:
        L'API stats.nba.com est GRATUITE mais parfois LENTE (60s+ par requête)
        En cas de timeout répété, l'API est probablement surchargée.
    """
    try:
        # Import dynamique (évite erreur si nba_api pas installé)
        from nba_api.stats.endpoints import ScoreboardV2, BoxScoreSummaryV3
        import time
        
        date_str = d.strftime('%Y-%m-%d')
        logger.debug(f"Fetching games for {date_str} from stats.nba.com...")
        
        # === ÉTAPE 1: Récupère le scoreboard (liste des matchs) avec retry ===
        max_retries = 5  # 5 tentatives (l'API NBA peut être instable)
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}/{max_retries} to fetch scoreboard...")
                
                # ScoreboardV2 = endpoint NBA API qui retourne tous les matchs du jour
                # timeout=60s car l'API peut être TRÈS lente (parfois 45s+)
                sb = ScoreboardV2(game_date=date_str, timeout=60)
                games_df = sb.get_data_frames()[0]  # DataFrame pandas avec les matchs
                break  # Succès, sort de la boucle retry
                
            except Exception as e:
                if attempt < max_retries - 1:
                    # Encore des tentatives restantes
                    wait_time = 10  # Attend 10s avant de réessayer (donne à l'API le temps de récupérer)
                    logger.warning(f"⚠️ Attempt {attempt + 1} failed: {type(e).__name__}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Toutes les tentatives échouées
                    logger.error(f"❌ All attempts failed to fetch scoreboard")
                    raise  # Re-lance l'exception
        
        # Vérification: y a-t-il des matchs ce jour-là ?
        if games_df.empty:
            logger.warning(f"⚠️ No games found for {date_str}")
            return []
        
        # === ÉTAPE 2: Pour chaque match, récupère les détails ===
        games = []
        for idx, row in games_df.iterrows():
            try:
                # IDs et noms des équipes
                game_id = str(row['GAME_ID']).zfill(10)  # Format: "0022500145"
                home_team_id = row['HOME_TEAM_ID']
                away_team_id = row['VISITOR_TEAM_ID']
                
                # Conversion ID → Nom d'équipe (ex: 1610612747 → "Lakers")
                home_team = TEAM_MAP.get(home_team_id, f"Team{home_team_id}")
                away_team = TEAM_MAP.get(away_team_id, f"Team{away_team_id}")
                
                # === ÉTAPE 3: Récupère les scores et records via BoxScoreSummaryV3 ===
                # Valeurs par défaut
                home_score = 0
                away_score = 0
                home_wins = None
                home_losses = None
                away_wins = None
                away_losses = None
                
                try:
                    # BoxScoreSummaryV3 = détails complets d'un match spécifique
                    box_summary = BoxScoreSummaryV3(game_id=game_id, timeout=30)
                    data_frames = box_summary.get_data_frames()
                    
                    # Le DataFrame #4 contient les stats d'équipe (scores + records)
                    if len(data_frames) > 4:
                        team_stats = data_frames[4]
                        
                        if not team_stats.empty:
                            # Parcourt les 2 lignes (home et away team)
                            for idx_ts, row_ts in team_stats.iterrows():
                                if row_ts['teamId'] == home_team_id:
                                    # Stats de l'équipe à domicile
                                    home_score = int(row_ts.get('score', 0)) if row_ts.get('score') else 0
                                    home_wins = int(row_ts.get('teamWins', 0)) if row_ts.get('teamWins') else None
                                    home_losses = int(row_ts.get('teamLosses', 0)) if row_ts.get('teamLosses') else None
                                    
                                elif row_ts['teamId'] == away_team_id:
                                    # Stats de l'équipe visiteuse
                                    away_score = int(row_ts.get('score', 0)) if row_ts.get('score') else 0
                                    away_wins = int(row_ts.get('teamWins', 0)) if row_ts.get('teamWins') else None
                                    away_losses = int(row_ts.get('teamLosses', 0)) if row_ts.get('teamLosses') else None
                                    
                except Exception as e:
                    # Échec récupération records - pas critique, on continue
                    logger.debug(f"Could not extract records for game {game_id}: {e}")
                
                # === ÉTAPE 4: Crée l'objet Game avec toutes les infos ===
                game = Game(
                    id=game_id,
                    date=date_str,
                    home_team=home_team,
                    away_team=away_team,
                    home_score=home_score,
                    away_score=away_score,
                    home_wins=home_wins,
                    home_losses=home_losses,
                    away_wins=away_wins,
                    away_losses=away_losses
                )
                
                games.append(game)
                
            except Exception as e:
                # Si un match pose problème, on log et on continue avec les autres
                logger.warning(f"⚠️ Error parsing game: {e}")
                continue
        
        logger.info(f"✅ Fetched {len(games)} games for {date_str}")
        return games
        
    except ImportError:
        # nba_api pas installé
        logger.error("❌ nba-api not installed")
        raise
        
    except Exception as e:
        # Erreur globale (réseau, API down, etc.)
        logger.error(f"❌ Failed to fetch games for {d}: {e}")
        raise
