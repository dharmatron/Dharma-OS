"""
Guardian Bot - Master Command Handlers
"""
import logging
import pytz
import med_hub  # The dedicated medication engine
from datetime import datetime
from config import MED_SCHEDULE, POINTS, TARGET_GOAL, TIMEZONE
from data import (
    load_data, add_credits, deduct_credits, remove_last_entry,
    set_flare_mode, set_snooze, export_to_csv, get_progress_bar
)
from telegram_client import (
    send_message, get_main_keyboard, get_sanctuary_keyboard, 
    get_meds_keyboard, get_quest_keyboard, get_vitals_keyboard,
    send_document, send_emergency_alert
)

logger = logging.getLogger(__name__)

# ── 1. UNIVERSAL TASK VALUES ────────────────────────────────────────────────
# Coherent logic: All "one-tap" tasks live here. 
# Changing a number here updates the whole system.
TASK_VALUES = {
    # Sanctuary Node
    "shower": 40, "teeth": 20, "refill": 10, "clean": 20, 
    "umi walkies": 50, "meditation": 25, "room": 40, "laundry": 30,
    # Vitals Node
    "vitals": 10, "scan": 15, "manual": 10,
    # System Defaults
    "electrolytes": 15, "default": 20
}

# ── 2. HELPERS ──────────────────────────────────────────────────────────────

def _now_cdmx():
    return datetime.now(pytz.timezone(TIMEZONE))

def _status_block(data: dict) -> str:
    mode = "🚨 FLARE" if data.get("flare_mode") else "🟢 NORMAL"
    bar  = get_progress_bar(data["total_credits"], TARGET_GOAL)
    remaining = max(0, TARGET_GOAL - data["total_credits"])
    return (
        f"📈 *GUARDIAN STATUS*\n"
        f"Mode: {mode}\n"
        f"Balance: *{data['total_credits']} pts*\n"
        f"Goal: {bar}\n"
        f"Remaining: {remaining} pts"
    )

# ── 3. CORE HANDLERS (The "Logic" Layer) ───────────────────────────────────

def handle_task_generic(text: str):
    """The workhorse for Sanctuary and Vitals. One tap = Points."""
    normalized = text.lower()
    points = TASK_VALUES.get("default")
    
    for keyword, value in TASK_VALUES.items():
        if keyword in normalized:
            points = value
            break
            
    res = add_credits(f"Task: {text.title()}", points)
    send_message(f"✅ *Action Logged*\n+{points} pts | Balance: {res['total']} pts", with_menu=True)

def handle_status(text: str):
    data = load_data()
    send_message(_status_block(data), with_menu=True)

def handle_flare(text: str):
    data = load_data()
    new_state = not data.get("flare_mode", False)
    set_flare_mode(new_state)
    status = "ENABLED 🚨" if new_state else "DISABLED 🟢"
    send_message(f"Flare Mode is now {status}", with_menu=True)

def handle_milestones(text: str):
    data = load_data()
    bar = get_progress_bar(data["total_credits"], TARGET_GOAL)
    send_message(f"🏁 *MILESTONES*\nTarget: {TARGET_GOAL} pts\n{bar}\nYou are the Architect of your own stability.", with_menu=True)

def handle_custom(text: str):
    parts = text.split()
    if len(parts) >= 3:
        try:
            pts = int(parts[-1])
            task = " ".join(parts[1:-1])
            res = add_credits(task, pts)
            send_message(f"✏️ Custom Task: {task}\n+{pts} pts logged.", with_menu=True)
            return
        except ValueError: pass
    send_message("Usage: `custom [task] [points]`")

def handle_fix(text: str):
    res = remove_last_entry()
    send_message(f"🛠️ Last entry removed.\nNew Balance: {res['total']} pts", with_menu=True)

def handle_export(text: str):
    file_path = export_to_csv()
    send_message("📊 Generating clinical history report...")
    send_document(file_path, caption="Dharma-OS Export")

def handle_snooze(text: str):
    set_snooze(30)
    send_message("💤 System silenced for 30 minutes. Rest is a prerequisite for power.", with_menu=True)

