# src/fetch/players.py
import requests
import logging
from src.config import Config
from datetime import datetime

logger = logging.getLogger(__name__)
cfg = Config()

def get_top_performers(game_id, limit=5, target_date=None):
    """
    Fetch top performers for a given BallDontLie game_id.
    target_date: optional date to search for (used when game_id doesn't work with nba-api)
    """
    
    try:
        # Try nba-api with game ID conversion
        performers = _get_from_nba_by_searching(game_id, limit, target_date)
        if performers:
            logger.debug(f"✅ Fetched {len(performers)} performers via NBA.com search")
            return performers
    except Exception as e:
        logger.debug(f"NBA.com search failed: {e}")
    
    # Fallback to BallDontLie if available
    try:
        performers = _get_from_balldontlie(game_id, limit)
        if performers:
            logger.debug(f"✅ Fetched {len(performers)} performers from BallDontLie")
            return performers
    except Exception as e:
        logger.debug(f"BallDontLie failed: {e}")
    
    logger.debug(f"⚠️ No player stats available for game {game_id}")
    return []


def _get_from_nba_by_searching(game_id, limit=5, target_date=None):
    """
    Try to find NBA.com game ID by searching for games on a given date.
    This is a workaround since BallDontLie game IDs don't map to NBA.com.
    """
    try:
        from nba_api.stats.endpoints import boxscoretraditionalv2, scoreboard
        from datetime import date
        
        # Use target_date if provided, otherwise use today
        search_date = target_date if target_date else date.today()
        
        logger.debug(f"Searching for NBA.com games on {search_date}...")
        
        try:
            # Try to get scoreboard
            sb = scoreboard.Scoreboard(game_date=search_date.strftime('%Y-%m-%d'))
            games = sb.get_data_frames()[0]
            
            if games.empty:
                logger.debug(f"No games found in scoreboard for {search_date}")
                return []
            
            logger.debug(f"Found {len(games)} games in scoreboard")
            
            # Try each game until we find one with player stats
            for idx, game in games.iterrows():
                game_id_nba = str(game['GAME_ID']).zfill(10)
                logger.debug(f"Trying NBA game ID: {game_id_nba}")
                
                try:
                    box_score = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id_nba)
                    player_stats_df = box_score.get_data_frames()[0]
                    
                    if not player_stats_df.empty:
                        performers = _parse_player_stats(player_stats_df, limit)
                        if performers:
                            logger.debug(f"Found {len(performers)} performers for game {game_id_nba}")
                            return performers
                except Exception as e:
                    logger.debug(f"Box score error for {game_id_nba}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Scoreboard error: {e}")
            return []
            
    except ImportError:
        logger.debug("nba-api not installed")
        return []
    except Exception as e:
        logger.debug(f"Error in NBA search: {e}")
        return []
    
    return []


def _parse_player_stats(player_stats_df, limit=5):
    """Parse and format player statistics from nba-api dataframe."""
    try:
        # Filter out team totals
        player_stats_df = player_stats_df[player_stats_df['PLAYER_NAME'] != 'Team Totals']
        
        if player_stats_df.empty:
            return []
        
        # Convert to list and sort by points
        players_list = player_stats_df.to_dict('records')
        players_list = sorted(
            players_list,
            key=lambda x: float(x.get('PTS', 0)) if x.get('PTS') else 0,
            reverse=True
        )[:limit]
        
        top_performers = []
        for row in players_list:
            try:
                pts = float(row.get('PTS', 0)) if row.get('PTS') else 0
                
                # Skip players with 0 points
                if pts == 0:
                    continue
                
                reb = float(row.get('REB', 0)) if row.get('REB') else 0
                ast = float(row.get('AST', 0)) if row.get('AST') else 0
                blk = float(row.get('BLK', 0)) if row.get('BLK') else 0
                stl = float(row.get('STL', 0)) if row.get('STL') else 0
                plus_minus = float(row.get('PLUS_MINUS', 0)) if row.get('PLUS_MINUS') else 0
                
                performer = {
                    "name": str(row.get('PLAYER_NAME', 'Unknown')).strip(),
                    "team": str(row.get('TEAM_ABBREVIATION', 'N/A')).strip(),
                    "pts": int(pts),
                    "reb": int(reb),
                    "ast": int(ast),
                    "fg_pct": str(row.get('FG%', '0%')).strip(),
                    "fg3_pct": str(row.get('FG3%', '0%')).strip(),
                    "+/-": int(plus_minus),
                }
                
                # Add defensive stats if significant
                if blk >= 1:
                    performer["blk"] = int(blk)
                if stl >= 1:
                    performer["stl"] = int(stl)
                
                top_performers.append(performer)
            except (ValueError, KeyError, TypeError) as e:
                logger.debug(f"Error parsing player: {e}")
                continue
        
        return top_performers
        
    except Exception as e:
        logger.debug(f"Error parsing stats: {e}")
        return []


def _get_from_balldontlie(game_id, limit=5):
    """Fetch from BallDontLie API as fallback."""
    try:
        url = f"https://api.balldontlie.io/v1/stats?game_ids[]={game_id}&per_page=100"
        headers = {}
        if cfg.BALLDONTLIE_API_KEY:
            headers["Authorization"] = f"Bearer {cfg.BALLDONTLIE_API_KEY}"
        
        r = requests.get(url, headers=headers, timeout=10)
        
        # Silently fail on auth errors
        if r.status_code == 401:
            return []
        
        r.raise_for_status()
        
        data = r.json().get("data", [])
        if not data:
            return []

        # Sort by points descending
        sorted_players = sorted(data, key=lambda x: x.get("pts", 0), reverse=True)[:limit]

        top_performers = []
        for p in sorted_players:
            try:
                fgm, fga = p.get("fgm", 0), p.get("fga", 0)
                fg_pct = f"{round((fgm / fga) * 100, 1)}%" if fga > 0 else "0%"
                fg3m, fg3a = p.get("fg3m", 0), p.get("fg3a", 0)
                fg3_pct = f"{round((fg3m / fg3a) * 100, 1)}%" if fg3a > 0 else "0%"

                performer = {
                    "name": f"{p['player']['first_name']} {p['player']['last_name']}",
                    "team": p["team"]["full_name"],
                    "pts": p.get("pts", 0),
                    "reb": p.get("reb", 0),
                    "ast": p.get("ast", 0),
                    "fg_pct": fg_pct,
                    "fg3_pct": fg3_pct,
                    "+/-": p.get("plus_minus", "N/A"),
                }

                # Add defensive stats if significant
                if p.get("blk", 0) >= 1:
                    performer["blk"] = p.get("blk", 0)
                if p.get("stl", 0) >= 1:
                    performer["stl"] = p.get("stl", 0)

                top_performers.append(performer)
            except KeyError as e:
                logger.debug(f"Missing field in BallDontLie: {e}")
                continue

        return top_performers
            
    except requests.exceptions.RequestException as e:
        logger.debug(f"BallDontLie error: {e}")
        return []
    except Exception as e:
        logger.debug(f"Error in BallDontLie: {e}")
        return []
