"""
Le mail du récap NBA (design « Courtside + couleurs d'équipes ») : fond sombre, accent orange,
carré des scores en tête, perf de la nuit, une carte par match aux couleurs des deux équipes
(logos, score, vidéo, résumé Trashtalk ou ESPN, meilleurs joueurs), Top 5, Top 10, ce soir, actus.

Tout est en tableaux et en styles en ligne : c'est ce que Gmail, Apple Mail et Outlook affichent
de façon fiable (pas de flexbox, pas de position absolue, pas de JavaScript).
"""
from datetime import datetime, timedelta
import logging
from html import escape

logger = logging.getLogger(__name__)

ACCENT = "#ff7a1a"
BG, CARD, CARD2, LINE, LINE2 = "#0d0f12", "#161a20", "#1b2026", "#23272e", "#2d333c"
TEXT, TEXT2, TEXT3, MUTED = "#eef0f3", "#c4cad2", "#9aa3ae", "#7d8590"
DISPLAY = "'Oswald','Arial Narrow','Helvetica Neue',Arial,sans-serif"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

# Diffuseurs français
BROADCAST_STYLES = {
    'bein sports': ('#5a2d82', 'beIN Sports'), 'bein': ('#5a2d82', 'beIN Sports'),
    'prime video': ('#1a98ff', 'Prime Video'), 'prime': ('#1a98ff', 'Prime Video'), 'amazon prime': ('#1a98ff', 'Prime Video'),
    'league pass': (None, 'League Pass'), 'nba tv': (None, 'NBA TV'), 'canal+': ('#000000', 'Canal+'),
}


def _e(s):
    return escape(str(s if s is not None else ""))


def _luminance(hex_color):
    try:
        h = hex_color.lstrip('#')
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    except Exception:
        return 0.3


def _team(teams, key):
    return (teams or {}).get(key) or {"abbr": str(key)[:3].upper(), "color": "#3a3f47", "alt": "#555", "logo": ""}


def _logo(info, size=26, pad=0, dim=False):
    """Logo ESPN prévu pour fond sombre (une pastille blanche serait inversée en noir par Outlook)."""
    if not info.get("logo"):
        return ""
    return (f'<img src="{_e(info["logo"])}" width="{size}" height="{size}" alt="" '
            f'style="display:inline-block;vertical-align:middle;border:0;width:{size}px;height:{size}px;{"opacity:0.75;" if dim else ""}">')


def _label(text):
    return f'<tr><td style="font-family:{DISPLAY};font-size:13px;letter-spacing:2px;color:{ACCENT};font-weight:600;padding:28px 20px 10px">{text}</td></tr>'


def _stat_line(p):
    parts = [f"{int(p.get('pts', 0))} pts"]
    if p.get('reb'):
        parts.append(f"{int(p['reb'])} reb")
    if p.get('ast'):
        parts.append(f"{int(p['ast'])} ast")
    if p.get('blk', 0) >= 3:
        parts.append(f"{int(p['blk'])} ctr")
    if p.get('stl', 0) >= 3:
        parts.append(f"{int(p['stl'])} int")
    return " · ".join(parts[:3])


def _short(name):
    bits = str(name).split()
    return f"{bits[0][0]}. {' '.join(bits[1:])}" if len(bits) > 1 and len(name) > 16 else name


