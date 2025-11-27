
import logging
import requests
from datetime import date

logger = logging.getLogger(__name__)

TIMEOUT = 15

def get_top_performers(game_id, limit=5, target_date=None):
    if target_date is None:
        target_date = date.today()
    
    date_str = target_date.strftime('%Y%m%d')
    
    try:
        logger.info(f"🏀 Fetching player stats from ESPN API for {target_date}...")
        
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
        
        for game in games:
            try:
                game_id = game.get("id")
                performers = _get_boxscore_performers(game_id)
                all_performers.extend(performers)
            except Exception as e:
                logger.debug(f"⚠️ Error processing game {game.get('id')}: {e}")
                continue
        
        
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
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        boxscore = data.get("boxscore", {})
        players_data = boxscore.get("players", [])
        
        if not players_data:
            return []
        
        all_performers = []
        
        for team_data in players_data:
            team_abbr = team_data.get("team", {}).get("abbreviation", "UNK")
            
            statistics = team_data.get("statistics", [])
            if not statistics:
                continue
            
            athletes = statistics[0].get("athletes", [])
            
            team_performers = []
            for athlete in athletes:
                performer = _parse_boxscore_player(athlete, team_abbr)
                if performer and performer.get('pts', 0) > 0:  # Seulement les joueurs ayant marqué
                    team_performers.append(performer)
            
            team_performers.sort(key=lambda x: x.get('pts', 0), reverse=True)
            top_3 = team_performers[:3]
            all_performers.extend(top_3)
        
        return all_performers
        
    except Exception as e:
        logger.debug(f"⚠️ Error fetching boxscore for game {game_id}: {e}")
        return []

def _parse_boxscore_player(athlete, team_abbr):
    try:
        name = athlete.get("athlete", {}).get("displayName", "Unknown")
        stats = athlete.get("stats", [])
        
        if len(stats) < 10:
            return None
        
        pts = int(stats[1]) if stats[1] else 0  # PTS à l'index 1
        reb = int(stats[5]) if stats[5] else 0  # REB à l'index 5
        ast = int(stats[6]) if stats[6] else 0  # AST à l'index 6
        stl = int(stats[8]) if stats[8] else 0  # STL à l'index 8
        blk = int(stats[9]) if stats[9] else 0  # BLK à l'index 9
        
        fg_str = stats[2] if stats[2] else "0-0"
        fg_parts = fg_str.split('-')
        fgm = int(fg_parts[0]) if len(fg_parts) > 0 else 0
        fga = int(fg_parts[1]) if len(fg_parts) > 1 else 0
        fg_pct = round((fgm / fga * 100), 1) if fga > 0 else 0.0
        
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
