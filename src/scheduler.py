"""
Planificateur pour exécuter le bot NBA Daily à des heures programmées.

Ce module utilise APScheduler pour exécuter automatiquement la newsletter
chaque jour à une heure configurée (par défaut 09:00).

Utilisation:
    - En production: lance le scheduler en arrière-plan (background)
    - GitHub Actions: n'utilise PAS ce scheduler (utilise CRON à la place)
    - Tests locaux: exécute ce fichier directement pour tester le scheduling
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.main import run
from src.config import Config

logger = logging.getLogger(__name__)
cfg = Config()


def schedule_bot():
    """
    Démarre le planificateur pour exécuter le bot quotidiennement.
    
    Configuration:
        - Heure d'exécution: définie dans .env via BOT_RUN_TIME (format HH:MM)
        - Par défaut: 09:00 (9h du matin)
        - Fuseau horaire: utilise le fuseau système
    
    Returns:
        BackgroundScheduler: Instance du scheduler (peut être arrêtée avec .shutdown())
    
    Fonctionnement:
        1. Parse BOT_RUN_TIME depuis la config (ex: "09:00" → heure=9, minute=0)
        2. Crée un CronTrigger pour exécuter chaque jour à cette heure
        3. Lance le scheduler en arrière-plan (ne bloque pas le programme)
    
    Exemple:
        >>> scheduler = schedule_bot()
        >>> # Le bot tournera chaque jour à 09:00
        >>> # Pour arrêter: scheduler.shutdown()
    
    Note:
        GitHub Actions n'utilise PAS ce scheduler mais son propre système CRON.
        Ce scheduler est utile pour:
        - Déploiement sur serveur (VPS, Raspberry Pi, etc.)
        - Tests locaux avec exécution automatique
    """
    # === ÉTAPE 1: Initialiser le scheduler en mode background ===
    # BackgroundScheduler = tourne en arrière-plan sans bloquer le thread principal
    scheduler = BackgroundScheduler()
    
    # === ÉTAPE 2: Récupérer l'heure configurée ===
    # Format attendu: "HH:MM" (24 heures), exemple: "09:00", "14:30", "23:45"
    run_time = cfg.BOT_RUN_TIME if hasattr(cfg, 'BOT_RUN_TIME') else "09:00"
    hour, minute = map(int, run_time.split(":"))
    
    logger.info(f"⏰ Scheduling NBA Daily Bot to run daily at {run_time}")
    
    # === ÉTAPE 3: Ajouter la tâche planifiée ===
    scheduler.add_job(
        func=lambda: run(dry_run=False),  # Fonction à exécuter (avec envoi d'email)
        trigger=CronTrigger(hour=hour, minute=minute),  # Trigger CRON quotidien
        id='nba_daily_bot',              # ID unique pour identifier la tâche
        name='NBA Daily Newsletter',      # Nom descriptif
        replace_existing=True             # Remplace la tâche si elle existe déjà
    )
    
    # === ÉTAPE 4: Démarrer le scheduler ===
    scheduler.start()
    logger.info("✅ Scheduler started")
    
    return scheduler


if __name__ == "__main__":
    """
    Point d'entrée pour tester le scheduler en local.
    
    Exécution:
        python -m src.scheduler
    
    Comportement:
        1. Configure le logging
        2. Démarre le scheduler
        3. Reste en boucle infinie (attend Ctrl+C)
        4. Arrête proprement le scheduler à l'interruption
    """
    # === Configuration du logging pour les tests ===
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # === Démarrage du scheduler ===
    scheduler = schedule_bot()
    
    try:
        # === Boucle infinie pour garder le programme actif ===
        # Le scheduler tourne en arrière-plan, on attend juste
        import time
        while True:
            time.sleep(1)  # Attend 1 seconde en boucle
    except KeyboardInterrupt:
        # === Arrêt propre avec Ctrl+C ===
        scheduler.shutdown()
        logger.info("Scheduler stopped")
