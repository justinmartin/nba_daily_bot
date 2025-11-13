# 🔐 GitHub Actions Setup Guide

Maintenant que le code est sur GitHub, configure les **GitHub Secrets** pour que le bot fonctionne automatiquement.

## 📋 Ajouter les Secrets GitHub

1. **Va sur ton repo GitHub** : https://github.com/justinmartin/nba_daily_bot
2. **Clique sur Settings** → Secrets and variables → Actions
3. **Clique sur "New repository secret"** et ajoute chaque secret ci-dessous :

### Secrets à ajouter :

| Secret Name | Valeur | Description |
|-------------|--------|-------------|
| `MAIL_SMTP_HOST` | `smtp.gmail.com` | Gmail SMTP server |
| `MAIL_SMTP_PORT` | `587` | SMTP port |
| `MAIL_SMTP_USER` | `your-email@gmail.com` | Your Gmail address |
| `MAIL_SMTP_PASSWORD` | `your-app-password` | Gmail app password (Settings → App passwords) |
| `NEWS_RECIPIENT` | `email1@example.com,email2@example.com` | Newsletter recipients (comma-separated) |
| `BALLDONTLIE_API_KEY` | `your-api-key` | Get from https://balldontlie.io/ |
| `HF_API_TOKEN` | `hf_xxxxxxxxxxxxx` | Get from https://huggingface.co/settings/tokens |
| `MODEL_ID` | `mistralai/Mistral-7B-Instruct-v0.2:featherless-ai` | LLM model (don't change) |
| `MAX_TOKENS` | `800` | Max tokens for generation |
| `TIMEZONE` | `Europe/Paris` | Timezone for scheduling |
| `BOT_RUN_TIME` | `07:30` | Daily run time (24h format) |
| `CACHE_PATH` | `./data/cache.db` | Cache path (don't change) |

## ✅ Vérifier que tout fonctionne

### Tester manuellement
1. Va sur **Actions** tab du repo
2. Clique sur **"🏀 NBA Daily Newsletter"** workflow
3. Clique sur **"Run workflow"** → **"Run workflow"**
4. Attends ~5 min et vérifie les logs

### Attendre l'exécution automatique
- Le bot s'exécutera automatiquement **chaque jour à 7:30 AM UTC**
- Pour Europe/Paris : **8:30 AM** (hiver) ou **9:30 AM** (été)
- Les emails seront envoyés à tes destinataires configurés

### Monitorer l'exécution
- Va sur l'onglet **Actions**
- Tu verras l'historique de toutes les exécutions
- Clique sur une exécution pour voir les logs détaillés
- Les artifacts (newsletters générées) sont disponibles en download

## 🔑 Comment créer les secrets correctement

**Pour chaque secret :**
1. Clique **"New repository secret"**
2. Remplis **Name** (ex: `MAIL_SMTP_HOST`)
3. Colle la valeur dans **Secret**
4. Clique **"Add secret"**

⚠️ **Important :**
- Ne mets PAS les secrets directement dans le code
- Ne commit PAS le `.env` (c'est dans `.gitignore`)
- Les secrets sont masqués dans les logs GitHub

## 📊 Exemple d'exécution réussie

```
✅ Checkout repository
✅ Setup Python 3.11
✅ Install dependencies
✅ Generate and send newsletter
✅ Upload newsletter output
```

Si tout est vert ✅, le bot fonctionne correctement !

## 🆘 Troubleshooting

### L'action ne s'exécute pas
- Vérifie que les secrets sont configurés
- Va dans **Actions** et vérifies qu'il n'y a pas d'erreurs

### Erreur SMTP
- Vérifie que `MAIL_SMTP_PASSWORD` est correcte
- Pour Gmail : utilise un **app password**, pas ton mot de passe normal

### Erreur API
- Vérifie que les tokens HF et BallDontLie sont valides
- Teste les APIs manuellement si doute

### Pas d'email reçu
- Vérifie `NEWS_RECIPIENT` (doit être correctement formaté)
- Cherche dans le dossier spam

---

**C'est fait ! Ton bot NBA tournera maintenant automatiquement chaque matin sur GitHub ! 🚀**
