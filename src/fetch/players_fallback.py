"""
ESPN API Fallback for NBA Player Stats.

Ce module est un fallback pour players.py quand stats.nba.com est bloqué/timeout.
Utilise l'API publique ESPN qui est plus rapide et fiable sur GitHub Actions.
"""

import logging
import requests
from datetime import date

logger = logging.getLogger(__name__)

# Timeout rapide car ESPN API est beaucoup plus rapide que stats.nba.com
TIMEOUT = 15


def get_top_performers_from_espn(target_date=None, limit=5):
    """
    Récupère les top performers NBA via ESPN API.
    
    Avantages ESPN API:
    - Rapide (15s timeout vs 60s NBA API)
    - Pas bloqué par les IPs cloud (GitHub Actions)
    - Pas besoin de clé API
    - Données officielles ESPN
    
    Args:
        target_date (date, optional): Date des matchs (défaut: aujourd'hui)
        limit (int): Nombre de performeurs à retourner (défaut: 5)
    
    Returns:
        list[dict]: Top performers avec stats (pts, reb, ast, etc.)
                    Format identique à players.py pour compatibilité
    
    Exemple:
        [
          {'name': 'LeBron James', 'team': 'LAL', 'pts': 40, 'reb': 10, ...},
          {'name': 'Stephen Curry', 'team': 'GSW', 'pts': 35, 'reb': 5, ...}
        ]
    """
    if target_date is None:
        target_date = date.today()
    
    date_str = target_date.strftime('%Y%m%d')
    
    try:
        logger.info(f"🏀 Fetching player stats from ESPN API for {target_date}...")
        
        # ESPN Scoreboard API endpoint
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
        params = {"dates": date_str}
        
        response = requests.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        games = data.get("events", [])
        
        if not games:
            logger.warning(f"⚠️ No games found on ESPN for {target_date}")
            return []
        
        all_performers = []
        
        # Parcourir tous les matchs et extraire les stats des joueurs
        for game in games:
            try:
                performers = _extract_performers_from_game(game)
                all_performers.extend(performers)
            except Exception as e:
                logger.debug(f"⚠️ Error processing game: {e}")
                continue
        
        # Trier par points décroissants et prendre les top N
        all_performers.sort(key=lambda x: x.get('pts', 0), reverse=True)
        top_performers = all_performers[:limit]
        
        logger.info(f"✅ ESPN API: Found {len(top_performers)} top performers")
        return top_performers
        
    except requests.exceptions.Timeout:
        logger.error(f"❌ ESPN API timeout after {TIMEOUT}s")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ ESPN API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ ESPN API error: {e}")
        return []


def _extract_performers_from_game(game):
    """
    Extrait les stats des joueurs d'un match ESPN.
    
    ESPN fournit les "leaders" (meilleurs joueurs) de chaque équipe pour le match.
    On récupère les joueurs des deux équipes et leurs stats.
    
    Args:
        game (dict): Données JSON du match depuis ESPN API
    
    Returns:
        list[dict]: Liste des performeurs du match
    """
    performers = []
    
    try:
        competitions = game.get("competitions", [])
        if not competitions:
            return []
        
        competition = competitions[0]
        competitors = competition.get("competitors", [])
        
        # Pour chaque équipe (home/away)
        for competitor in competitors:
            team_abbr = competitor.get("team", {}).get("abbreviation", "UNK")
            
            # ESPN fournit les "leaders" (meilleurs stats du match)
            leaders = competitor.get("leaders", [])
            
            # Extraire les stats des leaders de cette équipe
            team_performers = _parse_team_leaders(leaders, team_abbr)
            performers.extend(team_performers)
        
        return performers
        
    except Exception as e:
        logger.debug(f"⚠️ Error extracting performers from game: {e}")
        return []


def _parse_team_leaders(leaders, team_abbr):
    """
    Parse les "leaders" (meilleurs joueurs) d'une équipe depuis ESPN.
    
    ESPN fournit les leaders pour différentes catégories:
    - points: Meilleur marqueur
    - rebounds: Meilleur rebondeur
    - assists: Meilleur passeur
    
    On extrait le leader en points car c'est le plus pertinent pour top performers.
    
    Args:
        leaders (list): Liste des leaders depuis ESPN API
        team_abbr (str): Abréviation de l'équipe (ex: "LAL")
    
    Returns:
        list[dict]: Liste des performeurs de cette équipe
    """
    performers = []
    
    try:
        # Trouver le leader en points
        points_leader = None
        for leader_cat in leaders:
            if leader_cat.get("name") == "points":
                points_leader = leader_cat
                break
        
        if not points_leader:
            return []
        
        # ESPN peut avoir plusieurs joueurs ex-aequo
        athletes = points_leader.get("leaders", [])
        
        for athlete in athletes:
            try:
                performer = _parse_athlete_stats(athlete, team_abbr, leaders)
                if performer:
                    performers.append(performer)
            except Exception as e:
                logger.debug(f"⚠️ Error parsing athlete: {e}")
                continue
        
        return performers
        
    except Exception as e:
        logger.debug(f"⚠️ Error parsing team leaders: {e}")
        return []


def _parse_athlete_stats(athlete, team_abbr, all_leaders):
    """
    Parse les stats d'un joueur depuis ESPN.
    
    ESPN fournit les stats dans les "leaders" par catégorie.
    On reconstruit un dict avec toutes les stats du joueur.
    
    Args:
        athlete (dict): Données du joueur depuis ESPN
        team_abbr (str): Abréviation de l'équipe
        all_leaders (list): Tous les leaders (pour extraire rebounds, assists, etc.)
    
    Returns:
        dict: Stats du joueur au format standard
              {'name': ..., 'team': ..., 'pts': ..., 'reb': ..., ...}
    """
    try:
        # Nom du joueur
        name = athlete.get("athlete", {}).get("displayName", "Unknown")
        
        # Points (depuis le leader points)
        pts = int(float(athlete.get("value", 0)))
        
        # Rebounds et assists (chercher dans les autres leaders)
        reb = _find_stat_for_player(name, "rebounds", all_leaders)
        ast = _find_stat_for_player(name, "assists", all_leaders)
        
        # ESPN ne fournit pas toutes les stats détaillées dans les leaders
        # On met des valeurs par défaut pour les stats manquantes
        performer = {
            'name': name,
            'team': team_abbr,
            'pts': pts,
            'reb': reb,
            'ast': ast,
            'blk': 0,  # ESPN leaders ne fournit pas blocks/steals
            'stl': 0,
            'fg_pct': 0.0,  # ESPN leaders ne fournit pas les %
            'fg3_pct': 0.0,
            'fgm': 0,
            'fga': 0,
            'fg3m': 0,
            'fg3a': 0,
        }
        
        return performer
        
    except Exception as e:
        logger.debug(f"⚠️ Error parsing athlete stats: {e}")
        return None


def _find_stat_for_player(player_name, stat_name, all_leaders):
    """
    Trouve une stat spécifique pour un joueur dans les leaders.
    
    Args:
        player_name (str): Nom du joueur
        stat_name (str): Nom de la stat (ex: "rebounds", "assists")
        all_leaders (list): Tous les leaders du match
    
    Returns:
        int: Valeur de la stat (0 si non trouvée)
    """
    try:
        for leader_cat in all_leaders:
            if leader_cat.get("name") == stat_name:
                athletes = leader_cat.get("leaders", [])
                for athlete in athletes:
                    name = athlete.get("athlete", {}).get("displayName", "")
                    if name == player_name:
                        return int(float(athlete.get("value", 0)))
        return 0
    except:
        return 0
