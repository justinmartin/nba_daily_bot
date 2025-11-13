# src/fetch/news.py
import feedparser
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def fetch_news(limit=5):
    """Fetch NBA news from ESPN RSS feed."""
    url = "https://www.espn.com/espn/rss/nba/news"
    try:
        feed = feedparser.parse(url)
        
        # Check for feed parsing errors
        if feed.bozo:
            logger.warning(f"⚠️ Feed parsing issue: {feed.bozo_exception}")
        
        headlines = []
        for entry in feed.entries[:limit]:
            try:
                published = entry.get("published_parsed")
                date_str = datetime(*published[:6]).strftime("%d %b %Y %H:%M") if published else "N/A"
                headlines.append({
                    "title": entry.get("title", "No title"),
                    "link": entry.get("link", "#"),
                    "published": date_str,
                })
            except Exception as e:
                logger.warning(f"⚠️ Error parsing news entry: {e}")
                continue
        
        logger.info(f"✅ Fetched {len(headlines)} NBA news articles from ESPN")
        return headlines
    except Exception as e:
        logger.error(f"❌ Failed to fetch news: {e}")
        return []
