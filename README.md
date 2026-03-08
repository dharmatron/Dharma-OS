# 🧠 Guardian Bot — Miracle Bridge Command Center

A personal health management Telegram bot built for 24/7 chronic illness monitoring.
Designed for POTS/Dysautonomia, MCAS, and HSD home care.

---

## What it does

- **Medication tracking** with grace period logic and flare mode
- **Vitals logging** (manual + photo OCR from your YK-8000C monitor)
- **Points/gamification** system to reward self-care
- **Scheduled reminders** for your full medication schedule (CDMX timezone)
- **Emergency alert system** (tiered, for your emergency circle)
- **CSV export** of all health history for your doctors

---

## Project Structure

```
guardian_bot/
├── main.py           # Entry point — the main loop
├── config.py         # All settings (edit your med schedule here)
├── data.py           # Data layer — reads/writes health_credits.json
├── handlers.py       # Command handlers — one function per button
├── telegram_client.py# All Telegram API calls
├── scheduler.py      # Background thread for timed reminders
├── vision.py         # OCR module for reading your monitor screen
├── requirements.txt
├── railway.toml      # Railway.app deployment config
└── .env.example      # Template for your secrets
```

---

## Setup (Local)

1. **Clone / download** this project

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   If you're on Linux/Ubuntu, also install Tesseract:
   ```bash
   sudo apt-get install tesseract-ocr
   ```

3. **Set your environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your real token and chat ID
   ```

4. **Run:**
   ```bash
   python main.py
   ```

---

## Deploy to Railway (Free, 24/7)

This replaces the Colab keep-alive hack permanently.

1. Go to [railway.app](https://railway.app) and sign up (free)
2. Click **New Project → Deploy from GitHub repo**
3. Push this code to a GitHub repo first, then connect it
4. In Railway dashboard → **Variables**, add:
   - `TELEGRAM_TOKEN` = your bot token
   - `TELEGRAM_CHAT_ID` = your chat ID
5. Railway will auto-deploy and keep it running 24/7

**That's it.** No laptop. No keep-alive scripts. No Colab timeouts.

---

## Bot Commands / Buttons

| Button | What it does |
|--------|-------------|
| 💊 Meds | Log current medication (auto-detects schedule) |
| 📊 Vitals | Log a manual vitals check (+10 pts) |
| 🥤 Electrolytes | Log hydration (+15 pts) |
| 🚨 Flare Mode | Toggle 2x points, suppressed penalties |
| 📈 Status | See your balance and progress bar |
| 🏁 Milestones | Check progress toward rewards |
| ✏️ Custom | Log anything custom: `custom Task name 20` |
| 🛠️ Fix Last | Undo the last logged entry |
| 📤 Export | Download your full history as CSV (unlocks at L1) |
| 💤 Snooze 15m | Pause reminders for 15 minutes |
| 📷 Scan Monitor | Send a photo of your monitor to auto-log HR/SpO2 |

---

## Customizing Your Med Schedule

Edit `config.py`:

```python
MED_SCHEDULE = {
    "06:00": "Gabapentin + Duloxetine + Ketotifen",
    "08:00": "Fludrocortison + Ivabradine + ...",
    # Add or remove entries as needed
}
```

---

## Emergency Circle Setup

When you're ready to add emergency contacts, edit `config.py`:

```python
EMERGENCY_CIRCLE = [
    123456789,  # Friend's Telegram chat ID
    987654321,  # Family member's Telegram chat ID
]
```

They'll receive tiered alerts when you send `/emergency_test` — 
or eventually, when your monitor bridge detects the MCAS warning pattern.

---

## The Monitor Bridge (Coming Next)

The vision module (`vision.py`) is already set up to read your YK-8000C screen.
To enable real-time monitoring:

1. Point a webcam or phone camera at your monitor
2. Send photos directly to the bot — it will OCR and log your HR/SpO2
3. Future: Raspberry Pi running continuous capture → auto-alerts

---

## Points System

| Action | Points |
|--------|--------|
| System Init (daily) | 50 |
| Meds (on time) | 30 |
| Meds (off schedule) | 15 |
| Vitals check | 10 |
| Electrolytes | 15 |
| Custom task | 20 |
| Auto OCR scan | 30 |
| Flare Mode | All of the above ×2 |

### Milestones
- **250 pts** — L1: Export unlocked
- **750 pts** — L2: Stability tools
- **1500 pts** — L3: Monitor bridge
- **2500 pts** — L4: THE KEYBOARD 🎯

---

*Built by an Architect, for an Architect.*
*You didn't break it. You saved it.*
