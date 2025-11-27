"""
Fallback API pour les scores NBA.

Ce module fournit une alternative à stats.nba.com en cas de timeout/blocage.
Utilise ESPN API (gratuite, pas besoin de clé) comme backup.
"""

import logging
from datetime import date
from dataclasses import dataclass
import requests
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Game:
    """Structure identique à scores.py pour compatibilité."""
    id: str
    date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    home_wins: int = None
    home_losses: int = None
    away_wins: int = None
    away_losses: int = None


# Mapping ESPN team names → noms courts
ESPN_TEAM_MAP = {
    'Atlanta Hawks': 'Hawks',
    'Boston Celtics': 'Celtics',
    'Brooklyn Nets': 'Nets',
    'Charlotte Hornets': 'Hornets',
    'Chicago Bulls': 'Bulls',
    'Cleveland Cavaliers': 'Cavaliers',
    'Dallas Mavericks': 'Mavericks',
    'Denver Nuggets': 'Nuggets',
    'Detroit Pistons': 'Pistons',
    'Golden State Warriors': 'Warriors',
    'Houston Rockets': 'Rockets',
    'Indiana Pacers': 'Pacers',
    'LA Clippers': 'Clippers',
    'Los Angeles Lakers': 'Lakers',
    'Memphis Grizzlies': 'Grizzlies',
    'Miami Heat': 'Heat',
    'Milwaukee Bucks': 'Bucks',
    'Minnesota Timberwolves': 'Timberwolves',
    'New Orleans Pelicans': 'Pelicans',
    'New York Knicks': 'Knicks',
    'Oklahoma City Thunder': 'Thunder',
    'Orlando Magic': 'Magic',
    'Philadelphia 76ers': '76ers',
    'Phoenix Suns': 'Suns',
    'Portland Trail Blazers': 'Trail Blazers',
    'Sacramento Kings': 'Kings',
    'San Antonio Spurs': 'Spurs',
    'Toronto Raptors': 'Raptors',
    'Utah Jazz': 'Jazz',
    'Washington Wizards': 'Wizards',
}


def get_games_from_espn(d: date) -> List[Game]:
    """
    Récupère les scores depuis ESPN API (fallback).
    
    ESPN a une API non documentée mais gratuite et rapide.
    Plus fiable que stats.nba.com pour GitHub Actions.
    
    Args:
        d (date): Date des matchs
    
    Returns:
        List[Game]: Liste des matchs avec scores
    
    Note:
        ESPN API ne fournit pas toujours les records (W-L),
        donc home_wins/losses peuvent être None.
    """
    try:
        # ESPN API endpoint (format : YYYYMMDD)
        date_str = d.strftime('%Y%m%d')
        url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}'
        
        logger.info(f"📡 Fetching from ESPN API (fallback) for {d}...")
        
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        games = []
        events = data.get('events', [])
        
        logger.info(f"Found {len(events)} games on ESPN")
        
        for event in events:
            try:
                # Extraire les équipes
                competitions = event.get('competitions', [{}])[0]
                competitors = competitions.get('competitors', [])
                
                if len(competitors) != 2:
                    continue
                
                # ESPN met home en premier, away en second (parfois inversé)
                home_comp = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
                away_comp = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])
                
                home_team = home_comp.get('team', {}).get('displayName', 'Unknown')
                away_team = away_comp.get('team', {}).get('displayName', 'Unknown')
                
                # Mapper vers noms courts
                home_team = ESPN_TEAM_MAP.get(home_team, home_team)
                away_team = ESPN_TEAM_MAP.get(away_team, away_team)
                
                home_score = int(home_comp.get('score', 0))
                away_score = int(away_comp.get('score', 0))
                
                # Records (si disponibles)
                home_record = home_comp.get('records', [{}])[0].get('summary')
                away_record = away_comp.get('records', [{}])[0].get('summary')
                
                home_wins, home_losses = None, None
                away_wins, away_losses = None, None
                
                if home_record and '-' in home_record:
                    parts = home_record.split('-')
                    home_wins = int(parts[0])
                    home_losses = int(parts[1])
                
                if away_record and '-' in away_record:
                    parts = away_record.split('-')
                    away_wins = int(parts[0])
                    away_losses = int(parts[1])
                
                game = Game(
                    id=event.get('id', ''),
                    date=d.strftime('%Y-%m-%d'),
                    home_team=home_team,
                    away_team=away_team,
                    home_score=home_score,
                    away_score=away_score,
                    home_wins=home_wins,
                    home_losses=home_losses,
                    away_wins=away_wins,
                    away_losses=away_losses
                )
                games.append(game)
                
            except Exception as e:
                logger.warning(f"⚠️ Error parsing game from ESPN: {e}")
                continue
        
        logger.info(f"✅ Successfully fetched {len(games)} games from ESPN")
        return games
        
    except Exception as e:
        logger.error(f"❌ ESPN API fallback also failed: {e}")
        return []
