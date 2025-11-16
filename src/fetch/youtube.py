import logging
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def get_top_10_plays_video(target_date=None):
    """
    Fetch NBA's Top 10 Plays video for a given date from YouTube.
    Returns dict with title, url, thumbnail if found, None otherwise.
    """
    try:
        if target_date is None:
            target_date = datetime.now().date()
        
        # NBA YouTube channel RSS feed
        nba_channel_id = "UCWJ2lWNubArHWmf3FIHbfcQ"  # Official NBA channel
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={nba_channel_id}"
        
        logger.debug(f"Fetching NBA YouTube videos for {target_date}...")
        
        # Fetch RSS feed
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()
        
        # Parse XML
        soup = BeautifulSoup(response.content, 'xml')
        entries = soup.find_all('entry')
        
        # Format date variations to match title
        # NBA uses formats like "November 15, 2025" or "Nov 15, 2025"
        date_formats = [
            target_date.strftime("%B %-d, %Y"),      # November 15, 2025
            target_date.strftime("%b %-d, %Y"),      # Nov 15, 2025
            target_date.strftime("%B %d, %Y"),       # November 15, 2025 (with leading zero)
            target_date.strftime("%b %d, %Y"),       # Nov 15, 2025 (with leading zero)
        ]
        
        # Also check yesterday's date (videos are sometimes uploaded next day)
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
                continue
            
            title = title_tag.text
            
            # Check if it's a Top 10 Plays video
            if "top 10" not in title.lower() or "plays" not in title.lower():
                continue
            
            # Check if date matches
            date_match = False
            for date_format in date_formats:
                if date_format in title:
                    date_match = True
                    break
            
            if not date_match:
                continue
            
            # Extract video info
            video_id_tag = entry.find('yt:videoId')
            if not video_id_tag:
                continue
            
            video_id = video_id_tag.text
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Extract thumbnail
            thumbnail = None
            media_group = entry.find('media:group')
            if media_group:
                thumbnail_tag = media_group.find('media:thumbnail')
                if thumbnail_tag and thumbnail_tag.has_attr('url'):
                    thumbnail = thumbnail_tag['url']
            
            # Extract published date
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


def format_top_10_section(video_info):
    """
    Format the Top 10 Plays section for the newsletter.
    Returns HTML string.
    """
    if not video_info:
        return ""
    
    html = f"""
    <div style="margin-top: 15px; padding: 15px; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%); border-radius: 8px; text-align: center;">
        <h3 style="margin: 0 0 10px 0; color: white; font-size: 16px;">🎬 TOP 10 PLAYS OF THE NIGHT</h3>
        <a href="{video_info['url']}" style="display: inline-block; background: white; color: #ee5a6f; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px; margin-top: 8px;">
            ▶️ Watch Highlights
        </a>
        <p style="margin: 10px 0 0 0; font-size: 12px; color: rgba(255,255,255,0.9);">{video_info['title']}</p>
    </div>
    """
    
    return html
