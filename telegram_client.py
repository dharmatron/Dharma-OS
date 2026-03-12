"""
Guardian Bot - Telegram Layer
All Telegram API calls live here. Clean separation from business logic.
"""
import json
import logging
import requests
from config import TOKEN, CHAT_ID, MED_SCHEDULE, EMERGENCY_CIRCLE, ALERT_LEVELS

logger = logging.getLogger(__name__)
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# --- telegram_client.py (Updated Keyboards) ---

def get_main_keyboard() -> dict:
    """The central navigation hub."""
    return {
        "keyboard": [
            [{"text": "💊 Meds"}, {"text": "📊 Vitals"}],
            [{"text": "✨ Sanctuary"}, {"text": "⚔️ Quests"}],  
            [{"text": "🥤 Electrolytes"}, {"text": "🚨 Flare Mode"}],
            [{"text": "💤 Snooze 15m"}, {"text": "🏁 Milestones"}],
            [{"text": "📷 Scan Monitor"}, {"text": "✏️ Custom"}], 
            [{"text": "📈 Status"}, {"text": "🛠️ Fix Last"}, {"text": "📤 Export"}]
        ],
        "resize_keyboard": True
    }

def get_meds_keyboard() -> dict:
    """The Medication Management Hub."""
    return {
        "keyboard": [
            [{"text": "💉 Log Meds"},     {"text": "📋 View Schedule"}],
            [{"text": "🕒 Retro Log"},    {"text": "⚙️ Change Meds"}], 
            [{"text": "⬅️ Back"}]
        ],
        "resize_keyboard": True
    }
    
def get_med_confirm_keyboard() -> dict:
    """The interactive Yes/No confirmation for medications."""
    return {
        "keyboard": [
            [{"text": "✅ Yes (Taken)"}, {"text": "❌ No (Skip)"}],
            [{"text": "⬅️ Back to Meds"}]
        ],
        "resize_keyboard": True
    }

def get_retro_windows_keyboard() -> dict:
    """Generates buttons for each time slot window in MED_SCHEDULE."""
    from config import MED_SCHEDULE
    buttons = [[{"text": f"Log {time}"}] for time in MED_SCHEDULE.keys()]
    buttons.append([{"text": "⬅️ Back to Meds"}])
    return {"keyboard": buttons, "resize_keyboard": True}

def get_vitals_keyboard() -> dict:
    """The Diagnostic entry hub."""
    return {
        "keyboard": [
            [{"text": "📸 Scan Oximeter"}, {"text": "📸 Scan BP"}],
            [{"text": "🔢 Manual Entry"}, {"text": "⬅️ Back"}]
        ],
        "resize_keyboard": True
    }

def get_sanctuary_keyboard() -> dict:
    """The Self-Care Node."""
    return {
        "keyboard": [
            [{"text": "🚿 Shower"},       {"text": "🪥 Teeth"}],
            [{"text": "💧 Refill Water"}, {"text": "🍼 Clean Bottle"}],
            [{"text": "🐕 Umi walkies"}, {"text": "🧘 Meditation"}],
            [{"text": "🧹 Room"},         {"text": "👕 Laundry"}],
            [{"text": "⬅️ Back"}]
        ],
        "resize_keyboard": True
    }
    
def get_quest_keyboard() -> dict:
    """The Action/Task management hub."""
    return {
        "keyboard": [
            [{"text": "📋 View All"}, {"text": "🛒 Export Walmart"}],
            [{"text": "🧹 Clear Done"}, {"text": "⬅️ Back"}]
        ],
        "resize_keyboard": True
    }

def send_message(text: str, chat_id: str = None, with_menu: bool = True, custom_keyboard: dict = None) -> bool:
    """Send a message with either the main, sanctuary, or no keyboard."""
    target = chat_id or CHAT_ID
    payload = {"chat_id": target, "text": text, "parse_mode": "Markdown"}
    
    if custom_keyboard:
        payload["reply_markup"] = json.dumps(custom_keyboard)
    elif with_menu:
        payload["reply_markup"] = json.dumps(get_main_keyboard())

    try:
        res = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)
        return res.ok
    except Exception as e:
        logger.error(f"Send error: {e}")
        return False

def send_document(file_path: str, caption: str = "") -> bool:
    """Send a file (e.g. CSV export) to the user."""
    try:
        with open(file_path, "rb") as f:
            res = requests.post(
                f"{BASE_URL}/sendDocument",
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"document": f},
                timeout=30,
            )
        return res.ok
    except (requests.RequestException, IOError) as e:
        logger.error(f"File send error: {e}")
        return False

def send_emergency_alert(level: str, vitals_summary: str = ""):
    """
    Send tiered alert to the emergency circle.
    level: "level_1", "level_2", or "level_3"
    """
    message = ALERT_LEVELS.get(level, "⚠️ Alert from Guardian.")
    if vitals_summary:
        message += f"\n\nLast readings:\n{vitals_summary}"

    # Always notify the main user
    send_message(message, with_menu=False)

    # Notify emergency circle
    for contact_id in EMERGENCY_CIRCLE:
        send_message(message, chat_id=str(contact_id), with_menu=False)
        logger.info(f"Emergency alert sent to {contact_id}")

def get_updates(offset: int = 0) -> list:
    """Poll for new Telegram messages."""
    try:
        res = requests.get(
            f"{BASE_URL}/getUpdates",
            params={"offset": offset, "timeout": 2},
            timeout=10,
        )
        if res.ok:
            return res.json().get("result", [])
    except requests.RequestException as e:
        logger.error(f"getUpdates error: {e}")
    return []

def clear_webhook():
    """Clear update buffer on startup to avoid processing old messages."""
    try:
        requests.get(f"{BASE_URL}/getUpdates?offset=-1", timeout=5)
    except requests.RequestException:
        pass

def download_photo(file_id: str, save_path: str = "capture.jpg") -> str | None:
    """Download a photo sent to the bot. Returns path or None."""
    try:
        info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}", timeout=10).json()
        file_path = info["result"]["file_path"]
        img = requests.get(
            f"https://api.telegram.org/file/bot{TOKEN}/{file_path}",
            timeout=15,
        ).content
        with open(save_path, "wb") as f:
            f.write(img)
        return save_path
    except (requests.RequestException, KeyError, IOError) as e:
        logger.error(f"Photo download error: {e}")
        return None
