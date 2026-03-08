"""
Guardian Bot - Telegram Layer
All Telegram API calls live here. Clean separation from business logic.
"""
import json
import logging
import requests
from config import TOKEN, CHAT_ID, EMERGENCY_CIRCLE, ALERT_LEVELS

logger = logging.getLogger(__name__)
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

def get_main_keyboard() -> dict:
    """The main button grid shown after every response."""
    return {
        "keyboard": [
            [{"text": "💊 Meds"}, {"text": "📊 Vitals"}],
            [{"text": "🥤 Electrolytes"}, {"text": "⚔️ Quests"}],
            [{"text": "✨ Sanctuary"}, {"text": "🚨 Flare Mode"}],
            [{"text": "💤 Snooze 15m"}, {"text": "🏁 Milestones"}],
            [{"text": "📷 Scan Monitor"}, {"text": "✏️ Custom"}], 
            [{"text": "📈 Status"}, {"text": "🛠️ Fix Last"}, {"text": "📤 Export"}],
        
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }

def send_sanctuary_menu():
    """Sends an inline menu for Sanctuary tasks to avoid main menu clutter."""
    from telegram_client import BASE_URL
    import requests
    
    # Buttons with callback_data so the bot knows exactly what was clicked
    keyboard = {
        "inline_keyboard": [
            [{"text": "🚿 Shower", "callback_data": "sanc_shower"}, {"text": "🪥 Teeth", "callback_data": "sanc_teeth"}],
            [{"text": "💧 Refill Water", "callback_data": "sanc_refill"}, {"text": "🍼 Clean Bottle", "callback_data": "sanc_bottle"}],
            [{"text": "🐕 Umi walkies", "callback_data": "sanc_umi"}, {"text": "🐕 Meditation", "callback_data": "sanc_meditation"}],
            [{"text": "👕 Laundry", "callback_data": "sanc_laundry"}, {"text": "🧹 Room", "callback_data": "sanc_room"}],
        ]
    }
    
    payload = {
        "chat_id": CHAT_ID,
        "text": "✨ **Sanctuary Checklist**\n_Select a task to restore your environment._",
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard)
    }
    requests.post(f"{BASE_URL}/sendMessage", json=payload)

def send_message(text: str, chat_id: str = None, with_menu: bool = True) -> bool:
    """Send a message, optionally with the main keyboard."""
    target = chat_id or CHAT_ID
    payload = {
        "chat_id": target,
        "text": text,
        "parse_mode": "Markdown",
    }
    if with_menu:
        payload["reply_markup"] = json.dumps(get_main_keyboard())

    try:
        res = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)
        if not res.ok:
            logger.error(f"Telegram send failed: {res.text}")
        return res.ok
    except requests.RequestException as e:
        logger.error(f"Telegram request error: {e}")
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
