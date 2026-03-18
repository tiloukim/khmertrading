import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import get_api
from execution import market_buy, market_sell, cancel_all_orders

# ── Strategy Parameters ──────────────────────────────────────────────
RSI_PERIOD = 14
MA_PERIOD = 20
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
PROFIT_TARGET = 0.02  # 2% profit target
CHECK_INTERVAL = 300  # 5 minutes in seconds
TRADE_QTY = 5         # Shares per trade


def is_crypto(symbol: str) -> bool:
    """Check if a symbol is a crypto pair."""
    return '/' in symbol


TIMEFRAME_MAP = {
    '5m': '5Min',
    '15m': '15Min',
    '1H': '1Hour',
    '1D': '1Day',
}

TIMEFRAME_LOOKBACK = {
    '5m': 1,
    '15m': 2,
    '1H': 5,
    '1D': 60,
}


def fetch_bars(symbol, hours=20, timeframe='1H'):
    """Fetch price bars from Alpaca. Routes to crypto or stock endpoint."""
    if is_crypto(symbol):
        return fetch_crypto_bars(symbol, hours, timeframe)
    return fetch_stock_bars(symbol, hours, timeframe)


def fetch_stock_bars(symbol, hours=20, timeframe='1H'):
    """Fetch stock price bars from Alpaca with configurable timeframe."""
    api = get_api()
    end = datetime.utcnow()
    alpaca_tf = TIMEFRAME_MAP.get(timeframe, '1Hour')
    lookback_days = TIMEFRAME_LOOKBACK.get(timeframe, 5)
    start = end - timedelta(days=lookback_days)

    bars = api.get_bars(
        symbol,
        alpaca_tf,
        start=start.strftime('%Y-%m-%dT%H:%M:%SZ'),
        end=end.strftime('%Y-%m-%dT%H:%M:%SZ'),
        limit=hours + 10,
        feed='iex',
    ).df

    if bars.empty:
        print(f"⚠️  No data returned for {symbol}")
        return None

    bars = bars.reset_index()
    bars = bars[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail(hours)
    return bars


def fetch_crypto_bars(symbol, hours=48, timeframe='1H'):
    """Fetch crypto price bars from Alpaca with configurable timeframe."""
    api = get_api()
    end = datetime.utcnow()
    alpaca_tf = TIMEFRAME_MAP.get(timeframe, '1Hour')
    lookback_days = TIMEFRAME_LOOKBACK.get(timeframe, 5)
    start = end - timedelta(days=lookback_days)

    bars = api.get_crypto_bars(
        symbol,
        alpaca_tf,
        start=start.strftime('%Y-%m-%dT%H:%M:%SZ'),
        end=end.strftime('%Y-%m-%dT%H:%M:%SZ'),
        limit=hours + 10,
    ).df

    if bars.empty:
        print(f"⚠️  No crypto data returned for {symbol}")
        return None

    bars = bars.reset_index()
    # Crypto bars have 'symbol' column from multi-index — drop it if present
    if 'symbol' in bars.columns:
        bars = bars.drop(columns=['symbol'])
    bars = bars[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail(hours)
    return bars


def calculate_rsi(prices, period=RSI_PERIOD):
    """Calculate Relative Strength Index."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_ma(prices, period=MA_PERIOD):
    """Calculate Simple Moving Average."""
    return prices.rolling(window=period).mean()


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator. Returns DataFrame with macd_line, signal_line, histogram."""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    result = pd.DataFrame({
        'macd_line': macd_line,
        'signal_line': signal_line,
        'histogram': histogram,
    })
    return result


def calculate_bollinger(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands. Returns DataFrame with upper, middle, lower."""
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    result = pd.DataFrame({
        'upper': upper,
        'middle': middle,
        'lower': lower,
    })
    return result


def calculate_vwap(bars_df):
    """Calculate VWAP using typical price (H+L+C)/3 * volume."""
    typical_price = (bars_df['high'] + bars_df['low'] + bars_df['close']) / 3.0
    cum_tp_vol = (typical_price * bars_df['volume']).cumsum()
    cum_vol = bars_df['volume'].cumsum()
    vwap = cum_tp_vol / cum_vol
    return vwap


def combined_signal(bars):
    """Compute a combined BUY/SELL/HOLD signal from RSI, MA, MACD, Bollinger Bands.

    Parameters
    ----------
    bars : pd.DataFrame
        Must contain columns: timestamp, open, high, low, close, volume.

    Returns
    -------
    dict  {'signal': str, 'confidence': float, 'reasons': list[str]}
    """
    prices = bars['close']

    # ── Indicators ────────────────────────────────────────────────
    rsi = calculate_rsi(prices)
    ma = calculate_ma(prices)
    macd = calculate_macd(prices)
    bb = calculate_bollinger(prices)

    current_price = prices.iloc[-1]
    current_rsi = rsi.iloc[-1]
    current_ma = ma.iloc[-1]
    hist_curr = macd['histogram'].iloc[-1]
    hist_prev = macd['histogram'].iloc[-2] if len(macd) > 1 else hist_curr
    bb_lower = bb['lower'].iloc[-1]
    bb_upper = bb['upper'].iloc[-1]

    buy_score = 0
    sell_score = 0
    reasons = []  # type: list

    # ── BUY conditions ────────────────────────────────────────────
    if not pd.isna(current_rsi) and current_rsi < 30:
        buy_score += 30
        reasons.append("RSI %.1f < 30 (oversold)" % current_rsi)

    if not pd.isna(current_ma) and current_price < current_ma:
        buy_score += 20
        reasons.append("Price $%.2f below MA $%.2f" % (current_price, current_ma))

    if not (pd.isna(hist_curr) or pd.isna(hist_prev)) and hist_curr > hist_prev:
        buy_score += 25
        reasons.append("MACD histogram turning positive (%.4f > %.4f)" % (hist_curr, hist_prev))

    if not pd.isna(bb_lower) and bb_lower > 0:
        pct_from_lower = abs(current_price - bb_lower) / bb_lower
        if pct_from_lower <= 0.01:
            buy_score += 25
            reasons.append("Price near lower Bollinger band ($%.2f)" % bb_lower)

    # ── SELL conditions ───────────────────────────────────────────
    if not pd.isna(current_rsi) and current_rsi > 70:
        sell_score += 30
        reasons.append("RSI %.1f > 70 (overbought)" % current_rsi)

    if not pd.isna(current_ma) and current_price > current_ma:
        sell_score += 20
        reasons.append("Price $%.2f above MA $%.2f" % (current_price, current_ma))

    if not (pd.isna(hist_curr) or pd.isna(hist_prev)) and hist_curr < hist_prev:
        sell_score += 25
        reasons.append("MACD histogram turning negative (%.4f < %.4f)" % (hist_curr, hist_prev))

    if not pd.isna(bb_upper) and bb_upper > 0:
        pct_from_upper = abs(current_price - bb_upper) / bb_upper
        if pct_from_upper <= 0.01:
            sell_score += 25
            reasons.append("Price near upper Bollinger band ($%.2f)" % bb_upper)

    # ── Determine signal ──────────────────────────────────────────
    if buy_score > sell_score and buy_score >= 40:
        signal = 'BUY'
        confidence = min(buy_score, 100)
    elif sell_score > buy_score and sell_score >= 40:
        signal = 'SELL'
        confidence = min(sell_score, 100)
    else:
        signal = 'HOLD'
        confidence = 0.0

    return {
        'signal': signal,
        'confidence': float(confidence),
        'reasons': reasons,
    }


def momentum_signal(bars):
    """Compute a Momentum signal based on Rate of Change and volume trend.

    Parameters
    ----------
    bars : pd.DataFrame
        Must contain columns: close, volume.

    Returns
    -------
    dict  {'signal': str, 'confidence': float, 'reasons': list}
    """
    prices = bars['close']
    volumes = bars['volume']
    reasons = []

    if len(prices) < 11:
        return {'signal': 'HOLD', 'confidence': 0.0, 'reasons': ['Not enough data for momentum']}

    current_price = prices.iloc[-1]
    price_10_ago = prices.iloc[-11]
    roc = (current_price - price_10_ago) / price_10_ago * 100

    vol_avg_20 = volumes.tail(20).mean()
    current_vol = volumes.iloc[-1]
    vol_above_avg = current_vol > vol_avg_20

    signal = 'HOLD'
    confidence = 0.0

    if roc > 3 and vol_above_avg:
        signal = 'BUY'
        confidence = min(abs(roc) * 5, 100)
        reasons.append("ROC %.2f%% > 3%% (strong upward momentum)" % roc)
        reasons.append("Volume %s above 20-bar avg %s" % (
            "{:,.0f}".format(current_vol), "{:,.0f}".format(vol_avg_20)))
    elif roc < -3 and vol_above_avg:
        signal = 'SELL'
        confidence = min(abs(roc) * 5, 100)
        reasons.append("ROC %.2f%% < -3%% (strong downward momentum)" % roc)
        reasons.append("Volume %s above 20-bar avg %s" % (
            "{:,.0f}".format(current_vol), "{:,.0f}".format(vol_avg_20)))
    else:
        if abs(roc) <= 3:
            reasons.append("ROC %.2f%% within neutral zone (-3%% to 3%%)" % roc)
        if not vol_above_avg:
            reasons.append("Volume %s below 20-bar avg %s" % (
                "{:,.0f}".format(current_vol), "{:,.0f}".format(vol_avg_20)))

    return {'signal': signal, 'confidence': float(confidence), 'reasons': reasons}


def mean_reversion_signal(bars):
    """Compute a Mean Reversion signal based on z-score from 20-MA.

    Parameters
    ----------
    bars : pd.DataFrame
        Must contain columns: close.

    Returns
    -------
    dict  {'signal': str, 'confidence': float, 'reasons': list}
    """
    prices = bars['close']
    reasons = []

    if len(prices) < 20:
        return {'signal': 'HOLD', 'confidence': 0.0, 'reasons': ['Not enough data for mean reversion']}

    ma_20 = prices.rolling(window=20).mean()
    std_20 = prices.rolling(window=20).std()

    current_price = prices.iloc[-1]
    current_ma = ma_20.iloc[-1]
    current_std = std_20.iloc[-1]

    if pd.isna(current_ma) or pd.isna(current_std) or current_std == 0:
        return {'signal': 'HOLD', 'confidence': 0.0, 'reasons': ['Insufficient variance for z-score']}

    z_score = (current_price - current_ma) / current_std

    signal = 'HOLD'
    confidence = 0.0

    if z_score < -2:
        signal = 'BUY'
        confidence = min(abs(z_score) * 25, 100)
        reasons.append("Z-score %.2f < -2 (price 2+ std devs below mean)" % z_score)
        reasons.append("Price $%.2f vs 20-MA $%.2f" % (current_price, current_ma))
    elif z_score > 2:
        signal = 'SELL'
        confidence = min(abs(z_score) * 25, 100)
        reasons.append("Z-score %.2f > 2 (price 2+ std devs above mean)" % z_score)
        reasons.append("Price $%.2f vs 20-MA $%.2f" % (current_price, current_ma))
    else:
        reasons.append("Z-score %.2f within normal range (-2 to 2)" % z_score)

    return {'signal': signal, 'confidence': float(confidence), 'reasons': reasons}


def breakout_signal(bars):
    """Compute a Breakout signal based on 20-bar high/low with volume confirmation.

    Parameters
    ----------
    bars : pd.DataFrame
        Must contain columns: close, high, low, volume.

    Returns
    -------
    dict  {'signal': str, 'confidence': float, 'reasons': list}
    """
    prices = bars['close']
    highs = bars['high']
    lows = bars['low']
    volumes = bars['volume']
    reasons = []

    if len(prices) < 21:
        return {'signal': 'HOLD', 'confidence': 0.0, 'reasons': ['Not enough data for breakout']}

    current_price = prices.iloc[-1]
    # 20-bar high/low excluding the current bar
    high_20 = highs.iloc[-21:-1].max()
    low_20 = lows.iloc[-21:-1].min()

    vol_avg_20 = volumes.tail(20).mean()
    current_vol = volumes.iloc[-1]
    vol_above_avg = current_vol > vol_avg_20

    signal = 'HOLD'
    confidence = 0.0

    if current_price > high_20 and vol_above_avg:
        signal = 'BUY'
        breakout_pct = (current_price - high_20) / high_20 * 100
        confidence = min(breakout_pct * 20 + 40, 100)
        reasons.append("Price $%.2f broke above 20-bar high $%.2f (+%.2f%%)" % (
            current_price, high_20, breakout_pct))
        reasons.append("Volume confirmed: %s above avg %s" % (
            "{:,.0f}".format(current_vol), "{:,.0f}".format(vol_avg_20)))
    elif current_price < low_20:
        signal = 'SELL'
        breakdown_pct = (low_20 - current_price) / low_20 * 100
        confidence = min(breakdown_pct * 20 + 40, 100)
        reasons.append("Price $%.2f broke below 20-bar low $%.2f (-%.2f%%)" % (
            current_price, low_20, breakdown_pct))
    else:
        reasons.append("Price $%.2f within 20-bar range ($%.2f — $%.2f)" % (
            current_price, low_20, high_20))
        if not vol_above_avg:
            reasons.append("Volume below average — no breakout confirmation")

    return {'signal': signal, 'confidence': float(confidence), 'reasons': reasons}


def analyze(symbol, dry_run=True):
    """Analyze a symbol and return buy/sell/hold signal."""
    print(f"\n{'─' * 60}")
    print(f"  Analyzing {symbol}...")
    print(f"{'─' * 60}")

    bars = fetch_bars(symbol)
    if bars is None or len(bars) < MA_PERIOD:
        print(f"  ❌ Not enough data for {symbol} ({len(bars) if bars is not None else 0} bars, need {MA_PERIOD})")
        return 'HOLD', None

    # Calculate indicators
    bars['rsi'] = calculate_rsi(bars['close'])
    bars['ma'] = calculate_ma(bars['close'])

    # Current values
    current_price = bars['close'].iloc[-1]
    current_rsi = bars['rsi'].iloc[-1]
    current_ma = bars['ma'].iloc[-1]
    prev_rsi = bars['rsi'].iloc[-2] if len(bars) > 1 else current_rsi

    # Price vs MA
    price_vs_ma = ((current_price - current_ma) / current_ma) * 100

    # Display analysis
    print(f"\n  Current Price:    ${current_price:,.2f}")
    print(f"  20-Period MA:     ${current_ma:,.2f} ({price_vs_ma:+.2f}% from MA)")
    print(f"  RSI (14):         {current_rsi:.1f}")
    print(f"  Previous RSI:     {prev_rsi:.1f}")
    print(f"  Volume (last):    {bars['volume'].iloc[-1]:,.0f}")

    # Price history (last 5 bars)
    print(f"\n  Last 5 hourly closes:")
    for _, row in bars.tail(5).iterrows():
        ts = str(row['timestamp'])[:16]
        print(f"    {ts}  ${row['close']:,.2f}  RSI: {row['rsi']:.1f}" if not pd.isna(row['rsi']) else f"    {ts}  ${row['close']:,.2f}  RSI: N/A")

    # ── Decision Logic ────────────────────────────────────────────
    signal = 'HOLD'
    reason = ''

    # BUY: RSI oversold AND price below MA
    if current_rsi < RSI_OVERSOLD and current_price < current_ma:
        signal = 'BUY'
        reason = f"RSI {current_rsi:.1f} < {RSI_OVERSOLD} (oversold) AND price below MA"

    # SELL: RSI overbought
    elif current_rsi > RSI_OVERBOUGHT:
        signal = 'SELL'
        reason = f"RSI {current_rsi:.1f} > {RSI_OVERBOUGHT} (overbought)"

    # Check profit target for existing positions
    if signal == 'HOLD':
        api = get_api()
        try:
            position = api.get_position(symbol)
            entry_price = float(position.avg_entry_price)
            pl_pct = (current_price - entry_price) / entry_price
            if pl_pct >= PROFIT_TARGET:
                signal = 'SELL'
                reason = f"Profit target hit: {pl_pct*100:.2f}% >= {PROFIT_TARGET*100:.0f}%"
            elif pl_pct > 0:
                reason = f"In profit ({pl_pct*100:.2f}%) but below {PROFIT_TARGET*100:.0f}% target"
            else:
                reason = f"Position at {pl_pct*100:.2f}%, waiting for recovery"
        except:
            # No position held
            if current_rsi < 40 and current_price < current_ma:
                reason = f"RSI {current_rsi:.1f} trending low, approaching buy zone"
            elif current_rsi > 60:
                reason = f"RSI {current_rsi:.1f} is elevated, waiting for pullback"
            else:
                reason = f"RSI {current_rsi:.1f} is neutral, no clear signal"

    # Display signal
    icons = {'BUY': '🟢', 'SELL': '🔴', 'HOLD': '🟡'}
    print(f"\n  {icons[signal]} Signal: {signal}")
    print(f"  Reason: {reason}")

    # Execute if not dry run
    if not dry_run and signal != 'HOLD':
        print(f"\n  ⚡ EXECUTING: {signal} {TRADE_QTY} x {symbol}")
        if signal == 'BUY':
            market_buy(symbol, TRADE_QTY)
        elif signal == 'SELL':
            market_sell(symbol, TRADE_QTY)
    elif dry_run and signal != 'HOLD':
        print(f"\n  📋 DRY RUN: Would {signal} {TRADE_QTY} x {symbol} (no order placed)")

    return signal, {
        'price': current_price,
        'rsi': current_rsi,
        'ma': current_ma,
        'price_vs_ma': price_vs_ma,
    }


def run_loop(symbols: list, dry_run: bool = False):
    """Run the strategy in a loop, checking every 5 minutes."""
    print("=" * 60)
    print("  KHMERTRADING AI Strategy Bot")
    print(f"  Symbols: {', '.join(symbols)}")
    print(f"  Mode: {'DRY RUN' if dry_run else '🔴 LIVE TRADING'}")
    print(f"  Check interval: {CHECK_INTERVAL // 60} minutes")
    print(f"  RSI Buy < {RSI_OVERSOLD} | RSI Sell > {RSI_OVERBOUGHT}")
    print(f"  Profit Target: {PROFIT_TARGET * 100:.0f}%")
    print(f"  Trade Size: {TRADE_QTY} shares")
    print("=" * 60)

    try:
        while True:
            print(f"\n⏰ Check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            for symbol in symbols:
                analyze(symbol, dry_run=dry_run)

            print(f"\n💤 Sleeping {CHECK_INTERVAL // 60} minutes until next check...")
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\n🛑 Strategy bot stopped by user.")
        print(f"   Cancelling any open orders...")
        cancel_all_orders()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'live':
        # Live mode: python strategy.py live NVDA TSLA
        symbols = sys.argv[2:] if len(sys.argv) > 2 else ['NVDA', 'TSLA']
        run_loop(symbols, dry_run=False)
    elif len(sys.argv) > 1 and sys.argv[1] == 'loop':
        # Dry run loop: python strategy.py loop NVDA TSLA
        symbols = sys.argv[2:] if len(sys.argv) > 2 else ['NVDA', 'TSLA']
        run_loop(symbols, dry_run=True)
    else:
        # One-time dry run analysis
        symbols = sys.argv[1:] if len(sys.argv) > 1 else ['NVDA']
        for s in symbols:
            analyze(s, dry_run=True)
        print()
