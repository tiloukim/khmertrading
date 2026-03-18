import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

API_KEY = os.getenv('ALPACA_API_KEY')
SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')

if BASE_URL.endswith('/v2'):
    BASE_URL = BASE_URL[:-3]

def get_api():
    return tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')
