"""
Scheduler for running NBA Daily Bot at scheduled times.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.main import run
from src.config import Config

logger = logging.getLogger(__name__)
cfg = Config()

def schedule_bot():
    """Start the scheduler to run the bot daily."""
    scheduler = BackgroundScheduler()
    
    # Schedule bot to run daily at 9 AM (configurable via env var)
    # Format: HH:MM (24-hour format)
    run_time = cfg.BOT_RUN_TIME if hasattr(cfg, 'BOT_RUN_TIME') else "09:00"
    hour, minute = map(int, run_time.split(":"))
    
    logger.info(f"⏰ Scheduling NBA Daily Bot to run daily at {run_time}")
    
    scheduler.add_job(
        func=lambda: run(dry_run=False),
        trigger=CronTrigger(hour=hour, minute=minute),
        id='nba_daily_bot',
        name='NBA Daily Newsletter',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Scheduler started")
    
    return scheduler

if __name__ == "__main__":
    # Test the scheduler
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scheduler = schedule_bot()
    
    try:
        # Keep the scheduler running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
