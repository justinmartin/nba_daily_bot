"""
Fetch upcoming NBA games schedule with French broadcast information.
Scrapes nba.com/games page for game times and broadcaster data.
"""

import logging
import json
import re
from datetime import date, datetime
from dataclasses import dataclass, field
from typing import List
from html.parser import HTMLParser

import requests

logger = logging.getLogger(__name__)


@dataclass
class UpcomingGame:
    game_id: str
    home_team: str
    away_team: str
    home_tricode: str
    away_tricode: str
    home_record: str
    away_record: str
    game_time_utc: str
    game_time_fr: str       # e.g. "01h30"
    game_status: int         # 1=scheduled, 2=in progress, 3=final
    broadcasters: List[str] = field(default_factory=list)  # e.g. ["beIN Sports", "League Pass"]


# --- Main entry point ---

def get_upcoming_games(target_date: date) -> List[UpcomingGame]:
    """
    Fetch upcoming games for the given NBA game date with French broadcast info.
    Uses nba.com __NEXT_DATA__ as the primary source.
    Falls back to ESPN API if nba.com scraping fails.
    """
    # Primary: nba.com __NEXT_DATA__ (has broadcast info)
    try:
        games = _fetch_from_nba_com(target_date)
        if games:
            logger.info(f"✅ Found {len(games)} upcoming games from nba.com")
            return games
    except Exception as e:
        logger.warning(f"⚠️ nba.com scraping failed: {e}")

    # Fallback: ESPN API (no French broadcast info)
    try:
        games = _fetch_from_espn(target_date)
        if games:
            logger.info(f"✅ Found {len(games)} upcoming games from ESPN (sans diffuseurs FR)")
            return games
    except Exception as e:
        logger.error(f"❌ ESPN fallback also failed: {e}")

    return []


# --- nba.com __NEXT_DATA__ approach ---

class _NextDataParser(HTMLParser):
    """Extract the __NEXT_DATA__ JSON from the HTML page."""
    def __init__(self):
        super().__init__()
        self._capture = False
        self.data = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and ('id', '__NEXT_DATA__') in attrs:
            self._capture = True

    def handle_data(self, data):
        if self._capture:
            self.data += data

    def handle_endtag(self, tag):
        if tag == 'script' and self._capture:
            self._capture = False


def _fetch_from_nba_com(target_date: date) -> List[UpcomingGame]:
    """Fetch games and broadcast info from nba.com __NEXT_DATA__."""
    date_str = target_date.strftime('%Y-%m-%d')
    url = f'https://www.nba.com/games?date={date_str}'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    logger.info(f"📡 Fetching nba.com schedule for {date_str}...")
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    parser = _NextDataParser()
    parser.feed(resp.text)

    if not parser.data:
        logger.warning("__NEXT_DATA__ not found in nba.com HTML")
        return []

    data = json.loads(parser.data)
    props = data.get('props', {}).get('pageProps', {})

    # Navigate to game cards
    gcf = props.get('gameCardFeed', {})
    modules = gcf.get('modules', [])

    games: List[UpcomingGame] = []
    for module in modules:
        for card in module.get('cards', []):
            cd = card.get('cardData', {})
            try:
                game = _parse_card_data(cd)
                if game:
                    games.append(game)
            except Exception as e:
                logger.warning(f"⚠️ Error parsing game card: {e}")
                continue

    return games


def _parse_card_data(cd: dict) -> UpcomingGame:
    """Parse a single game card from __NEXT_DATA__ into an UpcomingGame."""
    game_id = cd.get('gameId', '')
    game_status = cd.get('gameStatus', 1)

    home = cd.get('homeTeam', {})
    away = cd.get('awayTeam', {})

    home_name = home.get('teamName', '')
    away_name = away.get('teamName', '')
    home_tri = home.get('teamTricode', '')
    away_tri = away.get('teamTricode', '')
    home_record = home.get('teamSubtitle', '')
    away_record = away.get('teamSubtitle', '')

    time_utc = cd.get('gameTimeUtc', '') or ''
    game_time_fr = _utc_to_french(time_utc) if time_utc else 'TBD'

    # --- Determine French broadcasters ---
    broadcasters = _extract_french_broadcasters(cd.get('broadcasters', {}))

    return UpcomingGame(
        game_id=game_id,
        home_team=home_name,
        away_team=away_name,
        home_tricode=home_tri,
        away_tricode=away_tri,
        home_record=home_record,
        away_record=away_record,
        game_time_utc=time_utc,
        game_time_fr=game_time_fr,
        game_status=game_status,
        broadcasters=broadcasters,
    )


