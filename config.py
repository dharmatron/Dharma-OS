"""
Guardian Bot - Configuration
Load all secrets from environment variables (never hardcode tokens!)
"""
import os

# --- TELEGRAM ---
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# --- GOALS ---
TARGET_GOAL = 2500

# --- DATA ---
DATA_FILE = os.environ.get("DATA_FILE", "health_credits.json")

# --- TIMEZONE ---
TIMEZONE = "America/Mexico_City"

# --- MEDICATION SCHEDULE ---
# Format: "HH:MM": "Med name as it will appear in logs"
MED_SCHEDULE = {
    "06:00": "Gabapentin + Duloxetine + Ketotifen",
    "08:00": "Fludrocortison + Ivabradine + Baclofen + Methylphenidate + Electrolytes",
    "14:00": "Gabapentin + Ketotifen",
    "20:00": "Ivabradine + Levocetirizine + Baclofen",
    "22:00": "Gabapentin + Duloxetine + Ketotifen",
}

# --- POINTS CONFIG ---
POINTS = {
    "meds_on_time":     30,
    "meds_off_schedule": 15,
    "vitals":           10,
    "electrolytes":     15,
    "custom":           20,
    "system_init":      50,
    "auto_ocr":         30,
}

# --- GRACE PERIOD (minutes) ---
GRACE_WARNING  = 5    # After this: penalty applied
GRACE_CUTOFF   = 30   # After this: no points

# --- ALERT LEVELS (for future monitor bridge) ---
# These map to the MCAS early warning stages we designed
ALERT_LEVELS = {
    "level_1": "⚠️ Heads up — early signs detected. Stay near your phones.",
    "level_2": "🚨 URGENT: Significant parameter changes. Please check in.",
    "level_3": "🆘 EMERGENCY: Critical readings. Call now.",
}

# --- EMERGENCY CIRCLE ---
# Add Telegram chat IDs of people to notify during emergencies
# Leave empty until you're ready to set this up
EMERGENCY_CIRCLE = []