def _score_grid(organized_games, teams):
    cells = []
    for i, g in enumerate(organized_games):
        rows = ""
        for k, side in enumerate(("away", "home")):
            t = _team(teams, g[side])
            win = g[f"{side}_score"] == max(g["away_score"], g["home_score"])
            col = TEXT if win else MUTED
            weight = "700" if win else "400"
            pad = "padding-top:4px;" if k else ""
            rows += (f'<tr><td width="22" style="{pad}">{_logo(t, 18, dim=not win)}</td><td style="{pad}font-weight:{weight};color:{col}">{_e(t["abbr"])}</td>'
                     f'<td align="right" style="{pad}font-weight:{weight};color:{col}">{g[f"{side}_score"]}</td></tr>')
        cells.append(f'''<td width="33%" valign="top" style="padding:10px;border-right:1px solid {LINE2};border-bottom:1px solid {LINE2}">
          <a href="#m{i}" style="text-decoration:none;color:{TEXT}">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-family:{SANS};font-size:13px">{rows}</table></a></td>''')
    while len(cells) % 3:
        cells.append(f'<td width="33%" style="border-bottom:1px solid {LINE2}">&nbsp;</td>')
    rows = "".join(f"<tr>{''.join(cells[i:i + 3])}</tr>" for i in range(0, len(cells), 3))
    return f'''<tr><td style="padding:0 14px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {LINE2};border-radius:14px;background:#14181e;border-collapse:separate;overflow:hidden">{rows}</table>
    </td></tr>'''


def perf_details(top):
    details = [f"{int(top.get('reb', 0))} reb", f"{int(top.get('ast', 0))} ast"]
    if top.get('stl', 0) >= 3:
        details.append(f"{int(top['stl'])} int")
    if top.get('blk', 0) >= 3:
        details.append(f"{int(top['blk'])} ctr")
    if top.get('fg_pct'):
        details.append(f"{top['fg_pct']:.0f} % au tir")
    return " · ".join(details)


def _perf_card(top, teams, perf_img=None):
    # Version image (jointe au mail, cid:perf) : logo en filigrane, identique partout
    if perf_img:
        alt = f"La perf de la nuit : {top.get('name', '')}, {int(top.get('pts', 0))} points, {perf_details(top)}"
        return f'''<tr><td style="padding:16px 14px 0"><img src="{perf_img}" width="452" alt="{_e(alt)}" style="display:block;width:100%;max-width:452px;height:auto;border:0;border-radius:18px"></td></tr>'''
    t = _team(teams, top.get('team'))
    ink = "#0d0f12" if _luminance(t['color']) > 0.6 else "#ffffff"
    return f'''<tr><td style="padding:16px 14px 0">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{t['color']};border-radius:18px">
        <tr>
          <td style="padding:16px 18px;font-family:{SANS};color:{ink}">
            <div style="font-size:10.5px;font-weight:700;letter-spacing:2px;opacity:0.85">LA PERF DE LA NUIT</div>
            <div style="font-family:{DISPLAY};font-weight:700;font-size:28px;line-height:1.05;margin-top:4px">{_e(top.get('name', '').upper())}</div>
            <div style="font-size:12.5px;opacity:0.9;margin-top:4px">{_e(perf_details(top))}</div>
          </td>
          <td align="right" valign="bottom" style="padding:16px 18px;color:{ink};white-space:nowrap">
            <span style="font-family:{DISPLAY};font-weight:700;font-size:56px;line-height:0.9">{int(top.get('pts', 0))}</span><span style="font-family:{DISPLAY};font-size:15px;font-weight:700"> PTS</span>
          </td>
        </tr>
      </table></td></tr>'''


def _button(url, label, primary=False, light=False, dashed=False):
    if primary:
        style = f"background:{ACCENT};color:#0d0f12;font-weight:700"
    elif light:
        style = f"background:{TEXT};color:#0d0f12;font-weight:700"
    elif dashed:
        style = f"border:1px dashed {LINE2};color:{TEXT3};font-weight:600"
    else:
        style = f"border:1px solid {LINE2};color:{TEXT};font-weight:600"
    return (f'<a href="{_e(url)}" style="display:block;text-align:center;font-family:{SANS};font-size:13px;{style};'
            f'border-radius:10px;padding:11px 0;text-decoration:none">{label}</a>')


