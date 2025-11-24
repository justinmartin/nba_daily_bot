"""
YouTube video fetcher for NBA Top 10 Plays.

Ce module récupère la vidéo "Top 10 Plays" officielle de la NBA depuis YouTube
en utilisant le flux RSS de la chaîne NBA officielle.
"""

import logging
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ID de la chaîne YouTube officielle NBA
NBA_CHANNEL_ID = "UCWJ2lWNubArHWmf3FIHbfcQ"


def get_top_10_plays_video(target_date=None):
    """
    Récupère la vidéo "Top 10 Plays" de la NBA pour une date donnée.
    
    Processus:
    1. Récupère le flux RSS de la chaîne YouTube NBA
    2. Parse toutes les vidéos récentes (XML)
    3. Cherche celle qui contient "Top 10" et "Plays" dans le titre
    4. Vérifie que la date correspond (aujourd'hui ou hier)
    
    Args:
        target_date (date, optional): Date cible. Par défaut = aujourd'hui.
    
    Returns:
        dict: {title, url, thumbnail, published, video_id} si trouvée
        None: Si aucune vidéo Top 10 trouvée
    
    Gestion des erreurs:
        - Timeout réseau après 10s
        - Continue si YouTube RSS est indisponible (retourne None)
    """
    try:
        # Par défaut, on cherche la vidéo d'aujourd'hui
        if target_date is None:
            target_date = datetime.now().date()
        
        # Construction de l'URL du flux RSS YouTube
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={NBA_CHANNEL_ID}"
        
        logger.debug(f"Fetching NBA YouTube videos for {target_date}...")
        
        # === ÉTAPE 1: Récupération du flux RSS ===
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()  # Lève une exception si erreur HTTP (404, 500, etc.)
        
        # === ÉTAPE 2: Parse le XML du flux RSS ===
        soup = BeautifulSoup(response.content, 'xml')
        entries = soup.find_all('entry')  # Chaque <entry> = une vidéo
        
        # === ÉTAPE 3: Prépare les formats de date possibles ===
        # La NBA utilise différents formats dans les titres de vidéos
        # Exemples: "November 15, 2025" ou "Nov 15, 2025"
        date_formats = [
            target_date.strftime("%B %-d, %Y"),      # "November 15, 2025"
            target_date.strftime("%b %-d, %Y"),      # "Nov 15, 2025"
            target_date.strftime("%B %d, %Y"),       # "November 15, 2025" (avec zéro)
            target_date.strftime("%b %d, %Y"),       # "Nov 15, 2025" (avec zéro)
        ]
        
        # La vidéo Top 10 est parfois uploadée le lendemain
        # On check aussi la veille pour être sûr
        yesterday = target_date - timedelta(days=1)
        date_formats.extend([
            yesterday.strftime("%B %-d, %Y"),
            yesterday.strftime("%b %-d, %Y"),
            yesterday.strftime("%B %d, %Y"),
            yesterday.strftime("%b %d, %Y"),
        ])
        
        # === ÉTAPE 4: Parcourt toutes les vidéos du flux RSS ===
        for entry in entries:
            # Récupère le titre de la vidéo
            title_tag = entry.find('title')
            if not title_tag:
                continue  # Skip si pas de titre
            
            title = title_tag.text
            
            # Filtre 1: Doit contenir "top 10" ET "plays" (case insensitive)
            if "top 10" not in title.lower() or "plays" not in title.lower():
                continue  # Ce n'est pas une vidéo Top 10 Plays
            
            # Filtre 2: Doit contenir une des dates formatées
            date_match = False
            for date_format in date_formats:
                if date_format in title:
                    date_match = True
                    break  # Date trouvée, on sort de la boucle
            
            if not date_match:
                continue  # Date ne correspond pas
            
            # === ÉTAPE 5: Extrait les infos de la vidéo ===
            # ID de la vidéo YouTube (ex: "dQw4w9WgXcQ")
            video_id_tag = entry.find('yt:videoId')
            if not video_id_tag:
                continue  # Skip si pas d'ID
            
            video_id = video_id_tag.text
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Thumbnail (image miniature)
            thumbnail = None
            media_group = entry.find('media:group')
            if media_group:
                thumbnail_tag = media_group.find('media:thumbnail')
                if thumbnail_tag and thumbnail_tag.has_attr('url'):
                    thumbnail = thumbnail_tag['url']
            
            # Date de publication
            published_tag = entry.find('published')
            published = published_tag.text if published_tag else None
            
            logger.info(f"✅ Found Top 10 Plays video: {title}")
            
            # Retourne les infos de la vidéo trouvée
            return {
                'title': title,
                'url': video_url,
                'thumbnail': thumbnail,
                'published': published,
                'video_id': video_id
            }
        
        # Aucune vidéo Top 10 trouvée pour cette date
        logger.warning(f"⚠️ No Top 10 Plays video found for {target_date}")
        return None
        
    except Exception as e:
        # En cas d'erreur (réseau, parsing XML, etc.)
        # On log l'erreur mais on continue (pas critique)
        logger.error(f"❌ Failed to fetch Top 10 Plays video: {e}")
        return None


def format_top_10_section(video_info):
    """
    Génère le HTML de la section "Top 10 Plays" pour la newsletter.
    
    Args:
        video_info (dict): Infos de la vidéo (title, url, thumbnail, etc.)
                          ou None si aucune vidéo trouvée
    
    Returns:
        str: HTML formaté avec bouton de lecture
             Chaîne vide si video_info est None
    
    Style:
        - Fond dégradé rouge (couleurs NBA)
        - Bouton blanc avec lien YouTube
        - Titre de la vidéo en petit sous le bouton
    """
    if not video_info:
        return ""  # Pas de vidéo = pas de section
    
    # HTML avec inline styles (compatible email)
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
