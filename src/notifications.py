import requests
import os


def send_telegram(message):
    # type: (str) -> bool
    """Send a message via Telegram bot to all configured chat IDs.
    TELEGRAM_CHAT_ID supports comma-separated IDs (e.g. '123456,-789012')."""
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_ids_raw = os.getenv('TELEGRAM_CHAT_ID', '')
    if not token or not chat_ids_raw:
        print(f"Telegram not configured: token={bool(token)}, chat_id={bool(chat_ids_raw)}")
        return False

    # Support multiple chat IDs separated by commas
    chat_ids = [c.strip() for c in chat_ids_raw.split(',') if c.strip()]

    if len(message) > 4000:
        message = message[:4000] + "\n... (truncated)"

    success = False
    url = "https://api.telegram.org/bot{}/sendMessage".format(token)

    for chat_id in chat_ids:
        try:
            resp = requests.post(url, json={
                'chat_id': chat_id,
                'text': message,
            }, timeout=10)
            print(f"Telegram [{chat_id}]: {resp.status_code}")
            if resp.status_code == 200:
                success = True
            else:
                print(f"Telegram [{chat_id}] error: {resp.text[:200]}")
        except Exception as e:
            print(f"Telegram [{chat_id}] error: {e}")

    return success


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
