"""
Guardian Bot - Command Handlers
Each button/command maps to a handler function.
Clean, testable, easy to extend.
"""
import logging
from datetime import datetime
from config import MED_SCHEDULE, POINTS, GRACE_WARNING, GRACE_CUTOFF, TARGET_GOAL, TIMEZONE
from data import (
    load_data, add_credits, deduct_credits, remove_last_entry,
    set_flare_mode, set_snooze, export_to_csv, get_progress_bar,
    check_meds_taken_today
)
from telegram_client import send_message, send_document, send_emergency_alert, get_sanctuary_keyboard, get_main_keyboardsend_message
import pytz

logger = logging.getLogger(__name__)

# ── HELPERS ──────────────────────────────────────────────────────────────────

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
        f"Progress: {bar}\n"
        f"Remaining to goal: {remaining} pts"
    )

def _find_current_med():
    """Find which med should be taken right now (within 1 hour window)."""
    now = _now_cdmx()
    current_hour = now.hour
    for med_time, med_name in MED_SCHEDULE.items():
        sched_hour = int(med_time.split(":")[0])
        if abs(current_hour - sched_hour) <= 1:
            return med_time, med_name
    return None, None

def _grace_penalty(med_time: str) -> tuple[int, str]:
    """
    Calculate grace period penalty.
    Returns (points_to_deduct, message).
    """
    now = _now_cdmx()
    fmt = "%H:%M"
    sched = datetime.strptime(med_time, fmt)
    current = datetime.strptime(now.strftime(fmt), fmt)
    diff_mins = (current - sched).total_seconds() / 60

    if diff_mins <= GRACE_WARNING:
        return 0, ""
    elif diff_mins <= GRACE_CUTOFF:
        return 10, f"⚠️ Grace period exceeded by {int(diff_mins - GRACE_WARNING)}m. -10 pts."
    else:
        return -1, f"🚫 Window closed (>{GRACE_CUTOFF}m). No points this dose."

# ── COMMAND HANDLERS ─────────────────────────────────────────────────────────

def handle_meds(_: str) -> None:
    med_time, med_name = _find_current_med()

    if not med_time:
        send_message("💊 No scheduled meds right now. Use ✏️ Custom to log an off-schedule dose.")
        return

    penalty_pts, penalty_msg = _grace_penalty(med_time)

    if penalty_pts == -1:
        # Window closed
        send_message(f"🚫 *{med_name}* window closed.\nNo points awarded — but your health still matters! Log it with ✏️ Custom.")
        return

    result = add_credits(f"Meds: {med_name}", POINTS["meds_on_time"])
    final = result["final_points"]

    if penalty_pts > 0:
        deduct_credits("Late med penalty", penalty_pts)
        final -= penalty_pts
        send_message(f"💊 *{med_name}* logged.\n{penalty_msg}\nNet: +{final} pts {'*(FLARE x2)*' if result['flare_active'] else ''}")
    else:
        bar = get_progress_bar(result["total"], TARGET_GOAL)
        send_message(
            f"💊 *Meds logged!* +{final} pts {'*(FLARE x2!)*' if result['flare_active'] else ''}\n"
            f"{bar}\n"
            f"Balance: {result['total']} pts"
        )

def handle_vitals(_: str) -> None:
    result = add_credits("Manual Vitals Check", POINTS["vitals"])
    send_message(
        f"📊 *Vitals logged!* +{result['final_points']} pts\n"
        f"Balance: {result['total']} pts\n\n"
        f"_Tip: Send a photo of your monitor screen to auto-log your readings!_"
    )

def handle_electrolytes(_: str) -> None:
    result = add_credits("Hydration / Electrolytes", POINTS["electrolytes"])
    send_message(
        f"🥤 *Electrolytes logged!* +{result['final_points']} pts\n"
        f"Balance: {result['total']} pts"
    )

