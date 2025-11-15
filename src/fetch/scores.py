from dataclasses import dataclass
import logging
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class Game:
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


# Team ID to name mapping
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
    """Fetch NBA games for a given date using stats.nba.com (no API key needed)."""
    try:
        from nba_api.stats.endpoints import ScoreboardV2, BoxScoreSummaryV3
        
        date_str = d.strftime('%Y-%m-%d')
        logger.debug(f"Fetching games for {date_str} from stats.nba.com...")
        
        # Get scoreboard for the date
        sb = ScoreboardV2(game_date=date_str)
        games_df = sb.get_data_frames()[0]
        
        if games_df.empty:
            logger.warning(f"⚠️ No games found for {date_str}")
            return []
        
        games = []
        for idx, row in games_df.iterrows():
            try:
                game_id = str(row['GAME_ID']).zfill(10)
                home_team_id = row['HOME_TEAM_ID']
                away_team_id = row['VISITOR_TEAM_ID']
                
                # Map team IDs to names
                home_team = TEAM_MAP.get(home_team_id, f"Team{home_team_id}")
                away_team = TEAM_MAP.get(away_team_id, f"Team{away_team_id}")
                
                # Get scores from box score summary (V3)
                home_score = 0
                away_score = 0
                
                try:
                    box_summary = BoxScoreSummaryV3(game_id=game_id)
                    # Dataframe 4 contains team stats with scores
                    team_stats = box_summary.get_data_frames()[4]
                    
                    if not team_stats.empty and 'score' in team_stats.columns:
                        # Find home and away scores
                        for idx_ts, row_ts in team_stats.iterrows():
                            if row_ts['teamId'] == home_team_id:
                                home_score = int(row_ts['score'])
                            elif row_ts['teamId'] == away_team_id:
                                away_score = int(row_ts['score'])
                except:
                    pass
                
                game = Game(
                    id=game_id,
                    date=date_str,
                    home_team=home_team,
                    away_team=away_team,
                    home_score=home_score,
                    away_score=away_score,
                    home_wins=None,
                    home_losses=None,
                    away_wins=None,
                    away_losses=None
                )
                
                games.append(game)
            except Exception as e:
                logger.warning(f"⚠️ Error parsing game: {e}")
                continue
        
        logger.info(f"✅ Fetched {len(games)} games for {date_str}")
        return games
        
    except ImportError:
        logger.error("❌ nba-api not installed")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch games for {d}: {e}")
        raise
