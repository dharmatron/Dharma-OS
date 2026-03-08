"""
Guardian Bot - Main Entry Point
The Miracle Bridge Command Center

Run locally:    python main.py
Deploy:         Push to Railway/Render, set env vars, done.
"""
import time
import logging
import sys
from config import TOKEN, CHAT_ID
from data import load_data, mark_update_processed
from telegram_client import get_updates, clear_webhook, send_message
from handlers import route
import scheduler

# ── LOGGING SETUP ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# ── STARTUP CHECKS ───────────────────────────────────────────────────────────

def _validate_config():
    """Fail fast if required env vars are missing."""
    errors = []
    if not TOKEN:
        errors.append("TELEGRAM_TOKEN is not set.")
    if not CHAT_ID:
        errors.append("TELEGRAM_CHAT_ID is not set.")
    if errors:
        for e in errors:
            logger.critical(e)
        sys.exit(1)

# ── MAIN LOOP ─────────────────────────────────────────────────────────────────

def main():
    _validate_config()

    logger.info("=" * 50)
    logger.info("  🧠 MIRACLE BRIDGE COMMAND CENTER")
    logger.info("  Guardian Bot - Starting up...")
    logger.info("=" * 50)

    # Clear old messages so we don't re-process history on restart
    clear_webhook()

    # Start background scheduler (med reminders, daily init)
    scheduler.start()

    send_message(
        "🛡️ *Guardian is online.*\n\n"
        "System restarted and ready.\n"
        "Use the buttons below or type a command.",
    )

    logger.info("Bot is listening for messages...")

    while True:
        try:
            data = load_data()
            last_id = data.get("last_update_id", 0)

            updates = get_updates(offset=last_id + 1)

            for update in updates:
                update_id  = update["update_id"]
                msg        = update.get("message", {})
                text       = msg.get("text", "")
                photo      = msg.get("photo")

                # Only respond to your own chat
                sender_id = str(msg.get("chat", {}).get("id", ""))
                if sender_id != str(CHAT_ID):
                    logger.warning(f"Ignored message from unknown chat: {sender_id}")
                    mark_update_processed(update_id)
                    continue

                logger.info(f"Incoming: '{text}' | photo: {bool(photo)}")

                photo_file_id = photo[-1]["file_id"] if photo else None
                route(text, photo_file_id=photo_file_id)
                mark_update_processed(update_id)

        except KeyboardInterrupt:
            logger.info("Shutdown requested.")
            scheduler.stop()
            break
        except Exception as e:
            # Log the real error (no more silent swallowing!)
            logger.error(f"Main loop error: {e}", exc_info=True)
            time.sleep(5)  # Brief pause before retrying

        time.sleep(2)

if __name__ == "__main__":
    main()
