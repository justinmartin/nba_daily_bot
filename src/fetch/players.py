import logging
from datetime import date
import pandas as pd

logger = logging.getLogger(__name__)


def get_top_performers(game_id, limit=5, target_date=None):
    """
    Get top performers for a given date using stats.nba.com (single source).
    Ignores game_id parameter and fetches all performers for target_date.
    """
    if target_date is None:
        target_date = date.today()
    
    return _get_from_stats_nba(limit, target_date)


def _get_from_stats_nba(limit=5, target_date=None):
    """
    Fetch top performers from stats.nba.com for a given date.
    Uses nba-api with no authentication needed.
    """
    try:
        from nba_api.stats.endpoints import ScoreboardV2, BoxScoreTraditionalV2
        
        if target_date is None:
            target_date = date.today()
        
        date_str = target_date.strftime('%Y-%m-%d')
        logger.debug(f"Fetching performers from stats.nba.com for {date_str}...")
        
        # Get all games for the date
        sb = ScoreboardV2(game_date=date_str)
        games_df = sb.get_data_frames()[0]
        
        if games_df.empty:
            logger.warning(f"⚠️ No games found for {date_str}")
            return []
        
        all_performers = []
        
        # Iterate through each game and collect player stats
        for idx, game_row in games_df.iterrows():
            try:
                game_id = str(game_row['GAME_ID']).zfill(10)
                
                # Get box score for this game
                box_score = BoxScoreTraditionalV2(game_id=game_id)
                player_stats = box_score.get_data_frames()[0]
                
                if player_stats.empty:
                    continue
                
                # Parse each player's stats
                for p_idx, player_row in player_stats.iterrows():
                    # Skip bench team rows and total rows
                    player_name = player_row.get('PLAYER_NAME', '')
                    if pd.isna(player_name) or 'Team Totals' in str(player_name):
                        continue
                    
                    performer = _parse_player_stats(player_row, game_row)
                    if performer:
                        all_performers.append(performer)
                        
            except Exception as e:
                logger.debug(f"⚠️ Error processing game {game_id}: {e}")
                continue
        
        # Sort by points (descending) and return top N
        all_performers.sort(key=lambda x: float(x.get('pts', 0)), reverse=True)
        top_performers = all_performers[:limit]
        
        logger.info(f"✅ Found {len(top_performers)} top performers for {date_str}")
        return top_performers
        
    except ImportError as e:
        logger.error(f"❌ Import error (nba-api or pandas not installed): {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch performers from stats.nba.com: {e}")
        raise


def _parse_player_stats(player_row, game_row):
    """
    Parse a player's stats from the box score row.
    Returns a dict with player info and key stats.
    """
    try:
        # Extract basic info
        name = player_row.get('PLAYER_NAME', 'Unknown')
        team = player_row.get('TEAM_ABBREVIATION', 'UNK')
        
        # Extract stats (handle both numeric and string formats)
        pts = float(player_row.get('PTS', 0)) if player_row.get('PTS') else 0
        reb = float(player_row.get('REB', 0)) if player_row.get('REB') else 0
        ast = float(player_row.get('AST', 0)) if player_row.get('AST') else 0
        blk = float(player_row.get('BLK', 0)) if player_row.get('BLK') else 0
        stl = float(player_row.get('STL', 0)) if player_row.get('STL') else 0
        
        # Calculate FG%
        fgm = float(player_row.get('FGM', 0)) if player_row.get('FGM') else 0
        fga = float(player_row.get('FGA', 1)) if player_row.get('FGA') else 1
        fg_pct = round((fgm / fga * 100), 1) if fga > 0 else 0
        
        # Calculate 3P%
        fg3m = float(player_row.get('FG3M', 0)) if player_row.get('FG3M') else 0
        fg3a = float(player_row.get('FG3A', 1)) if player_row.get('FG3A') else 1
        fg3_pct = round((fg3m / fg3a * 100), 1) if fg3a > 0 else 0
        
        performer = {
            'name': name,
            'team': team,
            'pts': int(pts),
            'reb': int(reb),
            'ast': int(ast),
            'blk': int(blk),
            'stl': int(stl),
            'fg_pct': fg_pct,
            'fg3_pct': fg3_pct,
            'fgm': int(fgm),
            'fga': int(fga),
            'fg3m': int(fg3m),
            'fg3a': int(fg3a),
        }
        
        return performer
        
    except Exception as e:
        logger.debug(f"⚠️ Error parsing player stats: {e}")
        return None
