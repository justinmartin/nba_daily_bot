
import logging
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

NBA_CHANNEL_ID = "UCWJ2lWNubArHWmf3FIHbfcQ"

def get_top_10_plays_video(target_date=None):
    try:
        if target_date is None:
            target_date = datetime.now().date()
        
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={NBA_CHANNEL_ID}"
        
        logger.debug(f"Fetching NBA YouTube videos for {target_date}...")
        
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()  # Lève une exception si erreur HTTP (404, 500, etc.)
        
        soup = BeautifulSoup(response.content, 'xml')
        entries = soup.find_all('entry')  # Chaque <entry> = une vidéo
        
        date_formats = [
            target_date.strftime("%B %-d, %Y"),      # "November 15, 2025"
            target_date.strftime("%b %-d, %Y"),      # "Nov 15, 2025"
            target_date.strftime("%B %d, %Y"),       # "November 15, 2025" (avec zéro)
            target_date.strftime("%b %d, %Y"),       # "Nov 15, 2025" (avec zéro)
        ]
        
        yesterday = target_date - timedelta(days=1)
        date_formats.extend([
            yesterday.strftime("%B %-d, %Y"),
            yesterday.strftime("%b %-d, %Y"),
            yesterday.strftime("%B %d, %Y"),
            yesterday.strftime("%b %d, %Y"),
        ])
        
        for entry in entries:
            title_tag = entry.find('title')
            if not title_tag:
                continue  # Skip si pas de titre
            
            title = title_tag.text
            
            if "top 10" not in title.lower() or "plays" not in title.lower():
                continue  # Ce n'est pas une vidéo Top 10 Plays
            
            date_match = False
            for date_format in date_formats:
                if date_format in title:
                    date_match = True
                    break  # Date trouvée, on sort de la boucle
            
            if not date_match:
                continue  # Date ne correspond pas
            
            video_id_tag = entry.find('yt:videoId')
            if not video_id_tag:
                continue  # Skip si pas d'ID
            
            video_id = video_id_tag.text
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            thumbnail = None
            media_group = entry.find('media:group')
            if media_group:
                thumbnail_tag = media_group.find('media:thumbnail')
                if thumbnail_tag and thumbnail_tag.has_attr('url'):
                    thumbnail = thumbnail_tag['url']
            
            published_tag = entry.find('published')
            published = published_tag.text if published_tag else None
            
            logger.info(f"✅ Found Top 10 Plays video: {title}")
            
            return {
                'title': title,
                'url': video_url,
                'thumbnail': thumbnail,
                'published': published,
                'video_id': video_id
            }
        
        logger.warning(f"⚠️ No Top 10 Plays video found for {target_date}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch Top 10 Plays video: {e}")
        return None
