"""Risk management module for KhmerTrading."""

import math
from config import get_api

# ── Risk Parameters ──────────────────────────────────────────────────
MAX_POSITION_PCT = 0.05      # max 5% of portfolio per trade
MAX_DRAWDOWN_PCT = 0.10      # 10% max drawdown kill switch
MAX_OPEN_POSITIONS = 5


def _is_crypto(symbol):
    # type: (str) -> bool
    return '/' in symbol


def calculate_position_size(symbol, portfolio_value):
    # type: (str, float) -> int
    """Return max shares to buy (floor of portfolio_value * MAX_POSITION_PCT / price).

    Always returns at least 1.
    """
    api = get_api()
    try:
        if _is_crypto(symbol):
            snapshots = api.get_crypto_snapshot(symbol)
            snapshot = snapshots[symbol] if isinstance(snapshots, dict) else snapshots
            price = float(snapshot.latest_trade.p)
        else:
            snapshot = api.get_snapshot(symbol, feed='iex')
            price = float(snapshot.latest_trade.p)
    except Exception:
        # Fallback: cannot determine price, return 1 share
        return 1

    if price <= 0:
        return 1

    shares = int(math.floor(portfolio_value * MAX_POSITION_PCT / price))
    return max(shares, 1)


def check_drawdown(equity, initial_capital=100000):
    # type: (float, float) -> bool
    """Return True if drawdown exceeds MAX_DRAWDOWN_PCT (trading should stop)."""
    if initial_capital <= 0:
        return False
    drawdown = (initial_capital - equity) / initial_capital
    return drawdown > MAX_DRAWDOWN_PCT


def check_position_limit():
    # type: () -> bool
    """Return True if number of open positions >= MAX_OPEN_POSITIONS (no new buys)."""
    api = get_api()
    positions = api.list_positions()
    return len(positions) >= MAX_OPEN_POSITIONS


def can_trade(equity, initial_capital=100000):
    # type: (float, float) -> tuple
    """Check whether trading is allowed.

    Returns (bool, reason_string).  False means trading should be skipped.
    """
    if check_drawdown(equity, initial_capital):
        return (False, "Drawdown %.2f%% exceeds max %.0f%%" % (
            (initial_capital - equity) / initial_capital * 100,
            MAX_DRAWDOWN_PCT * 100,
        ))

    if check_position_limit():
        return (False, "Position limit reached (%d open positions)" % MAX_OPEN_POSITIONS)

    return (True, "OK")
