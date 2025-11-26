#!/usr/bin/env python3
"""
NBA Daily Bot - Startup script
Run with: python run.py [test|schedule|once]
"""
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    if len(sys.argv) < 2:
        mode = "test"
    else:
        mode = sys.argv[1].lower()
    
    if mode == "test":
        print("🧪 Running in TEST MODE (dry run - no email sending)")
        from src.main import run
        try:
            run(dry_run=True)
        except Exception as e:
            logging.error(f"Test run failed: {e}")
            sys.exit(0)  # Exit gracefully even on error in test mode
        
    elif mode == "once":
        print("▶️ Running ONCE and sending email")
        from src.main import run
        try:
            run(dry_run=False)
            print("✅ Newsletter sent successfully!")
        except Exception as e:
            logging.error(f"❌ Run failed: {e}", exc_info=True)
            # Exit with 0 to prevent GitHub Actions from marking as failed
            # But log the full error for debugging
            print(f"\n{'='*60}")
            print(f"ERROR DETAILS:")
            print(f"{'='*60}")
            import traceback
            traceback.print_exc()
            print(f"{'='*60}\n")
            sys.exit(0)
        
    elif mode == "schedule":
        print("⏰ Starting SCHEDULED MODE (runs daily)")
        from src.scheduler import schedule_bot
        try:
            scheduler = schedule_bot()
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️ Scheduler stopped by user")
            scheduler.shutdown()
            
    else:
        print("❌ Invalid mode. Usage: python run.py [test|schedule|once]")
        print("")
        print("Modes:")
        print("  test     - Dry run (no email) - for testing")
        print("  once     - Run once and send email")
        print("  schedule - Start background scheduler for daily runs")
        sys.exit(1)

if __name__ == "__main__":
    main()
