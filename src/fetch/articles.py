"""
Les articles qui nourrissent le récap : ce qui s'est passé autour des matchs et les joueurs qui ont pesé sans
que ça se voie sur la feuille de stats. Le récit ESPN de chaque match vient de src/fetch/players.py.
The Athletic est payant : on s'en tient au titre et au résumé de son flux public.
"""
import logging
import re
from calendar import timegm
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
# source, flux, nombre d'articles, longueur gardée, lire la page entière
SOURCES = (
    ("Trashtalk", "https://trashtalk.co/feed/", 14, 2200, True),
    ("Basket USA", "https://www.basketusa.com/feed/", 8, 1300, False),
    ("Yahoo Sports", "https://sports.yahoo.com/nba/rss/", 10, 1000, False),
    ("The Athletic", "https://www.nytimes.com/athletic/rss/nba/", 15, 400, False),
    ("Hoops Rumors", "https://www.hoopsrumors.com/feed", 10, 500, False),
    ("RealGM", "https://basketball.realgm.com/rss/wiretap/0/0.xml", 10, 500, False),
    ("CBS Sports", "https://www.cbssports.com/rss/headlines/nba/", 8, 250, False),
)
BETTING = re.compile(r"\b(odds|picks?|prediction|predictions|best bets?|props?|parlay|fantasy|preview)\b", re.I)


def _clean(html):
    text = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _full_page(url):
    """Le corps d'un article Trashtalk (le flux n'en donne que la première phrase)."""
    try:
        response = requests.get(url, headers=UA, timeout=15)
        response.raise_for_status()
        body = BeautifulSoup(response.content.decode("utf-8", "replace"), "html.parser").find("article")
        paragraphs = [p.get_text(" ", strip=True) for p in body.find_all("p")] if body else []
        return " ".join(p for p in paragraphs if p and not re.match(r"Le \d{2} \w+\.? \d{4} à", p))
    except Exception as e:
        logger.debug(f"⚠️ Article illisible {url}: {e}")
        return ""


def _entry_text(entry):
    content = (entry.get("content") or [{}])[0].get("value", "")
    summary = entry.get("summary") or entry.get("description") or ""
    return _clean(content if len(content) > len(summary) else summary)


def fetch_articles(hours=30, now=None):
    """Les articles NBA des dernières heures, source par source : [{source, title, link, published, text}]."""
    since = (now or datetime.now(timezone.utc)) - timedelta(hours=hours)
    articles = []
    for source, url, limit, length, full in SOURCES:
        try:
            response = requests.get(url, headers=UA, timeout=15)
            response.raise_for_status()
            entries = feedparser.parse(response.content).entries
        except Exception as e:
            logger.warning(f"⚠️ Flux {source} indisponible : {e}")
            continue
        kept = 0
        for entry in entries:
            if kept == limit:
                break
            parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            published = datetime.fromtimestamp(timegm(parsed), timezone.utc) if parsed else None
            title = _clean(entry.get("title", ""))
            if not title or not published or published < since or BETTING.search(title):
                continue
            text = (_full_page(entry.get("link")) if full else "") or _entry_text(entry)
            articles.append({"source": source, "title": title, "link": entry.get("link", ""),
                             "published": published, "text": text[:length]})
            kept += 1
        logger.info(f"📰 {source} : {kept} article(s)")
    return articles
