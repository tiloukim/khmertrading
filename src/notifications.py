import requests
import os


def send_telegram(message):
    # type: (str) -> bool
    """Send a message via Telegram bot. Returns True on success, False on failure."""
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        print(f"Telegram not configured: token={bool(token)}, chat_id={bool(chat_id)}")
        return False
    try:
        url = "https://api.telegram.org/bot{}/sendMessage".format(token)
        # Telegram max message is 4096 chars, truncate if needed
        if len(message) > 4000:
            message = message[:4000] + "\n... (truncated)"
        resp = requests.post(url, json={
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
        }, timeout=10)
        print(f"Telegram response: {resp.status_code} {resp.text[:300]}")
        if resp.status_code != 200:
            # Retry without parse_mode in case HTML causes issues
            resp = requests.post(url, json={
                'chat_id': chat_id,
                'text': message,
            }, timeout=10)
            print(f"Telegram retry: {resp.status_code} {resp.text[:300]}")
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
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