def _game_card(i, g, teams, link, video, fallback_video_url, header_img=None):
    w, l = _team(teams, g['winner']), _team(teams, g['loser'])

    def side(key, align):
        t = _team(teams, g[key])
        win = g[f"{key}_score"] == max(g["away_score"], g["home_score"])
        ink = ("#0d0f12" if _luminance(t['color']) > 0.6 else "#ffffff") if win else "#8a929d"
        bg = f"background:{t['color']};padding:14px 14px 12px;" if win else f"background:{CARD2};border-top:4px solid {t['color']};padding:10px 14px 12px;"
        rec = g.get(f"{key}_record")
        name = f'<div style="font-weight:700;font-size:14px">{_e(g[key])}</div>' + (f'<div style="font-size:11px;opacity:0.8">{_e(rec)}</div>' if rec else "")
        logo = _logo(t, 34, dim=not win)
        ident = (f'<table role="presentation" cellpadding="0" cellspacing="0"><tr><td>{logo}</td><td style="padding-left:8px;color:{ink}">{name}</td></tr></table>' if align == "left" else
                 f'<table role="presentation" cellpadding="0" cellspacing="0" align="right"><tr><td align="right" style="padding-right:8px;color:{ink}">{name}</td><td>{logo}</td></tr></table>')
        return (f'<td width="50%" valign="top" align="{align}" style="{bg}color:{ink};font-family:{SANS}">{ident}'
                f'<div style="clear:both;font-family:{DISPLAY};font-weight:700;font-size:46px;line-height:1;padding-top:8px;text-align:{align}">{g[f"{key}_score"]}</div></td>')

    if header_img:  # en-tête dessiné en image, avec les logos en filigrane (intouchable par Outlook)
        alt = f'{g["away"]} {g["away_score"]} - {g["home_score"]} {g["home"]}'
        header = (f'<tr><td colspan="2" style="padding:0;line-height:0;font-size:0">'
                  f'<img src="{_e(header_img)}" width="100%" alt="{_e(alt)}" style="display:block;width:100%;height:auto;border:0"></td></tr>')
    else:
        header = f'<tr>{side("away", "left")}{side("home", "right")}</tr>'

    thumb = ""
    if video:
        caption = "Résumé du match" if video.get('kind') == 'full' else "Les temps forts"
        thumb = f'''<tr><td colspan="2" style="padding:12px 12px 0">
          <a href="{_e(video['url'])}" style="text-decoration:none;color:{TEXT}">
            <img src="{_e(video['thumb'])}" width="100%" alt="{_e(caption)}" style="display:block;width:100%;height:auto;border:0;border-radius:12px 12px 0 0">
            <div style="background:#232831;border-radius:0 0 12px 12px;padding:9px 12px;font-family:{SANS};font-size:12.5px;font-weight:600;color:{TEXT}"><span style="color:{ACCENT}">▶</span>&nbsp; {caption} · YouTube NBA</div>
          </a></td></tr>'''

    if link and link.get('kind') == 'trashtalk':
        b1 = _button(link['url'], "Résumé Trashtalk ↗", primary=True)
    elif link:
        b1 = _button(link['url'], "Résumé ESPN ↗", light=True)
    else:
        b1 = ""
    b2 = _button(video['url'], "▶ Vidéo") if video else _button(fallback_video_url, "Vidéos NBA ↗", dashed=True)
    buttons = f'''<tr><td colspan="2" style="padding:12px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td width="50%" style="padding-right:4px">{b1}</td><td width="50%" style="padding-left:4px">{b2}</td></tr></table></td></tr>'''

    lines = ""
    for p in g.get('winner_top_performers', [])[:2]:
        lines += (f'<tr><td style="padding:4px 0;color:{TEXT}">{_logo(w, 16)}&nbsp; <b>{_e(_short(p["name"]))}</b></td>'
                  f'<td align="right" style="padding:4px 0;color:{TEXT};font-weight:600">{_e(_stat_line(p))}</td></tr>')
    for p in g.get('loser_top_performers', [])[:1]:
        lines += (f'<tr><td style="padding:4px 0;color:{MUTED};font-size:12.5px">{_logo(l, 16, dim=True)}&nbsp; {_e(_short(p["name"]))}</td>'
                  f'<td align="right" style="padding:4px 0;color:{MUTED};font-size:12.5px">{_e(_stat_line(p))}</td></tr>')
    players = f'''<tr><td colspan="2" style="border-top:1px solid {LINE};padding:10px 16px 12px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-family:{SANS};font-size:13px">{lines}</table></td></tr>''' if lines else ""

    return f'''<tr><td style="padding:0 14px 16px"><a name="m{i}" id="m{i}"></a>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CARD};border-radius:18px;overflow:hidden;border-collapse:separate">
        {header}{thumb}{buttons}{players}
      </table></td></tr>'''


