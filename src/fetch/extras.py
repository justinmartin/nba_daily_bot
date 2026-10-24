"""
Ce qui habille chaque match dans le mail :
- logos et couleurs des équipes (ESPN) ;
- l'article Trashtalk du match s'il est paru, sinon le résumé ESPN ;
- la vidéo « FULL GAME HIGHLIGHTS » de la chaîne YouTube de la NBA ;
- le « Résumé NBA de la nuit » de Trashtalk.
"""
import html
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests

logger = logging.getLogger(__name__)

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) nba_daily_bot (perso)"}
TRASHTALK_RSS = "https://trashtalk.co/feed/"
NBA_CHANNEL_ID = "UCWJ2lWNubArHWmf3FIHbfcQ"

# Surnoms utilisés par Trashtalk ou par la NBA sur YouTube, en plus du nom ESPN
ALIASES = {
    "76ers": ["76ers", "sixers"],
    "Trail Blazers": ["trail blazers", "blazers"],
    "Timberwolves": ["timberwolves", "wolves"],
    "Cavaliers": ["cavaliers", "cavs"],
    "Mavericks": ["mavericks", "mavs"],
    "Clippers": ["clippers", "clips"],
}


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


LOCATIONS = {}  # surnom → ville (« Bucks » → « Milwaukee »), rempli par get_teams()


def names_of(team):
    names = [norm(x) for x in ALIASES.get(team, [team])]
    if LOCATIONS.get(team):
        names.append(norm(LOCATIONS[team]))
    return names


def mentions(text, team):
    t = f" {norm(text)} "
    return any(f" {n} " in t for n in names_of(team))


# ---------------------------------------------------------------- équipes
def get_teams():
    """{ surnom ESPN (« Pistons ») et abréviation ESPN (« DET ») : {abbr, color, alt, logo} }"""
    out = {}
    try:
        r = requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams", timeout=15)
        r.raise_for_status()
        for item in r.json()["sports"][0]["leagues"][0]["teams"]:
            t = item["team"]
            abbr = t.get("abbreviation", "")
            info = {
                "abbr": abbr,
                "name": t.get("name", ""),
                "color": "#" + (t.get("color") or "333333"),
                "alt": "#" + (t.get("alternateColor") or "666666"),
                # Logo carré 96 px, servi par le CDN d'ESPN (bien affiché par Gmail et Apple Mail)
                # Logo prévu pour fond sombre (pas de pastille blanche, qu'Outlook inverse en noir)
                "logo": f"https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500-dark/{abbr.lower()}.png&h=96&w=96",
            }
            out[t.get("name", "")] = info
            out[abbr] = info
            # Ville (« Milwaukee »), sauf les sigles courts comme « LA » qui se confondent avec l'article « la »
            if len(t.get("location") or "") > 3:
                LOCATIONS[t.get("name", "")] = t["location"]
    except Exception as e:
        logger.warning(f"⚠️ Équipes ESPN indisponibles : {e}")
    return out


# ---------------------------------------------------------------- Trashtalk
def trashtalk_items(hours=20):
    """Articles Trashtalk des dernières heures : [{title, link, published}]"""
    try:
        r = requests.get(TRASHTALK_RSS, headers=UA, timeout=15)
        r.raise_for_status()
        xml = r.content.decode("utf-8", "replace")  # le serveur n'annonce pas l'encodage
    except Exception as e:
        logger.warning(f"⚠️ Flux Trashtalk indisponible : {e}")
        return []
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    items = []
    for it in xml.split("<item>")[1:]:
        title = re.search(r"<title>\s*(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?\s*</title>", it)
        link = re.search(r"<link>\s*([^<\s]+)", it)
        pub = re.search(r"<pubDate>([^<]+)</pubDate>", it)
        if not (title and link):
            continue
        try:
            published = parsedate_to_datetime(pub.group(1)) if pub else None
        except Exception:
            published = None
        if published and published < since:
            continue
        items.append({"title": html.unescape(title.group(1).strip()), "link": link.group(1), "published": published})
    return items


GENERIC = re.compile(r"^(resume nba de la nuit|programme nba|la nuit des francais)")


def night_items(items, game_date):
    """Articles publiés depuis le début de la soirée NBA (22 h UTC le jour des matchs, avant le premier match)."""
    start = datetime(game_date.year, game_date.month, game_date.day, 22, tzinfo=timezone.utc)
    return [it for it in items if it["published"] and it["published"] >= start]


