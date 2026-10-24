"""
La carte « perf de la nuit » dessinée en image (PNG, jointe au mail) : couleur de l'équipe, grand logo
en filigrane, nom, stats et points. Une image s'affiche partout pareil, y compris dans Outlook en mode
sombre (qui repeint les fonds HTML mais ne touche pas aux images) et sans dépendre des fonds superposés.
"""
import io
import logging
from pathlib import Path

from functools import lru_cache

import requests
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

FONTS = Path(__file__).resolve().parents[2] / "assets" / "fonts"
W, H, R = 904, 284, 36          # dessinée en 2x pour les écrans Retina (affichée sur 452 px)


def _font(name, size, weight):
    f = ImageFont.truetype(str(FONTS / name), size)
    try:
        f.set_variation_by_axes([weight] if name.startswith("Oswald") else [14, weight])
    except Exception:
        pass
    return f


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _fit(draw, text, name, size, weight, max_w):
    """Réduit la taille jusqu'à ce que le texte tienne (noms longs)."""
    while size > 28:
        f = _font(name, size, weight)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return _font(name, size, weight)


@lru_cache(maxsize=64)
def _logo_bytes(abbr):
    r = requests.get(f"https://a.espncdn.com/i/teamlogos/nba/500-dark/{abbr.lower()}.png", timeout=15)
    r.raise_for_status()
    return r.content


def _logo(abbr, size, opacity=1.0):
    """Logo ESPN (prévu pour fond sombre), redimensionné, avec une opacité donnée."""
    logo = Image.open(io.BytesIO(_logo_bytes(abbr))).convert("RGBA").resize((size, size), Image.LANCZOS)
    if opacity < 1:
        logo.putalpha(logo.getchannel("A").point(lambda a: int(a * opacity)))
    return logo


def _png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def match_header_png(away, home):
    """
    Le haut d'une carte de match : extérieur à gauche, domicile à droite. Chaque moitié porte un grand logo
    en filigrane, le petit logo, le nom, le bilan et le score. Le vainqueur est sur sa couleur, le perdant en
    sombre avec un filet de sa couleur. away / home : {name, abbr, color, record, score}.
    """
    try:
        HW, HH = 452, 300  # chaque moitié (2x)
        img = Image.new("RGBA", (HW * 2, HH), (22, 26, 32, 255))
        win_side = "away" if away["score"] > home["score"] else "home"
        for k, (side, t) in enumerate((("away", away), ("home", home))):
            x0 = k * HW
            color = _rgb(t["color"])
            win = side == win_side
            half = Image.new("RGBA", (HW, HH), color + (255,) if win else (27, 32, 38, 255))
            if not win:
                ImageDraw.Draw(half).rectangle((0, 0, HW, 8), fill=color + (255,))
            lum = (0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]) / 255
            ink = ((13, 15, 18) if lum > 0.6 else (255, 255, 255)) if win else (138, 146, 157)
            # Grand logo en filigrane, du côté extérieur de la carte
            try:
                wm = _logo(t["abbr"], 340, 0.2 if win else 0.07)
                half.alpha_composite(wm, (HW - 230, 30) if k == 0 else (-110, 30))
                small = _logo(t["abbr"], 68, 1.0 if win else 0.75)
            except Exception:
                small = None
            d = ImageDraw.Draw(half)
            name_f, rec_f, score_f = _font("Inter.ttf", 28, 700), _font("Inter.ttf", 22, 500), _font("Oswald.ttf", 112, 700)
            name, rec, score = t["name"], t.get("record") or "", str(t["score"])
            if k == 0:  # à gauche : logo puis texte
                if small:
                    half.alpha_composite(small, (28, 30))
                d.text((112, 34), name, font=name_f, fill=ink)
                if rec:
                    d.text((112, 70), rec, font=rec_f, fill=ink + (200,))
                d.text((28, 116), score, font=score_f, fill=ink)
            else:  # à droite : texte puis logo, aligné à droite
                if small:
                    half.alpha_composite(small, (HW - 28 - 68, 30))
                nw = d.textlength(name, font=name_f)
                d.text((HW - 112 - nw, 34), name, font=name_f, fill=ink)
                if rec:
                    d.text((HW - 112 - d.textlength(rec, font=rec_f), 70), rec, font=rec_f, fill=ink + (200,))
                d.text((HW - 28 - d.textlength(score, font=score_f), 116), score, font=score_f, fill=ink)
            img.alpha_composite(half, (x0, 0))
        # Coins arrondis en haut seulement (la carte continue en dessous)
        mask = Image.new("L", img.size, 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle((0, 0, img.width - 1, img.height + 40), R, fill=255)
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.paste(img, (0, 0), mask)
        return _png(out)
    except Exception as e:
        logger.warning(f"⚠️ En-tête de match non dessiné : {e}")
        return None


def perf_card_png(name, details, pts, color, abbr):
    """PNG de la carte, ou None si quelque chose manque (le mail garde alors la version HTML)."""
    try:
        base = _rgb(color)
        lum = (0.2126 * base[0] + 0.7152 * base[1] + 0.0722 * base[2]) / 255
        ink = (13, 15, 18) if lum > 0.6 else (255, 255, 255)

        img = Image.new("RGBA", (W, H), base + (255,))

        # Grand logo, estompé, dans le coin droit (logo ESPN prévu pour fond sombre)
        try:
            r = requests.get(f"https://a.espncdn.com/i/teamlogos/nba/500-dark/{abbr.lower()}.png", timeout=15)
            r.raise_for_status()
            logo = Image.open(io.BytesIO(r.content)).convert("RGBA").resize((400, 400), Image.LANCZOS)
            alpha = logo.getchannel("A").point(lambda a: int(a * 0.2))
            logo.putalpha(alpha)
            img.alpha_composite(logo, (W - 330, -70))
        except Exception as e:
            logger.warning(f"⚠️ Logo du filigrane indisponible : {e}")

        d = ImageDraw.Draw(img)
        d.text((44, 46), "LA PERF DE LA NUIT", font=_font("Inter.ttf", 22, 700), fill=ink + (215,), spacing=0)
        name_font = _fit(d, name.upper(), "Oswald.ttf", 68, 700, 560)
        d.text((44, 84), name.upper(), font=name_font, fill=ink)
        d.text((44, 186), details, font=_font("Inter.ttf", 26, 500), fill=ink + (230,))

        # Les points, alignés à droite
        big, small = _font("Oswald.ttf", 150, 700), _font("Oswald.ttf", 34, 700)
        pts_txt = str(pts)
        pw, sw = d.textlength(pts_txt, font=big), d.textlength("PTS", font=small)
        x = W - 44 - sw - 8 - pw
        d.text((x, 54), pts_txt, font=big, fill=ink)
        d.text((W - 44 - sw, 192), "PTS", font=small, fill=ink)

        # Coins arrondis
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, W - 1, H - 1), R, fill=255)
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.paste(img, (0, 0), mask)

        buf = io.BytesIO()
        out.save(buf, "PNG", optimize=True)
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"⚠️ Carte « perf de la nuit » non dessinée : {e}")
        return None
