"""
NBA Top Performers Fetcher.

Ce module récupère les meilleurs performeurs (joueurs) NBA pour une date donnée
ou pour un match spécifique, en utilisant l'API stats.nba.com via nba_api.
"""

import logging
from datetime import date
import pandas as pd

logger = logging.getLogger(__name__)


def get_top_performers(game_id, limit=5, target_date=None):
    """
    Récupère les meilleurs performeurs NBA (joueurs avec le plus de points).
    
    Deux modes de fonctionnement:
    - Si game_id fourni: Top performers pour CE match uniquement
    - Si game_id vide/None: Top performers globaux pour tous les matchs du jour
    
    Args:
        game_id (str): ID du match spécifique (ex: "0022500145")
                       Peut être None ou "" pour mode global
        limit (int): Nombre de performeurs à retourner (défaut: 5)
        target_date (date, optional): Date cible (défaut: aujourd'hui)
    
    Returns:
        list[dict]: Liste des performeurs avec stats (pts, reb, ast, etc.)
                    Triés par points décroissants
    
    Exemple de retour:
        [
          {'name': 'LeBron James', 'team': 'LAL', 'pts': 40, 'reb': 10, 'ast': 8, ...},
          {'name': 'Stephen Curry', 'team': 'GSW', 'pts': 35, 'reb': 5, 'ast': 12, ...},
          ...
        ]
    """
    if target_date is None:
        target_date = date.today()
    
    # Router vers la bonne fonction selon le mode
    if game_id and game_id != "":
        return _get_performers_for_game(game_id, limit)
    else:
        return _get_from_stats_nba(limit, target_date)


def _get_performers_for_game(game_id, limit=5):
    """
    Récupère les top performers pour UN match spécifique.
    
    Processus:
    1. Appelle BoxScoreTraditionalV3 pour avoir les stats de tous les joueurs
    2. Parse chaque joueur et extrait ses stats
    3. Tri par points décroissants
    4. Retourne les N meilleurs
    
    Args:
        game_id (str): ID du match (ex: "0022500145")
        limit (int): Nombre de joueurs à retourner
    
    Returns:
        list[dict]: Top performers du match
    
    Gestion des erreurs:
        - Timeout 30s puis retry avec 60s si échec
        - Si échec complet: retourne [] (pas de crash)
    """
    try:
        from nba_api.stats.endpoints import BoxScoreTraditionalV3
        
        logger.debug(f"Fetching performers for game {game_id}...")
        
        try:
            box_score = BoxScoreTraditionalV3(game_id=game_id, timeout=30)
            player_stats = box_score.get_data_frames()[0]
        except:
            # If timeout, try once more with longer timeout
            try:
                box_score = BoxScoreTraditionalV3(game_id=game_id, timeout=60)
                player_stats = box_score.get_data_frames()[0]
            except Exception as e:
                logger.debug(f"⚠️ Failed to fetch performers for game {game_id}: {e}")
                return []
        
        if player_stats.empty:
            return []
        
        all_performers = []
        
        # Parse each player's stats
        for p_idx, player_row in player_stats.iterrows():
            performer = _parse_player_stats(player_row, None)
            if performer and performer.get('pts', 0) > 0:  # Only include players who scored
                all_performers.append(performer)
        
        # Sort by points and return top N
        all_performers.sort(key=lambda x: float(x.get('pts', 0)), reverse=True)
        top_performers = all_performers[:limit]
        
        return top_performers
        
    except Exception as e:
        logger.debug(f"⚠️ Error fetching performers for game {game_id}: {e}")
        return []


def _get_from_stats_nba(limit=5, target_date=None):
    """
    Fetch top performers from stats.nba.com for a given date.
    Uses nba-api with no authentication needed.
    
    FALLBACK: Si stats.nba.com timeout/bloqué → bascule automatiquement sur ESPN API
    """
    try:
        from nba_api.stats.endpoints import ScoreboardV2, BoxScoreTraditionalV3
        
        if target_date is None:
            target_date = date.today()
        
        date_str = target_date.strftime('%Y-%m-%d')
        logger.debug(f"Fetching performers from stats.nba.com for {date_str}...")
        
        # Get all games for the date
        sb = ScoreboardV2(game_date=date_str, timeout=60)
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
                    box_score = BoxScoreTraditionalV3(game_id=game_id, timeout=30)
                    player_stats = box_score.get_data_frames()[0]
                except:
                    # If timeout, try once more with full timeout
                    try:
                        box_score = BoxScoreTraditionalV3(game_id=game_id, timeout=60)
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
        
    except (ImportError, Exception) as e:
        # Intercepter TOUTES les erreurs (import, timeout, etc.) et utiliser le fallback
        logger.warning(f"⚠️ NBA API failed for player stats: {type(e).__name__}: {e}")
        logger.info("🔄 Trying ESPN API as fallback for player stats...")
        
        # FALLBACK: Basculer sur ESPN API
        try:
            from .players_fallback import get_top_performers_from_espn
            performers = get_top_performers_from_espn(target_date=target_date, limit=limit)
            if performers:
                logger.info(f"✅ ESPN API fallback succeeded: {len(performers)} performers")
                return performers
            else:
                logger.error("❌ ESPN API fallback returned no performers")
                raise Exception("Both NBA API and ESPN API failed")
        except Exception as fallback_error:
            logger.error(f"❌ ESPN API fallback also failed: {fallback_error}")
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