# ── 4. VISION BRIDGE (The Scanning Layer) ──────────────────────────────────

def handle_scan_monitor(text: str):
    send_message("📸 *VISION BRIDGE ACTIVE*\nSend a photo of the monitor. (Avoid glare for E-Ink/LCD displays).", with_menu=True)

def handle_photo(file_id: str):
    """Processes incoming medical monitor images."""
    send_message("👁️ *Analyzing Vitals...*")
    # vision.py integration point
    res = add_credits("Vitals Scan", 15)
    send_message(f"✅ Data Extracted.\n+15 pts logged.", with_menu=True)

# ── 5. LEGACY & EMERGENCY ───────────────────────────────────────────────────

def handle_emergency_test(text: str):
    send_emergency_alert("🚨 EMERGENCY TEST: The Architect has triggered a system-wide alert.")
    send_message("Emergency signals dispatched to your Circle.", with_menu=True)

def handle_restore(text: str):
    """Future: Restore 'Sanctuary' state from backup."""
    send_message("🏗️ Sanctuary Restoration protocol initialized. System environment stable.", with_menu=True)

# ── 6. NAVIGATION NODES (The "UI" Layer) ────────────────────────────────────

def handle_sanctuary_node(text: str):
    send_message("✨ *SANCTUARY NODE*", with_menu=True, custom_keyboard=get_sanctuary_keyboard())

def handle_meds_node(text: str):
    send_message("💊 *MEDS NODE*", with_menu=True, custom_keyboard=get_meds_keyboard())

def handle_quest_node(text: str):
    send_message("⚔️ *QUEST HUB*", with_menu=True, custom_keyboard=get_quest_keyboard())

def handle_vitals_node(text: str):
    send_message("📊 *VITALS HUB*", with_menu=True, custom_keyboard=get_vitals_keyboard())

def handle_back(text: str):
    send_message("🛰️ *MAIN HUB*", with_menu=True, custom_keyboard=get_main_keyboard())

# ── 7. THE ROUTER (PRIORITY MATCHING) ───────────────────────────────────────

# Yes, delete the old COMMAND_MAP. 
# This KEYWORD_MAP handles fuzzy matches and emojis perfectly.
KEYWORD_MAP = {
    # 1. High Priority (Specific Phrases)
    "log meds":  med_hub.start_sequence,
    "taken":     med_hub.process_confirmation,
    "skip":      med_hub.process_confirmation,
    "schedule":  med_hub.view_schedule,
    "shift":     med_hub.apply_med_override,
    "change":    med_hub.handle_change_meds_start,
    "emergency": handle_emergency_test,
    
    # 2. Nodes (Menu Swapping)
    "meds":      handle_meds_node,
    "sanctuary": handle_sanctuary_node,
    "quests":    handle_quest_node,
    "vitals":    handle_vitals_node,
    "back":      handle_back,
    "⬅️":       handle_back,
    
    # 3. System Commands
    "status":    handle_status,
    "flare":     handle_flare,
    "milestone": handle_milestones,
    "custom":    handle_custom,
    "export":    handle_export,
    "fix":       handle_fix,
    "snooze":    handle_snooze,
    "scan":      handle_scan_monitor,
    "restore":   handle_restore,
    
    # 4. Universal Tasks (Handled by handle_task_generic)
    "shower": handle_task_generic, "teeth": handle_task_generic,
    "refill": handle_task_generic, "clean": handle_task_generic,
    "walkies": handle_task_generic, "meditation": handle_task_generic,
    "room": handle_task_generic, "laundry": handle_task_generic,
    "manual": handle_task_generic,
}

def route(text: str, photo_file_id: str = None) -> None:
    if photo_file_id:
        handle_photo(photo_file_id)
        return

    normalized = text.lower().strip()

    # Step 1: Check the Keyword Map (Priority order)
    for keyword, handler in KEYWORD_MAP.items():
        if keyword in normalized:
            handler(normalized)
            return

    # Step 2: Dynamic Commands
    if normalized.startswith("quest"):
        # Quest addition logic here
        pass
