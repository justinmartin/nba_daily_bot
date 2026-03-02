
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Broadcast channel color scheme (French market)
BROADCAST_STYLES = {
    'bein sports':  {'color': '#6B2EAF', 'bold': True,  'label': 'beIN Sports'},
    'bein':         {'color': '#6B2EAF', 'bold': True,  'label': 'beIN Sports'},
    'prime video':  {'color': '#00A8E1', 'bold': False, 'label': 'Prime Video'},
    'prime':        {'color': '#00A8E1', 'bold': False, 'label': 'Prime Video'},
    'amazon prime': {'color': '#00A8E1', 'bold': False, 'label': 'Prime Video'},
    'league pass':  {'color': '#1D428A', 'bold': False, 'label': 'League Pass'},
    'nba tv':       {'color': '#1D428A', 'bold': False, 'label': 'NBA TV'},
    'canal+':       {'color': '#1A1A1A', 'bold': False, 'label': 'Canal+'},
}


def _broadcaster_badge(name: str) -> str:
    """Return an HTML badge for a broadcaster name."""
    key = name.lower().strip()
    style = BROADCAST_STYLES.get(key, {'color': '#555', 'bold': False, 'label': name})
    weight = 'font-weight:700;' if style['bold'] else 'font-weight:600;'
    return (
        f'<span style="display:inline-block; padding:3px 10px; margin:2px 4px; '
        f'border-radius:4px; font-size:12px; {weight} '
        f'color:white; background:{style["color"]};">'
        f'{style["label"]}</span>'
    )


def _render_upcoming_games(upcoming_games) -> str:
    """Render the 'Matchs à venir' section HTML."""
    section = """
                <div class="section">
                    <h2>📅 MATCHS À VENIR — CE SOIR</h2>
                    <div class="scores-list">"""

    for g in upcoming_games:
        # Only show scheduled (not started) games
        if g.game_status == 3:
            continue

        badges = ' '.join(_broadcaster_badge(b) for b in g.broadcasters)

        section += f"""
                        <div class="score-item" style="display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:8px;">
                            <div style="flex:1; min-width:200px;">
                                <div style="font-weight:700; font-size:15px; color:#1a1a1a;">
                                    {g.away_team} <span style="color:#999; font-size:12px;">({g.away_record})</span>
                                    &nbsp;@&nbsp;
                                    {g.home_team} <span style="color:#999; font-size:12px;">({g.home_record})</span>
                                </div>
                                <div style="margin-top:6px; font-size:13px; color:#667eea; font-weight:600;">
                                    🕐 {g.game_time_fr}
                                </div>
                            </div>
                            <div style="text-align:right;">
                                {badges}
                            </div>
                        </div>"""

    section += """
                    </div>
                </div>"""
    return section


