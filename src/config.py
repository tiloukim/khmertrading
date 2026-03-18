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

if BASE_URL.endswith('/v2'):
    BASE_URL = BASE_URL[:-3]

def get_api():
    return tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')