def _extract_french_broadcasters(bc: dict) -> List[str]:
    """
    Determine which French channels broadcast the game.

    Rules (based on observed nba.com behaviour):
    - intlTvBroadcasters / intlOttBroadcasters: Explicit international broadcasters
      (beIN Sports, Prime Video, etc.) — use directly when present.
    - nationalBroadcasters non-empty (ESPN, TNT, ABC, NBA TV, Peacock, NBCSN…):
      ⇒ beIN Sports France picks up these nationally-televised games.
    - subscriptionBroadcasters with "League Pass": Available on League Pass.
    - If nothing else → League Pass by default.
    """
    french: List[str] = []
    seen = set()

    def _add(name: str):
        key = name.lower().strip()
        if key not in seen:
            seen.add(key)
            french.append(name)

    # 1) Check explicit international TV and OTT broadcasters
    for field_name in ('intlTvBroadcasters', 'intlOttBroadcasters'):
        for b in bc.get(field_name, []):
            display = b.get('broadcasterDisplayName', '')
            if display:
                _add(display)

    # 2) National US broadcast → beIN Sports in France
    national = bc.get('nationalBroadcasters', [])
    national_ott = bc.get('nationalOttBroadcasters', [])
    if national or national_ott:
        _add('beIN Sports')

    # 3) Subscription broadcasters (League Pass)
    for b in bc.get('subscriptionBroadcasters', []):
        display = b.get('broadcasterDisplayName', '')
        if display:
            _add(display)

    # 4) Default: League Pass
    if not french:
        _add('League Pass')

    return french


# --- Time conversion ---

def _utc_to_french(utc_str: str) -> str:
    """Convert a UTC datetime string to French time as 'HHhMM'."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        try:
            from backports.zoneinfo import ZoneInfo
        except ImportError:
            # Last resort: manual offset (+1 CET, +2 CEST)
            return _utc_to_french_manual(utc_str)

    try:
        clean = utc_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(clean)
        fr_tz = ZoneInfo('Europe/Paris')
        fr_time = dt.astimezone(fr_tz)
        return fr_time.strftime('%Hh%M')
    except Exception as e:
        logger.warning(f"Time conversion failed for '{utc_str}': {e}")
        return 'TBD'


def _utc_to_french_manual(utc_str: str) -> str:
    """Manual UTC→CET conversion (no zoneinfo). Assumes CET (+1)."""
    try:
        clean = utc_str.replace('Z', '').replace('+00:00', '')
        dt = datetime.fromisoformat(clean)
        from datetime import timedelta
        # CET is UTC+1 (simplified, ignores DST)
        fr_time = dt + timedelta(hours=1)
        return fr_time.strftime('%Hh%M')
    except Exception:
        return 'TBD'


# --- ESPN fallback ---

def _fetch_from_espn(target_date: date) -> List[UpcomingGame]:
    """Fallback: fetch today's games from ESPN API (no French broadcast info)."""
    from src.fetch.scores import ESPN_TEAM_MAP

    date_str = target_date.strftime('%Y%m%d')
    url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}'

    logger.info(f"📡 Fetching ESPN schedule for {target_date}...")
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    games: List[UpcomingGame] = []
    for event in data.get('events', []):
        try:
            comp = event.get('competitions', [{}])[0]
            competitors = comp.get('competitors', [])
            if len(competitors) != 2:
                continue

            home_c = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
            away_c = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])

            home_full = home_c.get('team', {}).get('displayName', '')
            away_full = away_c.get('team', {}).get('displayName', '')
            home_name = ESPN_TEAM_MAP.get(home_full, home_full)
            away_name = ESPN_TEAM_MAP.get(away_full, away_full)
            home_abbr = home_c.get('team', {}).get('abbreviation', '')
            away_abbr = away_c.get('team', {}).get('abbreviation', '')

            home_rec = home_c.get('records', [{}])[0].get('summary', '') if home_c.get('records') else ''
            away_rec = away_c.get('records', [{}])[0].get('summary', '') if away_c.get('records') else ''

            game_date_utc = event.get('date', '')
            game_time_fr = _utc_to_french(game_date_utc) if game_date_utc else 'TBD'

            # ESPN broadcast data (US only)
            broadcasters = ['League Pass']
            for b in comp.get('broadcasts', []):
                for name in b.get('names', []):
                    if name.upper() in ('ESPN', 'TNT', 'ABC', 'NBA TV', 'NBCSN', 'PEACOCK'):
                        if 'beIN Sports' not in broadcasters:
                            broadcasters.insert(0, 'beIN Sports')

            game_status_type = comp.get('status', {}).get('type', {}).get('id', '1')

            games.append(UpcomingGame(
                game_id=event.get('id', ''),
                home_team=home_name,
                away_team=away_name,
                home_tricode=home_abbr,
                away_tricode=away_abbr,
                home_record=home_rec,
                away_record=away_rec,
                game_time_utc=game_date_utc,
                game_time_fr=game_time_fr,
                game_status=int(game_status_type),
                broadcasters=broadcasters,
            ))
        except Exception as e:
            logger.warning(f"⚠️ Error parsing ESPN event: {e}")
            continue

    return games