def render_email(summary_text, news, top_performers=None, games=None, organized_games=None, top_10_video=None, upcoming_games=None):
    if not summary_text or not summary_text.strip():
        logger.warning("Summary text is empty")
        summary_text = "No summary available"
    
    if news is None:
        news = []
    
    if top_performers is None:
        top_performers = []
        
    if games is None:
        games = []
    
    if organized_games is None:
        organized_games = []
    
    if top_10_video is None:
        top_10_video = None
    
    if upcoming_games is None:
        upcoming_games = []
    
    today = datetime.now().strftime("%A, %B %d %Y")
    summary_html = summary_text.replace("\n", "<br>")
    
    
    html = """<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                color: #1a1a1a; 
                background: #f5f5f5; 
                padding: 0; 
                margin: 0;
                line-height: 1.6;
            }
            .container { 
                max-width: 100%; 
                width: 100%; 
                background: white; 
                margin: 0;
                padding: 0;
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                padding: 30px 20px; 
                text-align: center; 
            }
            .header h1 { 
                margin: 0; 
                font-size: 28px; 
                font-weight: 700;
                word-break: break-word;
            }
            .header p { 
                margin: 10px 0 0 0; 
                font-size: 13px; 
                opacity: 0.9; 
            }
            .content { 
                padding: 20px; 
            }
            .section { 
                margin-bottom: 25px; 
            }
            .section h2 { 
                font-size: 18px; 
                color: #667eea; 
                border-bottom: 3px solid #667eea; 
                padding-bottom: 10px; 
                margin: 0 0 15px 0;
                word-break: break-word;
            }
            .summary { 
                background: #f8f9ff; 
                padding: 15px; 
                border-left: 4px solid #667eea; 
                border-radius: 4px; 
                line-height: 1.7; 
                font-size: 14px;
                word-break: break-word;
            }
            .summary p { margin: 10px 0; }
            .summary p:first-child { margin-top: 0; }
            .summary p:last-child { margin-bottom: 0; }
            
            .scores-list {
                list-style: none;
                padding: 0;
                margin: 0;
            }
            .score-item {
                padding: 12px;
                margin-bottom: 10px;
                background: #f8f9ff;
                border-left: 4px solid #667eea;
                border-radius: 4px;
                font-size: 14px;
                line-height: 1.6;
            }
            .score-item .teams {
                font-weight: 600;
                color: #333;
            }
            .score-item .result {
                color: #667eea;
                font-weight: 600;
                font-size: 15px;
                margin-top: 5px;
            }
            
            table { 
                width: 100%; 
                border-collapse: collapse; 
                margin-top: 10px;
                font-size: 13px;
            }
            th { 
                background: #667eea; 
                color: white; 
                padding: 10px 8px; 
                text-align: left; 
                font-weight: 600; 
                font-size: 12px;
                border: none;
            }
            td { 
                padding: 10px 8px; 
                border-bottom: 1px solid #e0e0e0; 
                font-size: 13px;
                word-break: break-word;
            }
            tr:hover { background: #f9f9f9; }
            
            ul { 
                list-style: none; 
                padding: 0; 
                margin: 0; 
            }
            li { 
                padding: 12px 0; 
                border-bottom: 1px solid #e0e0e0; 
                font-size: 13px; 
                line-height: 1.6;
            }
            li:last-child { border-bottom: none; }
            
            a { 
                color: #667eea; 
                text-decoration: none; 
                font-weight: 600;
                word-break: break-word;
            }
            a:hover { color: #764ba2; }
            
            small { 
                display: block; 
                color: #999; 
                margin-top: 4px; 
                font-size: 11px; 
            }
            
            .footer { 
                background: #f8f9fa; 
                padding: 15px 20px; 
                text-align: center; 
                font-size: 11px; 
                color: #888; 
                border-top: 1px solid #e0e0e0;
            }
            .footer p { margin: 0; }
            
            @media (max-width: 600px) {
                .header { padding: 20px 15px; }
                .header h1 { font-size: 22px; }
                .header p { font-size: 12px; }
                .content { padding: 15px; }
                .section { margin-bottom: 20px; }
                .section h2 { font-size: 16px; }
                .summary { padding: 12px; font-size: 13px; }
                .score-item { padding: 10px; margin-bottom: 8px; }
                table { font-size: 12px; }
                th { padding: 8px 5px; font-size: 11px; }
                td { padding: 8px 5px; font-size: 12px; }
                li { padding: 10px 0; font-size: 12px; }
                a { font-size: 13px; }
                small { font-size: 10px; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏀 NBA DAILY RECAP</h1>
                <p>""" + today + """</p>
            </div>
            
            <div class="content">
                <div class="section">
                    <h2>🔥 TONIGHT'S SUMMARY</h2>
                    <div class="summary">
                        """ + summary_html + """
                    </div>
                </div>"""
    
    if organized_games:
        html += """
                <div class="section">
                    <h2>📊 GAME RESULTS & MATCH DETAILS</h2>
                    <div class="scores-list">"""
        
        for game in organized_games:
            html += f"""
                        <div class="score-item">
                            <div class="teams">
                                🆆 {game['winner']} ({game['winner_record']}) {game['winner_score']} - {game['loser_score']} 🅻 {game['loser']} ({game['loser_record']})
                            </div>
                            <div class="result" style="margin-top: 8px;">
                                <strong>Margin:</strong> {game['margin']} points
                            </div>"""
            
            if game['winner_top_performers']:
                html += "<div style='margin-top: 10px; font-size: 13px; color: #1a5f1a; background: #f0f8f0; padding: 8px; border-radius: 3px;'><strong>🏆 Winner's Top Performers:</strong><br>"
                for p in game['winner_top_performers']:
                    stats = f"{p.get('pts', 0)}pts, {p.get('reb', 0)}reb, {p.get('ast', 0)}ast, FG: {p.get('fg_pct', 0):.0f}%"
                    extras = []
                    if p.get('blk'):
                        extras.append(f"{p.get('blk')}blk")
                    if p.get('stl'):
                        extras.append(f"{p.get('stl')}stl")
                    if extras:
                        stats += f", {', '.join(extras)}"
                    html += f"&nbsp;&nbsp;• <strong>{p['name']}</strong>: {stats}<br>"
                html += "</div>"
            
            if game['loser_top_performers']:
                html += "<div style='margin-top: 8px; font-size: 13px; color: #663333; background: #f8f0f0; padding: 8px; border-radius: 3px;'><strong>🔥 Best from Losing Team:</strong><br>"
                p = game['loser_top_performers'][0]
                stats = f"{p.get('pts', 0)}pts, {p.get('reb', 0)}reb, {p.get('ast', 0)}ast, FG: {p.get('fg_pct', 0):.0f}%"
                extras = []
                if p.get('blk'):
                    extras.append(f"{p.get('blk')}blk")
                if p.get('stl'):
                    extras.append(f"{p.get('stl')}stl")
                if extras:
                    stats += f", {', '.join(extras)}"
                html += f"&nbsp;&nbsp;• <strong>{p['name']}</strong>: {stats}<br>"
                html += "</div>"
            
            html += """
                        </div>"""
        
        html += """
                    </div>
                </div>"""
    elif games:
        html += """
                <div class="section">
                    <h2>📊 GAME RESULTS</h2>
                    <div class="scores-list">"""
        
        for game in games:
            away_wins = f"({game.away_wins}-{game.away_losses})" if game.away_wins else ""
            home_wins = f"({game.home_wins}-{game.home_losses})" if game.home_wins else ""
            
            if game.away_score > game.home_score:
                away_team_display = f"🆆 {game.away_team} {away_wins}"
                home_team_display = f"🅻 {game.home_team} {home_wins}"
            else:
                away_team_display = f"🅻 {game.away_team} {away_wins}"
                home_team_display = f"🆆 {game.home_team} {home_wins}"
            
            html += f"""
                        <div class="score-item">
                            <div class="teams">{away_team_display} @ {home_team_display}</div>
                            <div class="result">{game.away_score} - {game.home_score}</div>
                        </div>"""
        
        html += """
                    </div>
                </div>"""
    
    html += """
                <div class="section">
                    <h2>👑 TOP 5 PERFORMERS OF THE NIGHT</h2>"""
    
    if top_performers:
        seen_names = set()
        deduplicated = []
        for p in top_performers:
            player_name = p.get('name', 'Unknown')
            if player_name not in seen_names:
                seen_names.add(player_name)
                deduplicated.append(p)
        
        sorted_performers = sorted(deduplicated, key=lambda x: x.get('pts', 0), reverse=True)[:5]
        
        html += """
                    <table style="border-collapse: collapse; width: 100%; margin-top: 12px; font-size: 13px;">
                        <thead>
                            <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                                <th style="padding: 12px 10px; text-align: left; font-weight: 600; border: none;">#</th>
                                <th style="padding: 12px 10px; text-align: left; font-weight: 600; border: none;">PLAYER</th>
                                <th style="padding: 12px 10px; text-align: center; font-weight: 600; border: none;">PTS</th>
                                <th style="padding: 12px 10px; text-align: center; font-weight: 600; border: none;">REB</th>
                                <th style="padding: 12px 10px; text-align: center; font-weight: 600; border: none;">AST</th>
                                <th style="padding: 12px 10px; text-align: center; font-weight: 600; border: none;">FG%</th>
                                <th style="padding: 12px 10px; text-align: center; font-weight: 600; border: none;">3P%</th>
                                <th style="padding: 12px 10px; text-align: center; font-weight: 600; border: none;">BLK/STL</th>
                            </tr>
                        </thead>
                        <tbody>"""
        
        for rank, p in enumerate(sorted_performers, 1):
            blk_stl = []
            if p.get('blk'):
                blk_stl.append(f"{int(p['blk'])} BLK")
            if p.get('stl'):
                blk_stl.append(f"{int(p['stl'])} STL")
            blk_stl_str = " / ".join(blk_stl) if blk_stl else "-"
            
            row_bg = "#f9f9f9" if rank % 2 == 0 else "white"
            pts = int(p.get('pts', 0))
            rank_emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
            
            html += f"""
                            <tr style="background: {row_bg}; border-bottom: 1px solid #e0e0e0;">
                                <td style="padding: 12px 10px; font-weight: 700; color: #667eea;">{rank_emoji}</td>
                                <td style="padding: 12px 10px;"><strong>{p.get('name', 'Unknown')}</strong><br><span style="font-size: 11px; color: #999;">{p.get('team', 'N/A')}</span></td>
                                <td style="padding: 12px 10px; text-align: center; font-weight: 600; color: #667eea; font-size: 14px;">{pts}</td>
                                <td style="padding: 12px 10px; text-align: center;">{int(p.get('reb', 0))}</td>
                                <td style="padding: 12px 10px; text-align: center;">{int(p.get('ast', 0))}</td>
                                <td style="padding: 12px 10px; text-align: center; color: #2d5016; font-weight: 600;">{p.get('fg_pct', 'N/A')}</td>
                                <td style="padding: 12px 10px; text-align: center; color: #764ba2; font-weight: 600;">{p.get('fg3_pct', 'N/A')}</td>
                                <td style="padding: 12px 10px; text-align: center; font-size: 12px;">{blk_stl_str}</td>
                            </tr>"""
        
        html += """
                        </tbody>
                    </table>"""
    else:
        html += """
                    <p><em>No detailed player stats available tonight.</em></p>"""
    
    html += """
                </div>"""
    
    if top_10_video:
        html += f"""
                
                <div class="section">
                    <div style="margin-top: 0; padding: 20px; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%); border-radius: 8px; text-align: center;">
                        <h2 style="margin: 0 0 15px 0; color: white; font-size: 20px; border: none; padding: 0;">🎬 TOP 10 PLAYS OF THE NIGHT</h2>
                        <a href="{top_10_video['url']}" style="display: inline-block; background: white; color: #ee5a6f; padding: 14px 28px; border-radius: 6px; text-decoration: none; font-weight: 700; font-size: 15px; margin-top: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            ▶️ Watch Highlights on YouTube
                        </a>
                        <p style="margin: 15px 0 0 0; font-size: 13px; color: rgba(255,255,255,0.95); line-height: 1.5;">{top_10_video['title']}</p>
                    </div>
                </div>"""
    
    # --- UPCOMING GAMES (Matchs à venir) section ---
    if upcoming_games:
        html += _render_upcoming_games(upcoming_games)

    if news:
        html += """
                
                <div class="section">
                    <h2>📰 LATEST NEWS AND HEADLINES</h2>
                    <ul>"""
        
        for n in news:
            try:
                title = n.get('title', 'No title')
                link = n.get('link', '#')
                published = n.get('published', 'N/A')
                html += f"""
                        <li>
                            <a href="{link}"><strong>{title}</strong></a>
                            <small>{published}</small>
                        </li>"""
            except Exception as e:
                logger.warning(f"Error rendering news item: {e}")
                continue

        html += """
                    </ul>
                </div>"""
    
    html += """
            </div>
            
            <div class="footer">
                <p>🤖 Automatically generated by NBA Daily Bot</p>
            </div>
        </div>
    </body>
    </html>"""
    
    return html