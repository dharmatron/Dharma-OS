import logging
from datetime import datetime
import pytz
from config import MED_SCHEDULE, TIMEZONE
from data import load_data, save_data, add_credits
from telegram_client import (
    send_message, get_meds_keyboard, get_med_confirm_keyboard
)

logger = logging.getLogger(__name__)

def _get_current_window():

    data = load_data()
    overrides = data.get("schedule_overrides", {})
    
    cdmx_tz = pytz.timezone(TIMEZONE)
    now_hour = datetime.now(cdmx_tz).hour

    # 1. Check for Overrides (Shifted Windows)
    # If 08:00 was shifted to 10:00, and it's now 10:00, return '08:00'
    for original_time, details in overrides.items():
        shifted_time = details.get("new_time")
        if shifted_time:
            sh = int(shifted_time.split(":")[0])
            if abs(sh - now_hour) <= 2:
                return original_time

    # 2. Check Default Schedule
    # Only returns a window if it hasn't been explicitly overridden
    for window in MED_SCHEDULE.keys():
        if window not in overrides:
            hw = int(window.split(":")[0])
            if abs(hw - now_hour) <= 2:
                return window
                
    return None

def start_sequence(text: str = None):
    """Initiates the step-by-step medication check."""
    data = load_data()
    
    # Prevent overlapping sessions
    if data.get("med_session"):
        return 

    window = _get_current_window()
    if not window:
        send_message("⚠️ *Protocol Note:* No active medication window found right now.", with_menu=True)
        return
    
    meds_list = [m.strip() for m in MED_SCHEDULE[window].split("+")]
    data["med_session"] = {
        "window": window,
        "meds": meds_list,
        "index": 0
    }
    save_data(data)
    
    msg = f"🔔 *PROTOCOL ALERT: {window}*\nNext: **{meds_list[0]}**\n\nDid you take it?"
    send_message(msg, with_menu=True, custom_keyboard=get_med_confirm_keyboard())

def process_confirmation(text: str):
    """Logs the med as TAKEN or SKIPPED and moves to the next."""
    data = load_data()
    session = data.get("med_session")
    
    if not session:
        return # Silent fail if no session active

    # 1. Determine precision status
    is_taken = any(word in text.lower() for word in ["yes", "✅", "taken"])
    current_med = session["meds"][session["index"]]
    
    status_label = "TAKEN" if is_taken else "SKIPPED"
    points = 30 if is_taken else 0
    
    # 2. Log to history (Essential for medical review)
    add_credits(f"Med: {current_med} ({status_label})", points)
    
    # 3. Advance Index
    session["index"] += 1
    
    if session["index"] < len(session["meds"]):
        next_med = session["meds"][session["index"]]
        save_data(data)
        send_message(
            f"Logged: *{status_label}*\n\nNext: **{next_med}**", 
            with_menu=True, 
            custom_keyboard=get_med_confirm_keyboard()
        )
    else:
        # 4. Clean up session
        data["med_session"] = None
        save_data(data)
        send_message(
            "🏁 *Protocol Complete.*\nAll medications logged for this window.", 
            with_menu=True, 
            custom_keyboard=get_meds_keyboard()
        )

def view_schedule(text: str):
    """Outputs the full medication table."""
    msg = "📋 *MEDICATION MASTER SCHEDULE*\n\n"
    for time, meds in MED_SCHEDULE.items():
        msg += f"• `{time}`: {meds}\n"
    send_message(msg, with_menu=True, custom_keyboard=get_meds_keyboard())

def handle_change_meds_start(text: str):
    """Initializes the change med flow."""
    msg = (
        "⚙️ *MEDICATION SYSTEM OVERRIDE*\n\n"
        "How would you like to adjust the protocol?\n"
        "1. **Shift Time**: `shift [time] to [new_time]`\n"
        "2. **Edit Meds**: `edit [time] meds [new_list]`\n\n"
        "_Note: These changes persist until the next System Init._"
    )
    send_message(msg, with_menu=True, custom_keyboard=get_meds_keyboard())

def apply_med_override(text: str):
    """Parses and applies temporary changes to the schedule."""
    data = load_data()
    overrides = data.get("schedule_overrides", {})
    
    # Simple parsing logic for 'shift 08:00 to 09:00'
    if "shift" in text.lower():
        parts = text.split()
        try:
            old_time, new_time = parts[1], parts[3]
            overrides[old_time] = {"new_time": new_time}
            data["schedule_overrides"] = overrides
            save_data(data)
            send_message(f"✅ Time Shifted: {old_time} is now {new_time}.", with_menu=True)
        except:
            send_message("❌ Format Error. Use: `shift 08:00 to 09:00`.", with_menu=True)
