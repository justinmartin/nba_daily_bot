from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def render_email(summary_text, news, top_performers=None, games=None, organized_games=None):
    """Render newsletter HTML email."""
    
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
    
    # Add games section
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
            
            # Add top performers for winner
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
            
            # Add best performer for loser
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
        # Fallback to old format if organized_games not available
        html += """
                <div class="section">
                    <h2>📊 GAME RESULTS</h2>
                    <div class="scores-list">"""
        
        for game in games:
            # Determine winner and loser
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
    
    # Add top performers section (top 5 overall)
    html += """
                <div class="section">
                    <h2>👑 TOP 5 PERFORMERS OF THE NIGHT</h2>"""
    
    if top_performers:
        # Get top 5 by points
        sorted_performers = sorted(top_performers, key=lambda x: x.get('pts', 0), reverse=True)[:5]
        
        html += """
                    <table>
                        <thead>
                            <tr>
                                <th>Player</th>
                                <th>Team</th>
                                <th>PTS</th>
                                <th>REB</th>
                                <th>AST</th>
                                <th>FG%</th>
                                <th>3P%</th>
                                <th>+/-</th>
                                <th>BLK/STL</th>
                            </tr>
                        </thead>
                        <tbody>"""
        
        for p in sorted_performers:
            blk_stl = []
            if "blk" in p:
                blk_stl.append(f"{p['blk']} BLK")
            if "stl" in p:
                blk_stl.append(f"{p['stl']} STL")
            blk_stl_str = ", ".join(blk_stl) if blk_stl else "-"
            
            html += f"""
                            <tr>
                                <td>{p.get('name', 'Unknown')}</td>
                                <td>{p.get('team', 'N/A')}</td>
                                <td>{p.get('pts', 0)}</td>
                                <td>{p.get('reb', 0)}</td>
                                <td>{p.get('ast', 0)}</td>
                                <td>{p.get('fg_pct', 'N/A')}</td>
                                <td>{p.get('fg3_pct', 'N/A')}</td>
                                <td>{p.get('+/-', '-')}</td>
                                <td>{blk_stl_str}</td>
                            </tr>"""
        
        html += """
                        </tbody>
                    </table>"""
    else:
        html += """
                    <p><em>No detailed player stats available tonight.</em></p>"""
    
    html += """
                </div>"""
    
    # Add news section
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
    </html>
    """

    return html
