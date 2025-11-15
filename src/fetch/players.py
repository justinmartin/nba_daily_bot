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
        from nba_api.stats.endpoints import ScoreboardV2, BoxScoreTraditionalV3
        
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
                
                # Get box score for this game (V3 is the new standard)
                # Use reduced timeout to fail faster and not block
                try:
                    box_score = BoxScoreTraditionalV3(game_id=game_id, timeout=10)
                    player_stats = box_score.get_data_frames()[0]
                except:
                    # If timeout, try once more with full timeout
                    try:
                        box_score = BoxScoreTraditionalV3(game_id=game_id, timeout=20)
                        player_stats = box_score.get_data_frames()[0]
                    except Exception as e:
                        logger.debug(f"⚠️ Skipping game {game_id} due to timeout: {type(e).__name__}")
                        continue
                
                if player_stats.empty:
                    continue
                
                # Parse each player's stats
                for p_idx, player_row in player_stats.iterrows():
                    # Skip if no player name (V3 uses firstName and familyName)
                    first_name = player_row.get('firstName', '')
                    family_name = player_row.get('familyName', '')
                    
                    if pd.isna(first_name) or pd.isna(family_name):
                        if not first_name and not family_name:
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
    Parse a player's stats from the box score row (V3 format).
    Returns a dict with player info and key stats.
    """
    try:
        # Extract basic info (V3 uses firstName/familyName instead of PLAYER_NAME)
        first_name = player_row.get('firstName', '')
        family_name = player_row.get('familyName', '')
        name = f"{first_name} {family_name}".strip() if first_name or family_name else 'Unknown'
        team = player_row.get('teamTricode', 'UNK')
        
        # Extract stats from V3 format (camelCase instead of UPPER_CASE)
        pts = int(player_row.get('points', 0)) if player_row.get('points') else 0
        reb = int(player_row.get('reboundsTotal', 0)) if player_row.get('reboundsTotal') else 0
        ast = int(player_row.get('assists', 0)) if player_row.get('assists') else 0
        blk = int(player_row.get('blocks', 0)) if player_row.get('blocks') else 0
        stl = int(player_row.get('steals', 0)) if player_row.get('steals') else 0
        
        # Calculate FG%
        fgm = int(player_row.get('fieldGoalsMade', 0)) if player_row.get('fieldGoalsMade') else 0
        fga = int(player_row.get('fieldGoalsAttempted', 1)) if player_row.get('fieldGoalsAttempted') else 1
        fg_pct = round((fgm / fga * 100), 1) if fga > 0 else 0
        
        # Calculate 3P%
        fg3m = int(player_row.get('threePointersMade', 0)) if player_row.get('threePointersMade') else 0
        fg3a = int(player_row.get('threePointersAttempted', 1)) if player_row.get('threePointersAttempted') else 1
        fg3_pct = round((fg3m / fg3a * 100), 1) if fg3a > 0 else 0
        
        performer = {
            'name': name,
            'team': team,
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
        logger.debug(f"⚠️ Error parsing player stats: {e}")
        return None