def trashtalk_for_game(items, winner, loser, w_score, l_score):
    """
    L'article Trashtalk de ce match : d'abord un titre qui cite les deux équipes ou le score, sinon le premier
    article de la nuit qui cite l'une des deux (« Jayson Tatum termine les Knicks »).
    """
    scores = {f"{w_score}-{l_score}", f"{l_score}-{w_score}", f"{w_score} - {l_score}", f"{l_score} - {w_score}"}
    single = []
    for it in items:
        if GENERIC.search(norm(it["title"])):
            continue
        w, l = mentions(it["title"], winner), mentions(it["title"], loser)
        if (w and l) or any(sc in it["title"] for sc in scores):
            return it["link"]
        if w or l:
            single.append(it)
    single.sort(key=lambda it: it["published"] or datetime.max.replace(tzinfo=timezone.utc))
    return single[0]["link"] if single else None


def trashtalk_nightly(items):
    for it in items:
        if norm(it["title"]).startswith("resume nba de la nuit"):
            return {"title": it["title"], "link": it["link"]}
    return None


def espn_recap(game_id):
    return f"https://www.espn.com/nba/recap/_/gameId/{game_id}" if game_id else None


# ---------------------------------------------------------------- vidéos YouTube de la NBA
def _parse_page_videos(text):
    """Vidéos longues de la page « Vidéos » de la chaîne (le flux RSS est noyé sous les Shorts)."""
    seen = {}
    for m in re.finditer(r'"videoId":"([\w-]{11})"', text):
        vid = m.group(1)
        if vid in seen:
            continue
        chunk = text[m.end():m.end() + 2500]
        t = re.search(r'"title":\{"runs":\[\{"text":"(.*?)"\}', chunk) or re.search(r'"title":\{"content":"(.*?)"', chunk)
        if t:
            seen[vid] = t.group(1).encode().decode("unicode_escape", "ignore").encode("latin-1", "ignore").decode("utf-8", "ignore") if "\\u" in t.group(1) else t.group(1)
    return [{"id": k, "title": v} for k, v in seen.items()]


def nba_videos():
    """Vidéos récentes de la chaîne NBA : page « Vidéos » puis flux RSS, sans doublon."""
    out = []
    try:
        r = requests.get("https://www.youtube.com/@NBA/videos", headers={**UA, "Accept-Language": "en-US"}, timeout=15)
        if r.ok:
            out = _parse_page_videos(r.text)
    except Exception as e:
        logger.warning(f"⚠️ Page vidéos NBA indisponible : {e}")
    try:
        r = requests.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={NBA_CHANNEL_ID}", timeout=15)
        for e in r.text.split("<entry>")[1:]:
            vid = re.search(r"<yt:videoId>([^<]+)", e)
            title = re.search(r"<title>([^<]+)", e)
            if vid and title and vid.group(1) not in {v["id"] for v in out}:
                out.append({"id": vid.group(1), "title": html.unescape(title.group(1))})
    except Exception as e:
        logger.warning(f"⚠️ Flux YouTube NBA indisponible : {e}")
    return out


def _video(v, kind):
    return {**v, "kind": kind, "url": f"https://www.youtube.com/watch?v={v['id']}", "thumb": f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg"}


def highlight_videos(games_list, game_date):
    """
    Pour chaque match, la meilleure vidéo officielle disponible :
    « full » = résumé complet (FULL GAME HIGHLIGHTS), « clip » = fin de match ou perf d'un joueur.
    Renvoie ({ id du match : vidéo }, récap vidéo de la nuit ou None).
    """
    videos = nba_videos()
    day = f"{game_date:%B} {game_date.day}, {game_date:%Y}"  # « October 23, 2026 », comme dans les titres NBA
    other_day = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}")
    recent = [v for v in videos if day in v["title"] or not other_day.search(v["title"])]
    out, used = {}, set()
    for g in games_list:
        home, away = g.home_team, g.away_team
        both = [v for v in recent if mentions(v["title"], home) and mentions(v["title"], away)]
        full = next((v for v in both if "FULL GAME HIGHLIGHTS" in v["title"].upper()), None)
        if full:
            out[g.id] = _video(full, "full")
        elif both:
            out[g.id] = _video(both[0], "clip")
        else:
            # Une perf de joueur « … vs Knicks » : l'adversaire est cité, l'équipe du joueur rarement
            one = next((v for v in recent if v["id"] not in used and "nightly recap" not in v["title"].lower() and "top 10" not in v["title"].lower()
                        and re.search(r"\bvs\.?\s", v["title"]) and (mentions(v["title"], home) or mentions(v["title"], away))), None)
            if one:
                out[g.id] = _video(one, "clip")
        if g.id in out:
            used.add(out[g.id]["id"])
    nightly = next((v for v in videos if "nightly recap" in v["title"].lower() and day in v["title"]), None)
    logger.info(f"🎬 Vidéos : {sum(1 for v in out.values() if v['kind'] == 'full')} résumés complets, {sum(1 for v in out.values() if v['kind'] == 'clip')} extraits, sur {len(games_list)} matchs")
    return out, (_video(nightly, "nightly") if nightly else None)
