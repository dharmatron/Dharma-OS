import logging
import pytz
import med_hub
from datetime import datetime
from config import MED_SCHEDULE, TARGET_GOAL, TIMEZONE
from data import (
    load_data, add_credits, remove_last_entry, set_flare_mode, 
    set_snooze, export_to_csv, get_progress_bar, check_meds_taken_today
)
from telegram_client import (
    send_message, get_main_keyboard, get_sanctuary_keyboard, 
    get_meds_keyboard, get_quest_keyboard, get_vitals_keyboard,
    send_document, send_emergency_alert
)

logger = logging.getLogger(__name__)

# --- HELPERS ---
def _now_cdmx(): return datetime.now(pytz.timezone(TIMEZONE))

def _status_block(data: dict) -> str:
    mode = "🚨 FLARE" if data.get("flare_mode") else "🟢 NORMAL"
    bar = get_progress_bar(data["total_credits"], TARGET_GOAL)
    return f"📈 *STATUS*\nMode: {mode}\nBalance: *{data['total_credits']} pts*\n{bar}"

# --- LEGACY FUNCTIONS (PRESERVED) ---
def handle_task_generic(text: str):
    TASK_VALUES = {"shower": 40, "teeth": 20, "refill": 10, "clean": 20, "umi": 50, "meditation": 25, "room": 40, "laundry": 30, "vitals": 10, "default": 20}
    normalized = text.lower()
    points = next((v for k, v in TASK_VALUES.items() if k in normalized), 20)
    res = add_credits(f"Task: {text.title()}", points)
    send_message(f"✅ Logged +{points} pts.", with_menu=True)

def handle_status(text: str): send_message(_status_block(load_data()), with_menu=True)
def handle_flare(text: str):
    data = load_data(); new = not data.get("flare_mode", False); set_flare_mode(new)
    send_message(f"Flare Mode: {'ON 🚨' if new else 'OFF 🟢'}", with_menu=True)

def handle_milestones(text: str): send_message(f"🏆 *GOAL: {TARGET_GOAL}*\n{get_progress_bar(load_data()['total_credits'], TARGET_GOAL)}", with_menu=True)
def handle_custom(text: str):
    p = text.split()
    if len(p) >= 3: add_credits(" ".join(p[1:-1]), int(p[-1])); send_message("✏️ Logged.", with_menu=True)
    else: send_message("Use: `custom [task] [pts]`")

def handle_fix(text: str):
    data = load_data(); data["med_session"] = None; # Clear stuck sessions
    res = remove_last_entry(); save_data(data)
    send_message("🛠️ Session reset & last entry removed.", with_menu=True)

def handle_export(text: str): send_document(export_to_csv(), caption="Dharma-OS Export")
def handle_snooze(text: str): set_snooze(30); send_message("💤 Snoozed 30m.", with_menu=True)
def handle_emergency_test(text: str): send_emergency_alert("🚨 EMERGENCY TEST"); send_message("Alert sent.", with_menu=True)
def handle_restore(text: str): send_message("🏗️ Restoration protocol stable.", with_menu=True)

# --- NAVIGATION NODES ---
def handle_meds_node(text: str): send_message("💊 *MEDS HUB*", with_menu=True, custom_keyboard=get_meds_keyboard())
def handle_sanctuary_node(text: str): send_message("✨ *SANCTUARY*", with_menu=True, custom_keyboard=get_sanctuary_keyboard())
def handle_back_main(text: str): send_message("🛰️ *MAIN*", with_menu=True, custom_keyboard=get_main_keyboard())

# --- THE KEYWORD MAP (FIXED PRIORITY) ---
KEYWORD_MAP = {
    "back to meds": handle_meds_node,  # Specific navigation first!
    "log meds":    med_hub.start_sequence,
    "retro":       med_hub.start_retroactive_log,
    "log 06":      lambda t: med_hub.init_retro_session("06:00"),
    "log 08":      lambda t: med_hub.init_retro_session("08:00"),
    "log 14":      lambda t: med_hub.init_retro_session("14:00"),
    "log 20":      lambda t: med_hub.init_retro_session("20:00"),
    "log 22":      lambda t: med_hub.init_retro_session("22:00"),
    "taken":       med_hub.process_confirmation,
    "skip":        med_hub.process_confirmation,
    "schedule":    med_hub.view_schedule,
    "shift":       med_hub.apply_med_override,
    "change":      med_hub.handle_change_meds_start,
    "meds":        handle_meds_node,
    "sanctuary":   handle_sanctuary_node,
    "back":        handle_back_main,
    "⬅️":         handle_back_main,
    "status":      handle_status,
    "flare":       handle_flare,
    "milestone":   handle_milestones,
    "emergency":   handle_emergency_test,
    "fix":         handle_fix,
    "export":      handle_export,
    "snooze":      handle_snooze,
    "custom":      handle_custom,
    "restore":     handle_restore,
    "shower": handle_task_generic, "teeth": handle_task_generic, "room": handle_task_generic, "laundry": handle_task_generic
}

def route(text: str, photo_file_id: str = None) -> None:
    if photo_file_id: return
    n = text.lower().strip()
    for k, h in KEYWORD_MAP.items():
        if k in n: h(n); return
