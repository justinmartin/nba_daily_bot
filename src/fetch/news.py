"""
ESPN NBA News Fetcher.

Ce module récupère les actualités NBA depuis le flux RSS d'ESPN et scrape
le contenu complet de chaque article pour enrichir la newsletter.
"""

# src/fetch/news.py
import feedparser
from datetime import datetime
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# URL du flux RSS ESPN NBA
ESPN_NBA_RSS = "https://www.espn.com/espn/rss/nba/news"


def fetch_news(limit=5, include_content=True):
    """
    Récupère les dernières actualités NBA depuis ESPN.
    
    Processus:
    1. Parse le flux RSS ESPN NBA (feedparser)
    2. Extrait titre, lien, date de publication
    3. Optionnel: Scrape le contenu complet de chaque article (BeautifulSoup)
    
    Args:
        limit (int): Nombre maximum d'articles à récupérer (défaut: 5)
        include_content (bool): Si True, scrape le contenu complet (défaut: True)
    
    Returns:
        list: Liste de dicts contenant:
              - title: Titre de l'article
              - link: URL de l'article
              - published: Date de publication formatée
              - content (optionnel): Texte complet de l'article
              - summary (optionnel): Résumé (500 premiers caractères)
    
    Gestion des erreurs:
        - Si flux RSS invalide: log warning mais continue
        - Si article non parsable: skip et continue avec les autres
        - Si échec global: retourne liste vide (pas de crash)
    """
    try:
        # === ÉTAPE 1: Récupération du flux RSS ===
        feed = feedparser.parse(ESPN_NBA_RSS)
        
        # Vérification de la qualité du flux RSS
        # feed.bozo = True si le flux est mal formé (mais feedparser le parse quand même)
        if feed.bozo:
            logger.warning(f"⚠️ Feed parsing issue: {feed.bozo_exception}")
        
        # === ÉTAPE 2: Parcourt les articles du flux RSS ===
        headlines = []
        for entry in feed.entries[:limit]:  # Limite au nombre d'articles demandés
            try:
                # Extrait la date de publication (tuple Python time)
                published = entry.get("published_parsed")
                # Formate la date en string lisible: "24 Nov 2025 14:30"
                date_str = datetime(*published[:6]).strftime("%d %b %Y %H:%M") if published else "N/A"
                
                # Crée l'objet article avec les infos de base
                article = {
                    "title": entry.get("title", "No title"),
                    "link": entry.get("link", "#"),
                    "published": date_str,
                }
                
                # === ÉTAPE 3: Scrape optionnel du contenu complet ===
                if include_content:
                    content = _scrape_article_content(entry.get("link"))
                    if content:
                        article["content"] = content
                        # Résumé = 500 premiers caractères
                        article["summary"] = content[:500] + "..." if len(content) > 500 else content
                
                headlines.append(article)
                
            except Exception as e:
                # Si un article pose problème, on log et on continue avec les autres
                logger.warning(f"⚠️ Error parsing news entry: {e}")
                continue
        
        logger.info(f"✅ Fetched {len(headlines)} NBA news articles from ESPN")
        return headlines
        
    except Exception as e:
        # Erreur globale (réseau, serveur ESPN down, etc.)
        logger.error(f"❌ Failed to fetch news: {e}")
        return []  # Retourne liste vide au lieu de crash


def _scrape_article_content(url):
    """
    Scrape le contenu complet d'un article ESPN.
    
    Processus:
    1. Télécharge la page HTML (requests)
    2. Parse le HTML (BeautifulSoup)
    3. Trouve la div contenant l'article
    4. Extrait tous les paragraphes <p>
    5. Limite à 1000 caractères (évite token explosion)
    
    Args:
        url (str): URL de l'article ESPN
    
    Returns:
        str: Contenu texte de l'article (max 1000 chars)
        None: Si scraping échoue ou URL invalide
    
    Technique anti-bot:
        - User-Agent = Chrome/Windows pour éviter le blocage
        - Timeout 10s pour éviter blocage infini
    """
    if not url or url == "#":
        return None  # URL invalide
    
    try:
        logger.debug(f"Scraping article: {url}")
        
        # === ÉTAPE 1: Télécharge la page HTML ===
        # User-Agent = se fait passer pour Chrome sur Windows (évite blocage anti-bot)
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()  # Lève exception si erreur HTTP (404, 500, etc.)
        
        # === ÉTAPE 2: Parse le HTML avec BeautifulSoup ===
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # === ÉTAPE 3: Trouve le conteneur de l'article ===
        # ESPN utilise généralement la class 'article-body'
        article_body = soup.find('div', class_='article-body')
        
        # Si pas trouvé, essaie d'autres sélecteurs alternatifs
        if not article_body:
            article_body = soup.find('article') or soup.find('div', {'data-module': 'story'})
        
        # === ÉTAPE 4: Extrait le contenu texte ===
        if article_body:
            # Trouve tous les paragraphes <p> dans l'article
            paragraphs = article_body.find_all('p')
            
            # Join tous les textes de paragraphes (sans HTML)
            # List comprehension: garde seulement les paragraphes non-vides
            content = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            
            # Limite à ~1000 caractères pour éviter explosion de tokens LLM
            if len(content) > 1000:
                content = content[:1000] + "..."
            
            logger.debug(f"✅ Scraped {len(content)} chars from article")
            return content
        
        # Aucun contenu d'article trouvé dans la page
        logger.debug("⚠️ Could not find article body")
        return None
        
    except Exception as e:
        # Erreur de scraping (timeout, parsing, etc.) - pas critique
        logger.debug(f"⚠️ Failed to scrape article: {e}")
        return None