def _top5(top_performers, teams):
    seen, ranked, rows = set(), [], ""
    for p in sorted(top_performers, key=lambda x: x.get('pts', 0), reverse=True):
        if p.get('name') in seen:
            continue
        seen.add(p.get('name'))
        ranked.append(p)
        if len(ranked) == 5:
            break
    for i, p in enumerate(ranked, 1):
        t = _team(teams, p.get('team'))
        border = "border-bottom:1px solid #1c2027;" if i < len(ranked) else ""
        rows += f'''<tr>
          <td width="24" style="{border}padding:9px 0;font-family:{DISPLAY};font-size:20px;color:{ACCENT if i == 1 else TEXT3}">{i}</td>
          <td width="30" style="{border}padding:9px 0">{_logo(t, 22)}</td>
          <td style="{border}padding:9px 0 9px 6px;font-weight:700;color:{TEXT}">{_e(p.get('name'))}</td>
          <td align="right" width="40" style="{border}padding:9px 0;font-weight:700;color:{TEXT}">{int(p.get('pts', 0))}</td>
          <td align="right" width="34" style="{border}padding:9px 0;color:{TEXT2}">{int(p.get('reb', 0))}</td>
          <td align="right" width="34" style="{border}padding:9px 0;color:{TEXT2}">{int(p.get('ast', 0))}</td></tr>'''
    th = f"font-size:10.5px;letter-spacing:1px;color:{MUTED}"
    head = (f'<tr><td></td><td></td><td style="padding:0 0 6px 6px;{th}">JOUEUR</td>'
            f'<td align="right" style="{th}">PTS</td><td align="right" style="{th}">REB</td><td align="right" style="{th}">AST</td></tr>')
    return f'''{_label("LE TOP 5 DE LA NUIT")}<tr><td style="padding:0 20px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-family:{SANS};font-size:14px">{head}{rows}</table></td></tr>'''


def _video_block(video, title, sub):
    return f'''<tr><td style="padding:26px 14px 0">
      <a href="{_e(video['url'])}" style="text-decoration:none;color:{TEXT}">
        <img src="{_e(video.get('thumbnail') or video.get('thumb') or '')}" width="100%" alt="" style="display:block;width:100%;height:auto;border:0;border-radius:18px 18px 0 0">
        <div style="background:#232831;border-radius:0 0 18px 18px;padding:12px 16px">
          <div style="font-family:{DISPLAY};font-size:20px;font-weight:700;color:{TEXT}"><span style="color:{ACCENT}">▶</span>&nbsp; {title}</div>
          <div style="font-family:{SANS};font-size:12px;color:{TEXT2};margin-top:2px">{sub}</div>
        </div></a></td></tr>'''


def _upcoming(upcoming_games, teams):
    rows = ""
    for g in upcoming_games:
        if g.game_status == 3:
            continue
        h, a = _team(teams, g.home_team), _team(teams, g.away_team)
        badges = ""
        for b in g.broadcasters:
            color, label = BROADCAST_STYLES.get(b.lower().strip(), (None, b))
            badges += (f'<span style="display:inline-block;font-size:11px;font-weight:700;color:#ffffff;background:{color};border-radius:6px;padding:3px 7px;margin-left:4px">{_e(label)}</span>'
                       if color else f'<span style="display:inline-block;font-size:11px;font-weight:700;color:{TEXT3};border:1px solid {LINE2};border-radius:6px;padding:2px 7px;margin-left:4px">{_e(label)}</span>')
        rows += f'''<tr><td style="padding:0 14px 8px">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CARD};border-radius:12px;font-family:{SANS};font-size:14px"><tr>
            <td width="54" style="padding:10px 0 10px 12px;font-family:{DISPLAY};font-size:18px;color:{TEXT}">{_e(g.game_time_fr.replace('h', ':'))}</td>
            <td style="padding:10px 0;color:{TEXT};white-space:nowrap"><img src="{_e(a['logo'])}" width="20" height="20" alt="" style="vertical-align:middle;border:0"> <b>{_e(a['abbr'])}</b> <span style="color:#6b737e">@</span> <img src="{_e(h['logo'])}" width="20" height="20" alt="" style="vertical-align:middle;border:0"> <b>{_e(h['abbr'])}</b></td>
            <td align="right" style="padding:10px 12px 10px 0">{badges}</td></tr></table></td></tr>'''
    return f'{_label("CE SOIR")}{rows}' if rows else ""


