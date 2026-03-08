"""
Guardian Bot - Data Layer
Handles all reading/writing of health_credits.json
Replaces the Google Drive dependency with local file storage.
On Railway, this persists as long as the service is running.
"""
import json
import os
import logging
from datetime import datetime
from config import DATA_FILE, TIMEZONE
import pytz

# THE NEW MOUNTED PATH
DATA_FILE = "/app/data/health_credits.json" 

# Ensure the directory exists (Dharma-OS Safety Check)
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

logger = logging.getLogger(__name__)

def _empty_state() -> dict:
    """The default state if no JSON exists."""
    return {
        "total_credits": 0,  # Start at 0, don't hardcode your 350 here!
        "history": [],
        "last_update": datetime.now().isoformat()
        "flare_mode": False,
        "snooze_until": 0,
    }

def load_data() -> dict:
    """Load data from JSON file. Returns empty state if file doesn't exist."""
    try:
        if not os.path.exists(DATA_FILE):
            return _empty_state()
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            # Ensure all keys exist (safe upgrade for older files)
            for key, val in _empty_state().items():
                data.setdefault(key, val)
            return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load data: {e}. Starting fresh.")
        return _empty_state()

def save_data(data: dict) -> bool:
    """Save data to JSON file. Returns True on success."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except IOError as e:
        logger.error(f"Failed to save data: {e}")
        return False

def add_credits(task_name: str, points: int) -> dict:
    """
    Add credits for a task. Applies flare multiplier.
    Returns dict with final_points and new total.
    """
    data = load_data()
    cdmx_tz = pytz.timezone(TIMEZONE)
    now_cdmx = datetime.now(cdmx_tz)

    multiplier = 2 if data.get("flare_mode", False) else 1
    final_points = points * multiplier

    data["total_credits"] += final_points
    data["history"].append({
        "timestamp": now_cdmx.strftime("%Y-%m-%d %H:%M:%S"),
        "task": task_name,
        "points": final_points,
        "flare": data.get("flare_mode", False),
    })

    save_data(data)
    logger.info(f"Credits added: {task_name} (+{final_points}). Total: {data['total_credits']}")

    return {
        "final_points": final_points,
        "total": data["total_credits"],
        "multiplier": multiplier,
        "flare_active": data.get("flare_mode", False),
    }

def deduct_credits(task_name: str, points: int) -> dict:
    """
    Deduct credits. Penalties are suppressed in flare mode.
    Returns dict with result info.
    """
    data = load_data()

    if data.get("flare_mode", False):
        return {"suppressed": True, "reason": "Flare mode active"}

    cdmx_tz = pytz.timezone(TIMEZONE)
    now_cdmx = datetime.now(cdmx_tz)

    data["total_credits"] = max(0, data["total_credits"] - points)
    data["history"].append({
        "timestamp": now_cdmx.strftime("%Y-%m-%d %H:%M:%S"),
        "task": f"PENALTY: {task_name}",
        "points": -points,
        "flare": False,
    })

    save_data(data)
    return {"suppressed": False, "points_deducted": points, "total": data["total_credits"]}

def remove_last_entry() -> dict | None:
    """Remove the last history entry and reverse its points. Returns the removed entry."""
    data = load_data()
    if not data["history"]:
        return None

    last = data["history"].pop()
    data["total_credits"] = max(0, data["total_credits"] - last["points"])
    save_data(data)
    return last

def set_flare_mode(status: bool):
    """Toggle flare mode on or off."""
    data = load_data()
    data["flare_mode"] = status
    save_data(data)

def set_snooze(minutes: int):
    """Snooze scheduled alerts for N minutes."""
    import time
    data = load_data()
    data["snooze_until"] = time.time() + (minutes * 60)
    save_data(data)

def mark_update_processed(update_id: int):
    """Track last processed Telegram update to avoid duplicates."""
    data = load_data()
    data["last_update_id"] = update_id
    save_data(data)

def get_progress_bar(total: int, target: int, length: int = 10) -> str:
    """Generate a text progress bar."""
    ratio = min(total / target, 1.0)
    filled = int(ratio * length)
    bar = "▓" * filled + "░" * (length - filled)
    return f"{bar} {round(ratio * 100)}%"

def export_to_csv() -> str:
    """Export history to CSV. Returns file path."""
    import csv
    data = load_data()
    path = "guardian_export.csv"

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "task", "points", "flare"])
        writer.writeheader()
        for entry in data["history"]:
            writer.writerow(entry)

    logger.info(f"CSV exported: {len(data['history'])} entries")
    return path

def check_meds_taken_today(med_name: str) -> bool:
    """Check if a specific med has been logged today."""
    data = load_data()
    cdmx_tz = pytz.timezone(TIMEZONE)
    today = datetime.now(cdmx_tz).strftime("%Y-%m-%d")
    return any(
        med_name in e["task"] and e["timestamp"].startswith(today)
        for e in data["history"]
    )
