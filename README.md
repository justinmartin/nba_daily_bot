# 🏀 NBA Daily Bot

Le récap NBA de la nuit, en français, dans ta boîte mail chaque matin vers 7 h 45 (heure de Paris).

## Ce qu'il y a dans le mail

- **La nuit en bref** : un résumé rédigé par Claude, en français, façon Trashtalk, à partir des seuls résultats et actus du jour (aucun joueur ni chiffre inventé).
- **Le tableau des scores** en haut du mail : chaque score renvoie à la carte du match.
- **La perf de la nuit** : le meilleur marqueur, sur une carte aux couleurs de son équipe.
- **Une carte par match** :
  - aux couleurs du vainqueur, avec les logos en filigrane, dans l'ordre extérieur / domicile ;
  - le bouton **Résumé Trashtalk** si l'article est paru, sinon **Résumé ESPN** ;
  - la **vidéo** officielle de la NBA sur YouTube (résumé complet, sinon un extrait), avec sa miniature ;
  - les deux meilleurs joueurs du vainqueur et le meilleur du perdant.
- **Le Top 5 de la nuit** et le lien vers le **Top 10 officiel** sur YouTube.
- **Ce soir** : le programme de la nuit suivante avec les diffuseurs français.
- **Les actus** : Trashtalk et le flux NBA de The Athletic.

Si l'IA ne répond pas, le mail part quand même, avec un court résumé de repli.

### Le rendu

- Design sombre « courtside », pensé pour le téléphone (452 px de large), en tableaux et styles en ligne pour les messageries.
- La perf de la nuit et le haut de chaque carte de match sont **dessinés en image** (`src/send/perf_card.py`, Pillow, polices Oswald et Inter dans `assets/fonts`). Ils sont joints au mail (images `cid:`), donc s'affichent pareil partout. Si une image ne peut pas être dessinée, le mail reprend la version HTML.
- **Outlook en mode sombre** repeint les fonds HTML en gris, quoi que contienne le mail ; seules les images y échappent. Pour voir le vrai fond, il faut afficher le message en clair dans Outlook (icône soleil du message, ou réglage d'apparence « fond sombre pour les messages » désactivé).

## Comment ça tourne

Tout passe par GitHub Actions (`.github/workflows/nba-daily.yml`) :

- Les tâches planifiées de GitHub partent avec **des heures de retard le matin** (4 à 6 h constatées), mais à peu près à l'heure le soir. Le workflow se déclenche donc toutes les heures en soirée (`23 19-23`, UTC). Le premier run **attend sur place** (5 h 40 au plus, un run GitHub étant limité à 6 h), puis **se relance lui-même** : un « relais » lancé par l'API démarre tout de suite, contrairement à une tâche planifiée. La chaîne continue jusqu'à **7 h 40 à Paris**, puis le récap est préparé et envoyé.
- Les déclenchements du matin (`23 0-6`) servent de filet de sécurité : si rien n'est parti à 7 h 40, le premier qui démarre envoie tout de suite.
- Un seul run à la fois (`concurrency`). Une marque « déjà envoyé » (`actions/cache`, une clé par jour) arrête les doublons en quelques secondes.
- L'heure de Paris est calculée à chaque run, ce qui gère tout seul le passage à l'heure d'été ou d'hiver.
- Un lancement à la main (Actions → NBA Daily Newsletter → Run workflow, case « relais » décochée) envoie le mail **tout de suite**.
- En cas d'échec, un mail d'alerte part aux destinataires (`.github/scripts/notify_failure.py`).
- Un job `keepalive` empêche GitHub de désactiver le workflow après 60 jours sans commit.

## Rédaction du résumé

Ordre d'essai (`src/model/hf_client.py`) :

1. **Claude, via l'abonnement** : Claude Code en ligne de commande (`claude -p`), avec le modèle `CLAUDE_MODEL` (par défaut `claude-sonnet-5-5`). L'accès passe par le secret `CLAUDE_CODE_OAUTH_TOKEN`, un jeton créé avec `claude setup-token`, **valable 1 an** (créé le 21/10/2026, à renouveler avant le 21/10/2027).
2. **Hugging Face** en secours (`MODEL_ID` puis `MODEL_FALLBACKS`). Il ne sert que si le compte a des crédits.
3. Sinon, le **résumé de repli** en français.

## Sources

| Données | Source |
|---|---|
| Scores, bilans, joueurs | API publique d'ESPN (`site.api.espn.com`) |
| Programme et diffuseurs FR | nba.com/games |
| Top 10 et vidéos des matchs | chaîne YouTube officielle de la NBA (page « Vidéos » et flux RSS) |
| Logos et couleurs des équipes | API d'ESPN |
| Résumés des matchs | Trashtalk (RSS), sinon page « recap » d'ESPN |
| Actus | Trashtalk (RSS) et The Athletic, flux NBA |

## Secrets GitHub

| Secret | Rôle |
|---|---|
| `MAIL_SMTP_HOST`, `MAIL_SMTP_PORT`, `MAIL_SMTP_USER`, `MAIL_SMTP_PASSWORD` | Envoi Gmail (mot de passe d'application, pas le mot de passe du compte) |
| `NEWS_RECIPIENT` | Destinataires, séparés par des virgules |
| `CLAUDE_CODE_OAUTH_TOKEN` | Jeton `claude setup-token` (abonnement Claude) |
| `HF_API_TOKEN`, `USE_HF_INF_API` | Secours Hugging Face (facultatif) |
| `MAX_TOKENS`, `TIMEZONE`, `BOT_RUN_TIME`, `CACHE_PATH`, `BALLDONTLIE_API_KEY` | Réglages facultatifs |

## En local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # puis remplir
python run.py test              # génère le mail dans out/ sans l'envoyer
python run.py once              # génère et envoie
python scripts/test_email.py    # vérifie seulement l'envoi SMTP
```

Pour la rédaction par Claude en local, il faut Claude Code installé et connecté (`claude` dans le terminal).

## Organisation du code

```
src/
├── fetch/      scores.py, players.py (ESPN) · schedule.py (programme + diffuseurs) · news.py · youtube.py
│               extras.py : logos, résumés Trashtalk / ESPN, vidéos des matchs
├── model/      hf_client.py : Claude Code, puis Hugging Face
├── send/       render.py (mail HTML) · perf_card.py (images) · mailer.py (SMTP, images jointes)
├── config.py   variables d'environnement
└── main.py     orchestration et prompt
assets/fonts/   Oswald et Inter (licence OFL)
run.py          point d'entrée (test | once | schedule)
scripts/        test_email.py
```
