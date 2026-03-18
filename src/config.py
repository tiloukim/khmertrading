import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


def _get_secret(key, default=''):
    """Read from Streamlit secrets first, then fall back to env vars."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


API_KEY = _get_secret('ALPACA_API_KEY')
SECRET_KEY = _get_secret('ALPACA_SECRET_KEY')
BASE_URL = _get_secret('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

TELEGRAM_BOT_TOKEN = _get_secret('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = _get_secret('TELEGRAM_CHAT_ID', '')
DISCORD_WEBHOOK_URL = _get_secret('DISCORD_WEBHOOK_URL', '')

SMTP_HOST = _get_secret('SMTP_HOST', '')
SMTP_PORT = _get_secret('SMTP_PORT', '587')
SMTP_USER = _get_secret('SMTP_USER', '')
SMTP_PASS = _get_secret('SMTP_PASS', '')
REPORT_EMAIL = _get_secret('REPORT_EMAIL', '')

if BASE_URL.endswith('/v2'):
    BASE_URL = BASE_URL[:-3]

LIVE_BASE_URL = 'https://api.alpaca.markets'


def get_api(live=False):
    url = LIVE_BASE_URL if live else BASE_URL
    return tradeapi.REST(API_KEY, SECRET_KEY, url, api_version='v2')
