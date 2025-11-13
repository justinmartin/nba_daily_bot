from dataclasses import dataclass
import requests
from datetime import date
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from src.config import Config

logger = logging.getLogger(__name__)
cfg = Config()

BASE = "https://api.balldontlie.io/v1"

@dataclass
class Game:
    id: int
    date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    home_wins: int = None
    home_losses: int = None
    away_wins: int = None
    away_losses: int = None

def _get_session_with_retries():
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_games_by_date(d: date):
    """Fetch NBA games for a given date with retry logic."""
    try:
        session = _get_session_with_retries()
        headers = {}
        if cfg.BALLDONTLIE_API_KEY:
            headers["Authorization"] = f"Bearer {cfg.BALLDONTLIE_API_KEY}"
        
        resp = session.get(
            f"{BASE}/games", 
            params={"dates[]": d.isoformat(), "per_page": 100},
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to fetch games for {d}: {e}")
        raise
    
    data = resp.json().get("data", [])
    games = []
    for g in data:
        try:
            games.append(Game(
                id=g["id"],
                date=g["date"],
                home_team=g["home_team"]["full_name"],
                away_team=g["visitor_team"]["full_name"],
                home_score=g["home_team_score"],
                away_score=g["visitor_team_score"],
                home_wins=g.get("home_team", {}).get("wins"),
                home_losses=g.get("home_team", {}).get("losses"),
                away_wins=g.get("visitor_team", {}).get("wins"),
                away_losses=g.get("visitor_team", {}).get("losses")
            ))
        except KeyError as e:
            logger.warning(f"⚠️ Missing expected field in game data: {e}")
            continue
    
    logger.info(f"✅ Fetched {len(games)} games for {d}")
    return games
