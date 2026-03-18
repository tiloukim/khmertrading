import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

API_KEY = os.getenv('ALPACA_API_KEY')
SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

# Remove /v2 from base URL if present (SDK adds it automatically)
if BASE_URL.endswith('/v2'):
    BASE_URL = BASE_URL[:-3]

print(f"Connecting to Alpaca Paper Trading...")
print(f"Base URL: {BASE_URL}")

try:
    api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')
    account = api.get_account()

    print(f"\n✅ Connection successful!\n")
    print(f"Account ID:     {account.id}")
    print(f"Status:         {account.status}")
    print(f"Cash:           ${float(account.cash):,.2f}")
    print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
    print(f"Buying Power:   ${float(account.buying_power):,.2f}")
    print(f"Currency:       {account.currency}")
    print(f"Pattern Day Trader: {account.pattern_day_trader}")
    print(f"Trading Blocked:    {account.trading_blocked}")
    print(f"Account Blocked:    {account.account_blocked}")

except Exception as e:
    print(f"\n❌ Connection failed: {e}")