def _news(news):
    items = ""
    shown = news[:6]
    for k, a in enumerate(shown):
        border = "border-bottom:1px solid #1c2027;" if k < len(shown) - 1 else ""
        src = str(a.get('source', '')).upper()
        items += f'''<tr><td style="{border}padding:12px 0;font-family:{SANS}">
          <a href="{_e(a.get('link', '#'))}" style="text-decoration:none;color:{TEXT}">
            <div style="font-size:10.5px;font-weight:700;letter-spacing:0.5px;color:{ACCENT if 'TRASH' in src else TEXT3}">{_e(src)}</div>
            <div style="font-size:14.5px;font-weight:600;line-height:1.35;margin-top:3px">{_e(a.get('title'))}</div></a></td></tr>'''
    return f'{_label("LES ACTUS")}<tr><td style="padding:0 20px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{items}</table></td></tr>' if items else ""


def _outlook_lock(html):
    """
    Outlook (Outlook.com, nouvel Outlook) repeint les couleurs en mode sombre : un fond sombre devient gris,
    le blanc devient noir. Il marque alors les éléments repeints (data-ogsb / data-ogsc) : chaque couleur
    du mail reçoit une classe, et une règle qui la rétablit dans ce cas-là.
    """
    import re
    bgs, fgs = set(), set()

    def tag(m):
        attrs = m.group(0)
        style = re.search(r'style="([^"]*)"', attrs)
        if not style:
            return attrs
        st = style.group(1)
        classes = []
        b = re.search(r'background(?:-color)?:\s*(#[0-9a-fA-F]{6})', st)
        if b and "background-image" not in st:
            # Outlook en mode sombre repeint les couleurs de fond, pas les images : la même couleur en « image »
            attrs = attrs.replace(st, st.rstrip(";") + f";background-image:linear-gradient({b.group(1)},{b.group(1)})", 1)
        c = re.search(r'(?<![-\w])color:\s*(#[0-9a-fA-F]{6})', st)
        if b:
            bgs.add(b.group(1).lower()); classes.append(f"ob{b.group(1)[1:].lower()}")
        if c:
            fgs.add(c.group(1).lower()); classes.append(f"oc{c.group(1)[1:].lower()}")
        if not classes:
            return attrs
        return attrs.replace('style="', f'class="{" ".join(classes)}" style="', 1)

    html = re.sub(r'<(td|table|div|span|a|body|p)\b[^>]*>', tag, html)
    css = ":root{color-scheme:light dark;supported-color-schemes:light dark}"
    css += "".join(f"[data-ogsb] .ob{h[1:]}{{background-color:{h} !important}}" for h in sorted(bgs))
    css += "".join(f"[data-ogsc] .oc{h[1:]}{{color:{h} !important}}" for h in sorted(fgs))
    # Apple Mail et iOS en mode sombre : mêmes couleurs que le design
    css += "@media (prefers-color-scheme: dark){" + "".join(f".ob{h[1:]}{{background-color:{h} !important}}" for h in sorted(bgs))
    css += "".join(f".oc{h[1:]}{{color:{h} !important}}" for h in sorted(fgs)) + "}"
    return html.replace("</head>", f"<style>{css}</style></head>", 1)


