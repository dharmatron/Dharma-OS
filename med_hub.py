import logging
from datetime import datetime
import pytz
from config import MED_SCHEDULE, TIMEZONE
from data import load_data, save_data, add_credits
from telegram_client import (
    send_message, get_meds_keyboard, get_med_confirm_keyboard, 
    get_retro_windows_keyboard
)

logger = logging.getLogger(__name__)

def _get_current_window():
    data = load_data()
    overrides = data.get("schedule_overrides", {})
    cdmx_tz = pytz.timezone(TIMEZONE)
    now_hour = datetime.now(cdmx_tz).hour

    for original_time, details in overrides.items():
        shifted_time = details.get("new_time")
        if shifted_time:
            sh = int(shifted_time.split(":")[0])
            if abs(sh - now_hour) <= 2: return original_time

    for window in MED_SCHEDULE.keys():
        if window not in overrides:
            hw = int(window.split(":")[0])
            if abs(hw - now_hour) <= 2: return window
    return None

def start_sequence(text: str = None):
    data = load_data()
    # FIX: Handle stuck sessions instead of silent failure
    if data.get("med_session"):
        send_message("⚠️ *Session Active:* You are already logging meds. Use 'Skip' or 'Taken' to finish, or type 'fix' to reset.", with_menu=True)
        return 
    
    window = _get_current_window()
    if not window:
        send_message("⚠️ No active window. Use 'Retro Log' for past doses.", with_menu=True)
        return
    
    meds_list = [m.strip() for m in MED_SCHEDULE[window].split("+")]
    data["med_session"] = {"window": window, "meds": meds_list, "index": 0, "is_retro": False}
    save_data(data)
    
    send_message(f"🔔 *PROTOCOL: {window}*\nNext: **{meds_list[0]}**", with_menu=True, custom_keyboard=get_med_confirm_keyboard())

def start_retroactive_log(text: str = None):
    send_message("🕒 *RETROACTIVE LOG*\nSelect window:", with_menu=True, custom_keyboard=get_retro_windows_keyboard())

def init_retro_session(window: str):
    data = load_data()
    if data.get("med_session"):
        data["med_session"] = None # Clear old session for retro log
    
    meds_list = [m.strip() for m in MED_SCHEDULE[window].split("+")]
    data["med_session"] = {"window": window, "meds": meds_list, "index": 0, "is_retro": True}
    save_data(data)
    
    send_message(f"📝 *RETRO: {window}*\nNext: **{meds_list[0]}**", with_menu=True, custom_keyboard=get_med_confirm_keyboard())

def process_confirmation(text: str):
    data = load_data()
    session = data.get("med_session")
    if not session: return

    is_taken = any(word in text.lower() for word in ["yes", "✅", "taken"])
    current_med = session["meds"][session["index"]]
    
    points = (15 if session.get("is_retro") else 30) if is_taken else 0
    status = ("TAKEN (RETRO)" if session.get("is_retro") else "TAKEN") if is_taken else "SKIPPED"

    add_credits(f"Med: {current_med} ({status})", points)
    session["index"] += 1
    
    if session["index"] < len(session["meds"]):
        save_data(data)
        send_message(f"Logged {status}.\nNext: **{session['meds'][session['index']]}**", with_menu=True, custom_keyboard=get_med_confirm_keyboard())
    else:
        data["med_session"] = None
        save_data(data)
        send_message("🏁 *Done.*", with_menu=True, custom_keyboard=get_meds_keyboard())

def view_schedule(text: str):
    msg = "📋 *SCHEDULE*\n" + "\n".join([f"• `{t}`: {m}" for t, m in MED_SCHEDULE.items()])
    send_message(msg, with_menu=True, custom_keyboard=get_meds_keyboard())

def handle_change_meds_start(text: str):
    send_message("⚙️ *SHIFT:* `shift 08:00 to 09:00`", with_menu=True, custom_keyboard=get_meds_keyboard())

def apply_med_override(text: str):
    data = load_data(); overrides = data.get("schedule_overrides", {})
    try:
        p = text.split(); overrides[p[1]] = {"new_time": p[3]}
        data["schedule_overrides"] = overrides; save_data(data)
        send_message(f"✅ Shifted {p[1]} to {p[3]}", with_menu=True)
    except: send_message("❌ Format: `shift 08:00 to 09:00`", with_menu=True)
