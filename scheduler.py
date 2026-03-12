"""
Guardian Bot - Scheduler
Handles timed medication reminders and daily init.
Runs as a background thread alongside the main bot loop.
"""
import time
import logging
import threading
from datetime import datetime
from config import MED_SCHEDULE, TIMEZONE
from data import load_data, add_credits, check_meds_taken_today
from telegram_client import send_message

logger = logging.getLogger(__name__)

_scheduler_thread = None
_stop_event = threading.Event()

def _check_schedule():
    now_time = datetime.now(pytz.timezone(TIMEZONE)).strftime("%H:%M")
    if now_time in MED_SCHEDULE:
        # Instead of just a message, trigger the sequence
        from handlers import handle_log_meds_start
        handle_log_meds_start(f"Scheduled: {now_time}")

def _daily_init():  # Award System Init credits once per day on first run #
    
    import pytz
    cdmx_tz = pytz.timezone(TIMEZONE)
    today = datetime.now(cdmx_tz).strftime("%Y-%m-%d")
    data = load_data()

    already_init = any(   # Improved Check: Look specifically for today's "System Init"
        e.get("task") == "System Init" and e.get("timestamp", "").startswith(today)
        for e in data.get("history", [])
    )

    if not already_init:
        result = add_credits("System Init", 50)
        send_message(
            f"🛡️ *Guardian Online*\n\n"
            f"Good morning, Architect. System initialized.\n"
            f"+50 pts | Balance: {result['total']} pts\n\n"
            f"First meds due at {list(MED_SCHEDULE.keys())[0]} 💊"
        )
        logger.info("Daily init complete.")
        
    else:   # If already init, we just log it silently so it doesn't spam you
        logger.info("System already initialized for today. Skipping points/message.")

def _scheduler_loop():
    """Main scheduler loop. Checks every 30 seconds."""
    logger.info("Scheduler started.")
    _daily_init()

    while not _stop_event.is_set():
        try:
            _check_schedule()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        time.sleep(30)

    logger.info("Scheduler stopped.")

def start():
    """Start the scheduler in a background thread."""
    global _scheduler_thread
    _stop_event.clear()
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True, name="scheduler")
    _scheduler_thread.start()
    logger.info("Scheduler thread launched.")

def stop():
    """Stop the scheduler."""
    _stop_event.set()
    if _scheduler_thread:
        _scheduler_thread.join(timeout=5)
