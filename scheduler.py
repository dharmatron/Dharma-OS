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
    """Check if any meds are due right now and send reminders."""
    import pytz
    cdmx_tz = pytz.timezone(TIMEZONE)
    now = datetime.now(cdmx_tz)
    now_time = now.strftime("%H:%M")
    today = now.strftime("%Y-%m-%d")

    data = load_data()

    if data.get("flare_mode", False):
        pass

    # Skip if snoozed
    if time.time() < data.get("snooze_until", 0):
        return

    for med_time, med_name in MED_SCHEDULE.items():
        if now_time == med_time:
            if not check_meds_taken_today(med_name):
                send_message(
                    f"🔔 *TIME SENSITIVE*\n\n"
                    f"*{med_name}*\n"
                    f"Scheduled: {med_time}\n"
                    f"Window closes in 30 minutes.\n\n"
                    f"Tap 💊 Meds when taken!"
                )
                logger.info(f"Reminder sent for: {med_name}")
                time.sleep(61)  # Prevent duplicate alerts in same minute

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
