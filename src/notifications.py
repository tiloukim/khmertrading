import requests
import os


TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')


def send_telegram(message):
    # type: (str) -> bool
    """Send a message via Telegram bot. Returns True on success, False on failure."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = "https://api.telegram.org/bot{}/sendMessage".format(TELEGRAM_BOT_TOKEN)
        resp = requests.post(url, json={
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
        }, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def send_discord(message):
    # type: (str) -> bool
    """Send a message via Discord webhook. Returns True on success, False on failure."""
    if not DISCORD_WEBHOOK_URL:
        return False
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json={
            'content': message,
        }, timeout=10)
        return resp.status_code in (200, 204)
    except Exception:
        return False


def notify(message):
    # type: (str) -> None
    """Send notification to all configured channels. Never crashes the app."""
    print(message)
    try:
        send_telegram(message)
    except Exception:
        pass
    try:
        send_discord(message)
    except Exception:
        pass
