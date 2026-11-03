import logging
import re
import requests
from datetime import date

logger = logging.getLogger(__name__)

TIMEOUT = 15
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"


def game_score(p):
    """
    Le Game Score de John Hollinger : la ligne de stats entière en un seul chiffre (un 42-8-13 passe devant
    un 43-8-3), tirs ratés et balles perdues compris.
    """
    return round(
        p['pts'] + 0.4 * p['fgm'] - 0.7 * p['fga'] - 0.4 * (p['fta'] - p['ftm'])
        + 0.7 * p['oreb'] + 0.3 * p['dreb'] + p['stl'] + 0.7 * p['ast'] + 0.7 * p['blk']
        - 0.4 * p['pf'] - p['tov'], 1)


def rank(p):
    """Clé de tri des joueurs : le Game Score."""
    return p.get('score', p.get('pts', 0))


def get_night(target_date=None):
    """
    Toute la nuit vue par ESPN : ({joueurs de tous les matchs}, {id du match : {récit, absents}}).
    Les joueurs sont tous ceux qui ont joué, triés par équipe selon leur Game Score.
    """
    target_date = target_date or date.today()
    try:
        logger.info(f"🏀 Fetching box scores and recaps from ESPN for {target_date}...")
        response = requests.get(SCOREBOARD_URL, params={"dates": target_date.strftime('%Y%m%d')}, timeout=TIMEOUT)
        response.raise_for_status()
        events = response.json().get("events", [])
    except requests.RequestException as e:
        logger.error(f"❌ ESPN API request failed: {e}")
        return [], {}
    if not events:
        logger.warning(f"⚠️ No games found on ESPN for {target_date}")

    performers, stories = [], {}
    for event in events:
        game_id = event.get("id")
        try:
            response = requests.get(SUMMARY_URL, params={"event": game_id}, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.warning(f"⚠️ ESPN summary unavailable for game {game_id}: {e}")
            continue
        performers.extend(_box_players(data, game_id))
        stories[game_id] = {"story": _story(data), "out": _absents(data)}
    logger.info(f"✅ ESPN: {len(performers)} players, {sum(1 for s in stories.values() if s['story'])} recaps")
    return performers, stories


def _story(data):
    """Le récit du match écrit pour ESPN, en texte brut."""
    article = data.get("article") or {}
    text = re.sub(r"<[^>]+>", " ", article.get("story") or "")
    return re.sub(r"\s+", " ", text).strip()


def _absents(data):
    """{ équipe : [joueurs absents] }"""
    out = {}
    for team in data.get("injuries") or []:
        abbr = (team.get("team") or {}).get("abbreviation", "")
        names = [(i.get("athlete") or {}).get("displayName") for i in team.get("injuries") or []
                 if str(i.get("status", "")).lower() == "out"]
        if abbr and any(names):
            out[abbr] = [n for n in names if n]
    return out


def _box_players(data, game_id):
    players = []
    for team_data in (data.get("boxscore") or {}).get("players", []):
        team_abbr = (team_data.get("team") or {}).get("abbreviation", "UNK")
        for block in team_data.get("statistics") or []:
            labels = block.get("labels") or block.get("names") or []
            team_players = [p for p in (_parse_player(a, team_abbr, labels) for a in block.get("athletes") or []) if p]
            for p in team_players:
                p['game_id'] = game_id
            players.extend(sorted(team_players, key=rank, reverse=True))
    return players


def _made_attempted(value):
    made, _, attempted = str(value or "0-0").partition("-")
    return int(made or 0), int(attempted or 0)


def _pct(made, attempted):
    return round(made / attempted * 100, 1) if attempted else 0.0


def _parse_player(athlete, team_abbr, labels):
    """Lit la ligne de stats par le nom des colonnes ; None pour un joueur qui n'a pas joué."""
    stats = dict(zip(labels, athlete.get("stats") or []))
    if not stats or not stats.get("MIN") or stats.get("MIN") == "0":
        return None
    try:
        number = lambda key: int(str(stats.get(key) or 0).replace("+", ""))
        fgm, fga = _made_attempted(stats.get("FG"))
        fg3m, fg3a = _made_attempted(stats.get("3PT"))
        ftm, fta = _made_attempted(stats.get("FT"))
        p = {
            'name': (athlete.get("athlete") or {}).get("displayName", "Unknown"),
            'team': team_abbr,
            'starter': bool(athlete.get("starter")),
            'min': number("MIN"),
            'pts': number("PTS"), 'reb': number("REB"), 'ast': number("AST"),
            'blk': number("BLK"), 'stl': number("STL"), 'tov': number("TO"),
            'oreb': number("OREB"), 'dreb': number("DREB"), 'pf': number("PF"),
            'plus_minus': number("+/-"),
            'fgm': fgm, 'fga': fga, 'fg_pct': _pct(fgm, fga),
            'fg3m': fg3m, 'fg3a': fg3a, 'fg3_pct': _pct(fg3m, fg3a),
            'ftm': ftm, 'fta': fta,
        }
    except (TypeError, ValueError) as e:
        logger.debug(f"⚠️ Error parsing boxscore player: {e}")
        return None
    p['score'] = game_score(p)
    return p
