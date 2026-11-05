
import feedparser
from datetime import datetime, timedelta, timezone
from itertools import zip_longest
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

try:
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

TRASHTALK_RSS = "https://www.trashtalk.co/feed/"
ATHLETIC_RSS = "https://www.nytimes.com/athletic/rss/nba/"  # flux NBA (le flux « news » mélange tous les sports)
ESPN_NEWS = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news"
DEFAULT_NEWS_SOURCES = (
    {"name": "Trashtalk", "url": TRASHTALK_RSS, "limit": 5},
    {"name": "The Athletic", "url": ATHLETIC_RSS, "limit": 5},
)
LINKS_IN_MAIL = 6


def _load_feed(source_url):
    response = requests.get(
        source_url,
        timeout=15,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        verify=False,
    )
    response.raise_for_status()
    return feedparser.parse(response.content)


def fetch_news(source_limits=None, include_content=False, window=None):
    """window : (début, fin) en UTC, pour ne garder que les articles parus pendant la nuit."""
    try:
        sources = source_limits or DEFAULT_NEWS_SOURCES
        headlines = []

        for source in sources:
            source_name = source.get("name", "News")
            source_url = source.get("url")
            source_limit = source.get("limit", 0)

            if not source_url or source_limit <= 0:
                continue

            feed = _load_feed(source_url)

            if feed.bozo:
                logger.warning(f"⚠️ Feed parsing issue for {source_name}: {feed.bozo_exception}")

            source_articles = []
            for entry in feed.entries:
                if len(source_articles) == source_limit:
                    break
                try:
                    published = entry.get("published_parsed")
                    if window and not (published and window[0] <= datetime(*published[:6], tzinfo=timezone.utc) <= window[1]):
                        continue
                    date_str = datetime(*published[:6]).strftime("%d %b %Y %H:%M") if published else "N/A"
                    summary = entry.get("summary") or entry.get("description") or ""

                    article = {
                        "source": source_name,
                        "title": entry.get("title", "No title"),
                        "link": entry.get("link", "#"),
                        "published": date_str,
                        "summary": summary.strip(),
                    }

                    if include_content:
                        content = _scrape_article_content(entry.get("link"))
                        if content:
                            article["content"] = content
                            article["summary"] = content[:800] + "..." if len(content) > 800 else content

                    source_articles.append(article)

                except Exception as e:
                    logger.warning(f"⚠️ Error parsing {source_name} entry: {e}")
                    continue

            headlines.extend(source_articles)
            logger.info(f"✅ Fetched {len(source_articles)} articles from {source_name}")

        # Un article de chaque source à tour de rôle : le mail n'en montre que 6
        by_source = [[a for a in headlines if a["source"] == source["name"]] for source in sources]
        return [a for round_ in zip_longest(*by_source) for a in round_ if a]

    except Exception as e:
        logger.error(f"❌ Failed to fetch news: {e}")
        return []  # Retourne liste vide au lieu de crash


def _fetch_espn(window):
    """Articles d'ESPN parus dans la fenêtre : (papiers, résumés de matchs)."""
    try:
        response = requests.get(ESPN_NEWS, params={"limit": 50}, timeout=15)
        response.raise_for_status()
        entries = response.json().get("articles", [])
    except Exception as e:
        logger.warning(f"⚠️ ESPN news unavailable: {e}")
        return [], []

    stories, recaps = [], []
    for entry in entries:
        link = ((entry.get("links") or {}).get("web") or {}).get("href")
        kind = {"HeadlineNews": stories, "Recap": recaps}.get(entry.get("type"))
        if not link or kind is None or not entry.get("published"):
            continue
        published = datetime.fromisoformat(entry["published"].replace("Z", "+00:00"))
        if window[0] <= published <= window[1]:
            kind.append({
                "source": "ESPN",
                "title": entry.get("headline", "No title"),
                "link": link.replace("http://", "https://", 1),
                "published": published.strftime("%d %b %Y %H:%M"),
                "summary": entry.get("description", ""),
            })
    return stories, recaps


def fetch_night_links(window, count=LINKS_IN_MAIL):
    """
    Liens du mail. À l'heure de l'envoi, Trashtalk et The Athletic ont encore peu publié : on complète
    avec les papiers d'ESPN de la nuit, puis ses résumés de matchs et les derniers articles de The Athletic.
    """
    stories, recaps = _fetch_espn(window)
    links = fetch_news(window=window) + stories
    if len(links) >= count:
        return links[:count]
    athletic = ({"name": "The Athletic", "url": ATHLETIC_RSS, "limit": count},)
    older = fetch_news(athletic, window=(window[0] - timedelta(days=1), window[0]))
    fill = [a for round_ in zip_longest(recaps, older) for a in round_ if a]
    return (links + fill)[:count]


def _scrape_article_content(url):
    if not url or url == "#":
        return None  # URL invalide

    try:
        logger.debug(f"Scraping article: {url}")

        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()  # Lève exception si erreur HTTP (404, 500, etc.)

        soup = BeautifulSoup(response.content, 'html.parser')

        article_body = soup.find('div', class_='article-body')

        if not article_body:
            article_body = soup.find('article') or soup.find('div', {'data-module': 'story'})

        if article_body:
            paragraphs = article_body.find_all('p')

            content = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])

            if len(content) > 1500:
                content = content[:1500] + "..."

            logger.debug(f"✅ Scraped {len(content)} chars from article")
            return content

        logger.debug("⚠️ Could not find article body")
        return None

    except Exception as e:
        logger.debug(f"⚠️ Failed to scrape article: {e}")
        return None