def render_email(summary_text, news, top_performers=None, games=None, organized_games=None, top_10_video=None, upcoming_games=None,
                 teams=None, links=None, videos=None, nightly_video=None, tt_nightly=None, perf_img=None, header_imgs=None):
    summary_text = summary_text if summary_text and summary_text.strip() else "Pas de récap aujourd'hui."
    news, top_performers, organized_games, upcoming_games = news or [], top_performers or [], organized_games or [], upcoming_games or []
    teams, links, videos = teams or {}, links or {}, videos or {}

    now = datetime.now()
    prev = now - timedelta(days=1)
    night = f"Nuit du {prev.day} au {now.day} {MONTHS[now.month - 1]}"
    count = len(organized_games)
    sub = f"{night} · {count} match{'s' if count > 1 else ''}" if count else night
    fallback_video = nightly_video['url'] if nightly_video else "https://www.youtube.com/@NBA/videos"

    summary_html = "".join(f'<p style="margin:0 0 10px">{_e(p)}</p>' for p in summary_text.strip().split("\n") if p.strip())

    body = f'''<tr><td style="padding:26px 20px 18px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
        <td style="font-family:{DISPLAY};font-weight:700;font-size:34px;line-height:1;color:{TEXT};letter-spacing:0.5px">LE RÉCAP <span style="color:{ACCENT}">NBA</span>
          <div style="font-family:{SANS};font-weight:400;font-size:13px;color:{TEXT3};letter-spacing:0;margin-top:6px">{_e(sub)}</div></td>
      </tr></table></td></tr>'''

    if organized_games:
        body += _score_grid(organized_games, teams)
        best = max(top_performers, key=lambda p: p.get('pts', 0)) if top_performers else None
        if best:
            body += _perf_card(best, teams, perf_img)

    body += f'''{_label("LA NUIT EN BREF")}<tr><td style="padding:0 20px;font-family:{SANS};font-size:15px;line-height:1.6;color:#d9dde3">{summary_html}</td></tr>'''

    if organized_games:
        body += _label("LES MATCHS")
        for i, g in enumerate(organized_games):
            body += _game_card(i, g, teams, links.get(g['id']), videos.get(g['id']), fallback_video, (header_imgs or {}).get(g['id']))
        if tt_nightly:
            body += f'''<tr><td style="padding:0 14px">
              <a href="{_e(tt_nightly['link'])}" style="display:block;text-decoration:none;color:{TEXT};border:1px solid {LINE2};border-radius:16px;padding:14px 16px;font-family:{SANS}">
                <div style="font-size:10.5px;font-weight:700;letter-spacing:1.5px;color:{ACCENT}">TRASHTALK · LE RÉSUMÉ DE LA NUIT</div>
                <div style="font-size:15px;font-weight:700;line-height:1.35;margin-top:5px">{_e(tt_nightly['title'])}</div></a></td></tr>'''
        if nightly_video:
            body += _video_block(nightly_video, "LE RÉCAP VIDÉO DE LA NUIT", "Tous les matchs en quelques minutes · YouTube NBA")

    if top_performers:
        body += _top5(top_performers, teams)
    if top_10_video:
        body += _video_block(top_10_video, "TOP 10 DE LA NUIT", "Les plus belles actions · YouTube NBA")
    if upcoming_games:
        body += _upcoming(upcoming_games, teams)
    body += _news(news)
    body += f'''<tr><td style="padding:24px 20px 30px"><div style="border-top:1px solid {LINE};padding-top:18px;font-family:{SANS};font-size:11.5px;color:{MUTED};line-height:1.6">
      Scores ESPN · vidéos chaîne NBA · actus Trashtalk et The Athletic · récap rédigé par Claude</div></td></tr>'''

    return _outlook_lock(f'''<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark"><meta name="supported-color-schemes" content="light dark">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&display=swap" rel="stylesheet">
<title>Le récap NBA</title></head>
<body style="margin:0;padding:0;background:{BG}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG}"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:{BG};color:{TEXT}">
{body}
</table></td></tr></table></body></html>''')
