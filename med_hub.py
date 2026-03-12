# med_hub.py
import logging
from datetime import datetime
import pytz
from config import MED_SCHEDULE, TIMEZONE
from data import load_data, save_data, add_credits
from telegram_client import send_message, get_meds_keyboard, get_med_confirm_keyboard

logger = logging.getLogger(__name__)

def _get_current_window():
    cdmx_tz = pytz.timezone(TIMEZONE)
    now = datetime.now(cdmx_tz).strftime("%H:%M")
    # Finding the window closest to current time (2hr buffer)
    for window in MED_SCHEDULE.keys():
        hw = int(window.split(":")[0])
        hn = int(now.split(":")[0])
        if abs(hw - hn) <= 2: return window
    return None

def start_sequence(text: str = None):
    data = load_data()
    if data.get("med_session"): return # Don't interrupt active session
    
    window = _get_current_window()
    if not window:
        send_message("⚠️ No active med window found.", with_menu=True)
        return
    
    meds = MED_SCHEDULE[window].split(" + ")
    data["med_session"] = {"window": window, "meds": meds, "index": 0}
    save_data(data)
    
    send_message(f"💊 *PROTOCOL: {window}*\nNext: **{meds[0]}**\nConfirm intake:", 
                 with_menu=True, custom_keyboard=get_med_confirm_keyboard())

def process_confirmation(text: str):
    data = load_data()
    session = data.get("med_session")
    if not session: return

    is_taken = any(word in text.lower() for word in ["yes", "✅", "taken"])
    current_med = session["meds"][session["index"]]
    
    # Precise Data Logging
    status = "TAKEN" if is_taken else "SKIPPED"
    points = 30 if is_taken else 0
    add_credits(f"Med: {current_med} ({status})", points)
    
    session["index"] += 1
    if session["index"] < len(session["meds"]):
        save_data(data)
        send_message(f"Logged {status}.\nNext: **{session['meds'][session['index']]}**", 
                     with_menu=True, custom_keyboard=get_med_confirm_keyboard())
    else:
        data["med_session"] = None
        save_data(data)
        send_message("🏁 *Protocol Complete.*", with_menu=True, custom_keyboard=get_meds_keyboard())
