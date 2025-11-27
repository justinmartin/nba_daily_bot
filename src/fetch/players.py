"""
NBA Top Performers Fetcher via ESPN API.

Ce module récupère les meilleurs performeurs (joueurs) NBA en utilisant l'API ESPN.
ESPN API est gratuite, rapide et fonctionne sur GitHub Actions (contrairement à stats.nba.com).
"""

import logging
import requests
from datetime import date

logger = logging.getLogger(__name__)

# Timeout rapide car ESPN API est beaucoup plus rapide que stats.nba.com
TIMEOUT = 15


def get_top_performers(game_id, limit=5, target_date=None):
    """
    Récupère les meilleurs performeurs NBA via ESPN API avec boxscore complet.
    
    Utilise l'endpoint /summary qui donne TOUS les joueurs de chaque match,
    permettant d'avoir les 3 meilleurs scoreurs de chaque équipe.
    
    Args:
        game_id (str): Ignoré (gardé pour compatibilité avec l'ancien code)
        limit (int): Nombre de performeurs à retourner (défaut: 5)
        target_date (date, optional): Date des matchs (défaut: aujourd'hui)
    
    Returns:
        list[dict]: Top performers avec stats (pts, reb, ast, etc.)
                    Format identique à l'ancien code pour compatibilité
    
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
        
        # Parcourir tous les matchs et récupérer le boxscore complet
        for game in games:
            try:
                game_id = game.get("id")
                performers = _get_boxscore_performers(game_id)
                all_performers.extend(performers)
            except Exception as e:
                logger.debug(f"⚠️ Error processing game {game.get('id')}: {e}")
                continue
        
        # Note: on ne fait PAS de tri global ni de limit ici
        # Chaque match a déjà ses top 3 par équipe
        # organize_game_data() dans main.py s'occupera de filtrer par équipe
        
        logger.info(f"✅ ESPN API: Found {len(all_performers)} total performers")
        return all_performers
        
    except requests.exceptions.Timeout:
        logger.error(f"❌ ESPN API timeout after {TIMEOUT}s")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ ESPN API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ ESPN API error: {e}")
        return []


def _get_boxscore_performers(game_id):
    """
    Récupère les top 3 scoreurs de chaque équipe via l'endpoint /summary.
    
    Cet endpoint donne le boxscore complet, mais on ne prend que les 3 meilleurs
    de chaque équipe (triés par points).
    
    Args:
        game_id (str): ID du match ESPN
    
    Returns:
        list[dict]: Top 3 scoreurs de chaque équipe (max 6 joueurs par match)
    """
    try:
        # Endpoint ESPN summary avec boxscore complet
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        boxscore = data.get("boxscore", {})
        players_data = boxscore.get("players", [])
        
        if not players_data:
            return []
        
        all_performers = []
        
        # Parcourir les 2 équipes
        for team_data in players_data:
            team_abbr = team_data.get("team", {}).get("abbreviation", "UNK")
            
            # Les stats sont dans statistics[0]
            statistics = team_data.get("statistics", [])
            if not statistics:
                continue
            
            athletes = statistics[0].get("athletes", [])
            
            # Parser tous les joueurs de l'équipe
            team_performers = []
            for athlete in athletes:
                performer = _parse_boxscore_player(athlete, team_abbr)
                if performer and performer.get('pts', 0) > 0:  # Seulement les joueurs ayant marqué
                    team_performers.append(performer)
            
            # Trier par points et prendre les 3 meilleurs
            team_performers.sort(key=lambda x: x.get('pts', 0), reverse=True)
            top_3 = team_performers[:3]
            all_performers.extend(top_3)
        
        return all_performers
        
    except Exception as e:
        logger.debug(f"⚠️ Error fetching boxscore for game {game_id}: {e}")
        return []


def _parse_boxscore_player(athlete, team_abbr):
    """
    Parse les stats d'un joueur depuis le boxscore ESPN.
    
    Format des stats ESPN boxscore:
    Labels: ['MIN', 'PTS', 'FG', '3PT', 'FT', 'REB', 'AST', 'TO', 'STL', 'BLK', 'OREB', 'DREB', 'PF', '+/-']
    Index:     0     1     2     3     4     5      6      7     8      9      10     11     12    13
    
    Args:
        athlete (dict): Données du joueur depuis ESPN boxscore
        team_abbr (str): Abréviation de l'équipe
    
    Returns:
        dict: Stats du joueur au format standard
              {'name': ..., 'team': ..., 'pts': ..., 'reb': ..., ...}
    """
    try:
        name = athlete.get("athlete", {}).get("displayName", "Unknown")
        stats = athlete.get("stats", [])
        
        # Vérifier qu'on a assez de stats
        if len(stats) < 10:
            return None
        
        # Extraire les stats (format ESPN)
        pts = int(stats[1]) if stats[1] else 0  # PTS à l'index 1
        reb = int(stats[5]) if stats[5] else 0  # REB à l'index 5
        ast = int(stats[6]) if stats[6] else 0  # AST à l'index 6
        stl = int(stats[8]) if stats[8] else 0  # STL à l'index 8
        blk = int(stats[9]) if stats[9] else 0  # BLK à l'index 9
        
        # Parser FG (format "X-Y" pour made-attempted)
        fg_str = stats[2] if stats[2] else "0-0"
        fg_parts = fg_str.split('-')
        fgm = int(fg_parts[0]) if len(fg_parts) > 0 else 0
        fga = int(fg_parts[1]) if len(fg_parts) > 1 else 0
        fg_pct = round((fgm / fga * 100), 1) if fga > 0 else 0.0
        
        # Parser 3PT (format "X-Y")
        fg3_str = stats[3] if stats[3] else "0-0"
        fg3_parts = fg3_str.split('-')
        fg3m = int(fg3_parts[0]) if len(fg3_parts) > 0 else 0
        fg3a = int(fg3_parts[1]) if len(fg3_parts) > 1 else 0
        fg3_pct = round((fg3m / fg3a * 100), 1) if fg3a > 0 else 0.0
        
        performer = {
            'name': name,
            'team': team_abbr,
            'pts': pts,
            'reb': reb,
            'ast': ast,
            'blk': blk,
            'stl': stl,
            'fg_pct': fg_pct,
            'fg3_pct': fg3_pct,
            'fgm': fgm,
            'fga': fga,
            'fg3m': fg3m,
            'fg3a': fg3a,
        }
        
        return performer
        
    except Exception as e:
        logger.debug(f"⚠️ Error parsing boxscore player: {e}")
        return None
