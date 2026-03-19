"""Yahoo Finance data provider for real-time prices and bars."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Map our symbols to Yahoo Finance tickers
CRYPTO_MAP = {
    'BTC/USD': 'BTC-USD',
    'ETH/USD': 'ETH-USD',
    'SOL/USD': 'SOL-USD',
    'AVAX/USD': 'AVAX-USD',
    'LINK/USD': 'LINK-USD',
    'DOGE/USD': 'DOGE-USD',
}

YF_TIMEFRAME_MAP = {
    '5m': '5m',
    '15m': '15m',
    '1H': '1h',
    '1D': '1d',
}

YF_PERIOD_MAP = {
    '5m': '5d',
    '15m': '5d',
    '1H': '1mo',
    '1D': '3mo',
}


def _to_yf_symbol(symbol):
    """Convert our symbol format to Yahoo Finance format."""
    return CRYPTO_MAP.get(symbol, symbol)


def get_live_price(symbol):
    """Get real-time price for a symbol. Returns dict with price, change, change_pct, prev_close."""
    yf_symbol = _to_yf_symbol(symbol)
    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.fast_info
        price = info.last_price
        prev_close = info.previous_close
        if price and prev_close:
            change = price - prev_close
            change_pct = (change / prev_close) * 100
        else:
            change = 0
            change_pct = 0
        return {
            'price': price,
            'prev_close': prev_close,
            'change': change,
            'change_pct': change_pct,
        }
    except Exception as e:
        print(f"Yahoo Finance error for {symbol}: {e}")
        return None


def get_live_prices(symbols):
    """Get real-time prices for multiple symbols. Returns dict of symbol -> price_info."""
    results = {}
    for symbol in symbols:
        data = get_live_price(symbol)
        if data:
            results[symbol] = data
    return results


def fetch_yahoo_bars(symbol, timeframe='1H', limit=100):
    """Fetch OHLCV bars from Yahoo Finance.

    Returns DataFrame with columns: timestamp, open, high, low, close, volume
    """
    yf_symbol = _to_yf_symbol(symbol)
    yf_tf = YF_TIMEFRAME_MAP.get(timeframe, '1h')
    yf_period = YF_PERIOD_MAP.get(timeframe, '1mo')

    try:
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=yf_period, interval=yf_tf)

        if df.empty:
            return None

        df = df.reset_index()
        # Yahoo uses 'Date' or 'Datetime' depending on interval
        date_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
        df = df.rename(columns={
            date_col: 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
        })
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail(limit)
        return df
    except Exception as e:
        print(f"Yahoo Finance bars error for {symbol}: {e}")
        return None
