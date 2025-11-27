
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.main import run
from src.config import Config

logger = logging.getLogger(__name__)
cfg = Config()

def schedule_bot():
    scheduler = BackgroundScheduler()
    
    run_time = cfg.BOT_RUN_TIME if hasattr(cfg, 'BOT_RUN_TIME') else "09:00"
    hour, minute = map(int, run_time.split(":"))
    
    logger.info(f"⏰ Scheduling NBA Daily Bot to run daily at {run_time}")
    
    scheduler.add_job(
        func=lambda: run(dry_run=False),  # Fonction à exécuter (avec envoi d'email)
        trigger=CronTrigger(hour=hour, minute=minute),  # Trigger CRON quotidien
        id='nba_daily_bot',              # ID unique pour identifier la tâche
        name='NBA Daily Newsletter',      # Nom descriptif
        replace_existing=True             # Remplace la tâche si elle existe déjà
    )
    
    scheduler.start()
    logger.info("✅ Scheduler started")
    
    return scheduler

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scheduler = schedule_bot()
    
    try:
        import time
        while True:
            time.sleep(1)  # Attend 1 seconde en boucle
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
