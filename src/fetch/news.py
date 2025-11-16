# src/fetch/news.py
import feedparser
from datetime import datetime
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def fetch_news(limit=5, include_content=True):
    """Fetch NBA news from ESPN RSS feed with optional content scraping."""
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
                
                article = {
                    "title": entry.get("title", "No title"),
                    "link": entry.get("link", "#"),
                    "published": date_str,
                }
                
                # Optionally fetch article content
                if include_content:
                    content = _scrape_article_content(entry.get("link"))
                    if content:
                        article["content"] = content
                        article["summary"] = content[:500] + "..." if len(content) > 500 else content
                
                headlines.append(article)
            except Exception as e:
                logger.warning(f"⚠️ Error parsing news entry: {e}")
                continue
        
        logger.info(f"✅ Fetched {len(headlines)} NBA news articles from ESPN")
        return headlines
    except Exception as e:
        logger.error(f"❌ Failed to fetch news: {e}")
        return []


def _scrape_article_content(url):
    """Scrape article content from ESPN page."""
    if not url or url == "#":
        return None
    
    try:
        logger.debug(f"Scraping article: {url}")
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # ESPN article content is typically in div with class 'article-body'
        article_body = soup.find('div', class_='article-body')
        if not article_body:
            # Try alternative selectors
            article_body = soup.find('article') or soup.find('div', {'data-module': 'story'})
        
        if article_body:
            # Extract all paragraphs
            paragraphs = article_body.find_all('p')
            content = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            
            # Limit to ~1000 characters to avoid token explosion
            if len(content) > 1000:
                content = content[:1000] + "..."
            
            logger.debug(f"✅ Scraped {len(content)} chars from article")
            return content
        
        logger.debug("⚠️ Could not find article body")
        return None
        
    except Exception as e:
        logger.debug(f"⚠️ Failed to scrape article: {e}")
        return None
