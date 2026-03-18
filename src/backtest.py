"""
Backtesting engine for the RSI + MA strategy.
Tests against historical Alpaca data and reports performance metrics.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from config import get_api
from strategy import calculate_rsi, calculate_ma

# ── Timeframe mapping (duplicated from strategy.py for independence) ─
TIMEFRAME_MAP = {
    '5m': '5Min',
    '15m': '15Min',
    '1H': '1Hour',
    '1D': '1Day',
}


def fetch_historical_bars(symbol, days=90, timeframe='1H'):
    # type: (str, int, str) -> Optional[pd.DataFrame]
    """Fetch historical bars for backtesting. Handles stocks and crypto."""
    api = get_api()
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    alpaca_tf = TIMEFRAME_MAP.get(timeframe, '1Hour')

    start_str = start.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_str = end.strftime('%Y-%m-%dT%H:%M:%SZ')

    is_crypto = '/' in symbol

    try:
        if is_crypto:
            bars = api.get_crypto_bars(
                symbol,
                alpaca_tf,
                start=start_str,
                end=end_str,
            ).df
        else:
            bars = api.get_bars(
                symbol,
                alpaca_tf,
                start=start_str,
                end=end_str,
                feed='iex',
            ).df
    except Exception as e:
        print("Error fetching bars for %s: %s" % (symbol, e))
        return None

    if bars.empty:
        return None

    bars = bars.reset_index()
    # Crypto bars may have 'symbol' column from multi-index
    if 'symbol' in bars.columns:
        bars = bars.drop(columns=['symbol'])
    bars = bars[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    return bars


def run_backtest(
    symbol,            # type: str
    days=90,           # type: int
    initial_capital=100000,  # type: float
    trade_qty=5,       # type: int
    rsi_period=14,     # type: int
    ma_period=20,      # type: int
    rsi_oversold=30,   # type: float
    rsi_overbought=70, # type: float
    profit_target=0.02,  # type: float
    timeframe='1H',    # type: str
):
    # type: (...) -> Optional[Dict]
    """
    Run a backtest of the RSI+MA strategy on historical data.

    Returns a dict with equity_curve, trades, and metrics, or None on failure.
    """
    bars = fetch_historical_bars(symbol, days=days, timeframe=timeframe)
    if bars is None or len(bars) < ma_period:
        return None

    # Calculate indicators
    bars['rsi'] = calculate_rsi(bars['close'], period=rsi_period)
    bars['ma'] = calculate_ma(bars['close'], period=ma_period)

    # Simulation state
    cash = float(initial_capital)
    position_held = False
    entry_price = 0.0
    trades = []  # type: List[Dict]
    equity_curve = []  # type: List[Dict]

    for idx in range(len(bars)):
        row = bars.iloc[idx]
        price = float(row['close'])
        rsi = float(row['rsi']) if not pd.isna(row['rsi']) else 50.0
        ma = float(row['ma']) if not pd.isna(row['ma']) else price
        ts = row['timestamp']

        if not position_held:
            # BUY signal: RSI oversold AND price below MA
            if rsi < rsi_oversold and price < ma:
                entry_price = price
                cost = price * trade_qty
                if cash >= cost:
                    cash -= cost
                    position_held = True
                    trades.append({
                        'type': 'BUY',
                        'timestamp': str(ts),
                        'price': price,
                        'qty': trade_qty,
                        'rsi': round(rsi, 2),
                    })
        else:
            # SELL signal: RSI overbought OR profit target hit
            pl_pct = (price - entry_price) / entry_price if entry_price > 0 else 0
            if rsi > rsi_overbought or pl_pct >= profit_target:
                cash += price * trade_qty
                profit = (price - entry_price) * trade_qty
                reason = 'profit_target' if pl_pct >= profit_target else 'rsi_overbought'
                trades.append({
                    'type': 'SELL',
                    'timestamp': str(ts),
                    'price': price,
                    'qty': trade_qty,
                    'rsi': round(rsi, 2),
                    'profit': round(profit, 2),
                    'return_pct': round(pl_pct * 100, 2),
                    'reason': reason,
                })
                position_held = False
                entry_price = 0.0

        # Track equity
        equity = cash
        if position_held:
            equity += price * trade_qty
        equity_curve.append({
            'timestamp': str(ts),
            'equity': round(equity, 2),
        })

    metrics = calculate_metrics(trades, equity_curve, initial_capital)

    return {
        'equity_curve': equity_curve,
        'trades': trades,
        'metrics': metrics,
    }


def calculate_metrics(trades, equity_curve, initial_capital):
    # type: (List[Dict], List[Dict], float) -> Dict
    """Calculate backtest performance metrics."""
    final_equity = equity_curve[-1]['equity'] if equity_curve else initial_capital
    total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100

    # Extract sell trades (completed round-trips)
    sell_trades = [t for t in trades if t['type'] == 'SELL']
    total_trades = len(sell_trades)

    if total_trades > 0:
        winning = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = (len(winning) / total_trades) * 100
    else:
        win_rate = 0.0

    # Max drawdown from equity curve
    max_drawdown = 0.0
    if equity_curve:
        equities = [e['equity'] for e in equity_curve]
        peak = equities[0]
        for eq in equities:
            if eq > peak:
                peak = eq
            drawdown = (peak - eq) / peak * 100 if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

    # Sharpe ratio (annualized) from equity curve returns
    sharpe_ratio = 0.0
    if len(equity_curve) > 1:
        equities = pd.Series([e['equity'] for e in equity_curve])
        returns = equities.pct_change().dropna()
        if len(returns) > 1 and returns.std() > 0:
            # Annualize: assume ~252 trading days, ~7 hours per day for 1H bars
            periods_per_year = 252 * 7  # approximate for hourly
            mean_ret = returns.mean()
            std_ret = returns.std()
            sharpe_ratio = (mean_ret / std_ret) * np.sqrt(periods_per_year)

    return {
        'total_return_pct': round(total_return_pct, 2),
        'final_equity': round(final_equity, 2),
        'win_rate': round(win_rate, 2),
        'max_drawdown': round(max_drawdown, 2),
        'total_trades': total_trades,
        'sharpe_ratio': round(sharpe_ratio, 2),
    }