def handle_sanctuary(text: str):
    data = load_data()
    normalized = text.lower().strip()
    
    # If they just tapped the main "Sanctuary" button
    if "sanctuary" in text.lower():
        from telegram_client import send_sanctuary_menu
        send_sanctuary_menu()
        return

    if "sanctuary" in normalized:
        send_message("✨ **Sanctuary Mode**\n_Self-care is the ultimate quest._\n\n", custom_keyboard=get_sanctuary_keyboard())
        return

    tasks = {
        "sanc_shower": ("🚿 Shower", 40),
        "sanc_teeth":  ("🪥 Teeth", 20),
        "sanc_refill": ("💧 Refill Water", 10),
        "sanc_bottle": ("🍼 Clean Water Bottle", 20),
        "sanc_refill": ("💧 Refill Water", 10),
        "sanc_walkies": ("🐕Umi Walkies", 50),
        "sanc_meditation": ("🧘 Meditation", 25),
        "sanc_room":   ("🧹 Room", 40),
        "sanc_laundry":("👕 Laundry", 30)
    }
    
    for key, (display_name, pts) in tasks.items():
        if key in normalized:
            bonus = 0
            if key in ["bottle", "refill"]:             # --- HYDRATION STREAK LOGIC ---
                data["water_streak"] = data.get("water_streak", 0) + 1
                if data["water_streak"] >= 3:
                    bonus = 20
                    data["water_streak"] = 0 # Reset
                    msg = "\n🔥 **HYDRATION STREAK!** (+20 bonus pts)"
                else:
                    msg = ""
            else:
                msg = ""

            res = add_credits(f"Sanctuary: {display_name}", pts + bonus)
            save_data(data)
            send_message(f"✨ **Sanctuary Restored:** {display_name}\n+{pts+bonus} pts{msg}\nTotal: {res['total']} pts\nYou're doing great, Architect."")
            return
        
    # Match the incoming text/callback to the task
    for key, (name, pts) in tasks.items():
        if key in text or name.lower() in text.lower():
            # --- HYDRATION STREAK LOGIC ---
            bonus = 0
            if "bottle" in key or "refill" in key:
                data["water_streak"] = data.get("water_streak", 0) + 1
                if data["water_streak"] >= 3:
                    bonus = 20
                    data["water_streak"] = 0 # Reset
                    msg_bonus = "\n🔥 **HYDRATION STREAK!** (+20 bonus pts)"
                else:
                    msg_bonus = ""
            else:
                msg_bonus = ""

            res = add_credits(f"Sanctuary: {name}", pts + bonus)
            save_data(data)
            send_message(f"✨ **Sanctuary Restored:** {name}\n+{pts + bonus} pts{msg_bonus}\nTotal: {res['total']} pts\nYou're doing great, Architect.")
            return
                         

def handle_quests(text: str):
    data = load_data()
    if "quests" not in data:
        data["quests"] = []

    normalized = text.lower().strip()
    
    if normalized in ["⚔️ quests", "quests"]:     # 1. Show Active Quests
        if not data["quests"]:
            send_message("⚔️ **No active Quests.**\nType `quest [item]` to add one (e.g., `quest buy puffed rice`).")
        else:
            quest_list = "\n".join([f"{i+1}. {q}" for i, q in enumerate(data["quests"])])
            send_message(f"⚔️ **Active Quests:**\n\n{quest_list}\n\n_Type 'done [number]' to complete one (+5 pts)_")
        return
    
    if normalized.startswith("quest "): # 2. Add a Quest
        new_quest = text[6:].strip()
        data["quests"].append(new_quest)
        save_data(data)
        send_message(f"📜 **Quest Accepted:** {new_quest}")

   
    elif normalized.startswith("done "):   # 3. Complete a Quest (Earn Credits!)
        try:
            idx = int(normalized.split(" ")[1]) - 1
            if 0 <= idx < len(data["quests"]):
                completed = data["quests"].pop(idx)

                save_data(data)  # Save first to update list
                
                res = add_credits(f"Quest: {completed}", 5)   # Reward the architect
                send_message(f"🏆 **Quest Complete:** {completed}\n+5 pts | New Balance: {res['total']} pts")
            else:
                send_message("❌ Invalid quest number.")
        except ValueError:
            send_message("❌ Please use a number (e.g., `done 1`).")


def handle_flare(_: str) -> None:
    data = load_data()
    new_status = not data.get("flare_mode", False)
    set_flare_mode(new_status)

    if new_status:
        send_message(
            "🚨 *FLARE MODE ACTIVATED*\n\n"
            "All points doubled. Penalties suppressed.\n"
            "You're doing great — just survive today.\n\n"
            "_Tap 🚨 Flare Mode again to deactivate when you're better._"
        )
    else:
        send_message(
            "🟢 *NORMAL MODE RESTORED*\n\n"
            "Great job getting through that. Standard scoring resumed."
        )

def handle_status(_: str) -> None:
    data = load_data()
    send_message(_status_block(data))

def handle_milestones(_: str) -> None:
    data  = load_data()
    bal   = data["total_credits"]
    levels = [
        (250,  "L1: Boot",       "📤 Export unlocked"),
        (750,  "L2: Stability",  "🔧 Advanced tools"),
        (1500, "L3: Specialist", "🧬 Monitor bridge"),
        (2500, "L4: Keyboard!",  "⌨️ THE GOAL"),
    ]
    lines = ["🏁 *MILESTONE TRACKER*\n"]
    for pts, label, reward in levels:
        if bal >= pts:
            lines.append(f"✅ *{label}* — {reward}")
        else:
            lines.append(f"🔒 *{label}* — {pts - bal} pts away | {reward}")
    send_message("\n".join(lines))

def handle_custom(text: str) -> None:
    """
    Expects format: "custom TaskName 50"
    If called from button with no args, prompt the user.
    """
    parts = text.strip().split(" ", 2)
    if len(parts) < 3:
        send_message(
            "✏️ *Custom Log*\n\n"
            "Reply with:\n`custom [what you did] [points]`\n\n"
            "Example: `custom Walked to kitchen 10`",
            with_menu=False,
        )
        return

    try:
        pts  = int(parts[-1])
        task = " ".join(parts[1:-1])
        result = add_credits(task, pts)
        send_message(f"✏️ *Logged:* {task}\n+{result['final_points']} pts\nBalance: {result['total']} pts")
    except ValueError:
        send_message("❌ Points must be a number. Example: `custom Rest 10`", with_menu=False)

def handle_fix(_: str) -> None:
    removed = remove_last_entry()
    if not removed:
        send_message("❌ Nothing to fix — history is empty.")
        return
    send_message(
        f"🛠️ *Removed last entry:*\n"
        f"Task: {removed['task']}\n"
        f"Points reversed: {removed['points']}"
    )

def handle_export(_: str) -> None:
    data = load_data()
    if data["total_credits"] < 250:
        send_message(f"🔒 Export unlocks at L1 (250 pts). {250 - data['total_credits']} pts to go!")
        return

    path = export_to_csv()
    sent = send_document(path, caption="📊 Your Guardian health log export")
    if not sent:
        send_message("❌ Export failed. Try again in a moment.")

def handle_snooze(_: str) -> None:
    set_snooze(15)
    send_message("💤 *Snoozed 15 minutes.* Alerts paused. Rest up, Architect.")

def handle_scan_monitor(_: str) -> None:
    send_message(
        "📷 *Monitor Scan Mode*\n\n"
        "Send a clear photo of your YK-8000C screen.\n"
        "I'll extract your heart rate and log it automatically.\n\n"
        "_Make sure the green HR number is visible and in focus._",
        with_menu=False,
    )

def handle_photo(file_id: str) -> None:
    """Process a photo sent to the bot — OCR for vitals."""
    from vision import ocr_vitals
    from telegram_client import download_photo

    path = download_photo(file_id)
    if not path:
        send_message("❌ Couldn't download the photo. Try again.")
        return

    vitals = ocr_vitals(path)
    if not vitals:
        send_message(
            "📷 Photo received but I couldn't read the numbers clearly.\n"
            "Try: better lighting, hold the camera steady, zoom in on the screen."
        )
        return

    result = add_credits(f"Auto-OCR: HR {vitals.get('hr', '?')} SpO2 {vitals.get('spo2', '?')}", POINTS["auto_ocr"])
    send_message(
        f"📸 *Vitals auto-logged!*\n"
        f"HR: {vitals.get('hr', '?')} bpm\n"
        f"SpO2: {vitals.get('spo2', '?')}%\n"
        f"+{result['final_points']} pts | Balance: {result['total']}"
    )

def handle_emergency_test(_: str) -> None:
    """Hidden command: /emergency_test — test the alert system."""
    send_emergency_alert("level_1", "HR: 105 | SpO2: 94% | PI: 0.8%")
    send_message("🔔 Test alert sent to emergency circle.")

# ── ROUTER ───────────────────────────────────────────────────────────────────

# Add this function above COMMAND_MAP
def handle_restore(text: str):
    from data import save_data
    new_data = {
        "total_credits": 350,
        "history": [{"timestamp": _now_cdmx().strftime("%Y-%m-%d %H:%M:%S"), "task": "Cloud Migration Success", "points": 350, "flare": False}],
        "flare_mode": False,
        "snooze_until": 0
    }
    save_data(new_data)
    send_message("🛡️ **RESTORATION COMPLETE**: Points set to 350 on permanent volume.")

# Then add it to the COMMAND_MAP at the bottom
COMMAND_MAP = {
    # ... your other commands ...
    "restore":          handle_restore,
    "/restore":         handle_restore,
}

COMMAND_MAP = {
    "💊 meds":          handle_meds,
    "meds":             handle_meds,
    "📊 vitals":        handle_vitals,
    "vitals":           handle_vitals,
    "🥤 electrolytes":  handle_electrolytes,
    "electrolytes":     handle_electrolytes,
    "⚔️ quests":       handle_quests,
    "quests":          handle_quests,
    "quest":           handle_quests,
    "done":            handle_quests,
    "✨ sanctuary":     handle_sanctuary,
    "shower":          handle_sanctuary,
    "teeth":           handle_sanctuary,
    "bottle":          handle_sanctuary, 
    "🚨 flare mode":    handle_flare,
    "flare":            handle_flare,
    "📈 status":        handle_status,
    "status":           handle_status,
    "🏁 milestones":    handle_milestones,
    "milestones":       handle_milestones,
    "✏️ custom":        handle_custom,
    "🛠️ fix last":      handle_fix,
    "fix":              handle_fix,
    "📤 export":        handle_export,
    "export":           handle_export,
    "💤 snooze 15m":    handle_snooze,
    "snooze":           handle_snooze,
    "📷 scan monitor":  handle_scan_monitor,
    "scan":             handle_scan_monitor,
    "/emergency_test":  handle_emergency_test,
    "restore":          handle_restore,
    "/restore":         handle_restore,
}


def route(text: str, photo_file_id: str = None) -> None:
    """Route an incoming message to the correct handler."""
    if photo_file_id:
        handle_photo(photo_file_id)
        return

    normalized = text.lower().strip()

    # Exact match first
    if normalized in COMMAND_MAP:
        COMMAND_MAP[normalized](normalized)
        return

    # Prefix match (e.g. "custom Walk the dog 20")
    for key in COMMAND_MAP:
        if normalized.startswith(key):
            COMMAND_MAP[key](normalized)
            return

    # Unknown
    send_message(
        f"❓ I don't know *{text}*.\n\nUse the buttons below or type a command.",
    )
