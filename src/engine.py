import os
import sys
import time
import logging
from datetime import datetime

# Ensure src/ is on the path
sys.path.insert(0, os.path.dirname(__file__))

from config import get_api
from strategy import (
    fetch_bars, calculate_rsi, calculate_ma, combined_signal,
    RSI_OVERSOLD, RSI_OVERBOUGHT, MA_PERIOD, PROFIT_TARGET, TRADE_QTY,
)
from execution import market_buy, market_sell
from risk import can_trade, calculate_position_size
from earnings import should_pause_trading

# ── Config ───────────────────────────────────────────────────────────
CHECK_INTERVAL = 300   # 5 minutes
RETRY_INTERVAL = 60    # wait after error
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'live_bot.log')

SYMBOLS = ['NVDA', 'TSLA']  # default watchlist — override via CLI args

# ── Logging ──────────────────────────────────────────────────────────
logger = logging.getLogger('khmertrading')
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

# File handler
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


# ── Analysis + Execution ─────────────────────────────────────────────
def check_and_trade(symbol):
    """Analyze a symbol and execute trades if signals fire."""
    bars = fetch_bars(symbol)
    if bars is None or len(bars) < MA_PERIOD:
        bar_count = len(bars) if bars is not None else 0
        logger.warning("CHECK  %s — not enough data (%d bars, need %d)", symbol, bar_count, MA_PERIOD)
        return

    price = bars['close'].iloc[-1]

    # ── Combined signal ──────────────────────────────────────────
    result = combined_signal(bars)
    signal = result['signal']
    confidence = result['confidence']
    reasons = result['reasons']

    logger.info(
        "CHECK  %s — price=$%.2f  signal=%s  confidence=%.0f%%  reasons=%s",
        symbol, price, signal, confidence, '; '.join(reasons) if reasons else 'none',
    )

    # Also check profit target for existing positions
    if signal == 'HOLD':
        try:
            api = get_api()
            position = api.get_position(symbol)
            entry_price = float(position.avg_entry_price)
            pl_pct = (price - entry_price) / entry_price
            if pl_pct >= PROFIT_TARGET:
                signal = 'SELL'
                confidence = 100.0
                reasons = ["Profit target hit: %.2f%% >= %.0f%%" % (pl_pct * 100, PROFIT_TARGET * 100)]
                logger.info("CHECK  %s — profit target override — signal=SELL confidence=100%%", symbol)
        except Exception:
            pass

    # ── Confidence gate ──────────────────────────────────────────
    if signal != 'HOLD' and confidence < 50:
        logger.info("SKIP   %s — %s signal confidence %.0f%% < 50%%, treating as HOLD", symbol, signal, confidence)
        return

    # ── Earnings check ────────────────────────────────────────────
    if signal != 'HOLD':
        paused, pause_reason = should_pause_trading(symbol)
        if paused:
            logger.info("EARNINGS %s — %s", symbol, pause_reason)
            return

    # ── Execute ──────────────────────────────────────────────────
    if signal == 'BUY':
        # Risk management checks
        api = get_api()
        account = api.get_account()
        equity = float(account.equity)
        allowed, deny_reason = can_trade(equity)
        if not allowed:
            logger.info("RISK   %s — BUY blocked: %s", symbol, deny_reason)
            return

        qty = calculate_position_size(symbol, float(account.portfolio_value))
        logger.info("TRADE  %s — BUY %d shares (confidence=%.0f%%) — %s",
                     symbol, qty, confidence, '; '.join(reasons))
        order = market_buy(symbol, qty)
        if order:
            logger.info("TRADE  %s — BUY FILLED — order_id=%s status=%s", symbol, order.id, order.status)
        else:
            logger.error("TRADE  %s — BUY FAILED", symbol)

    elif signal == 'SELL':
        # Use actual position qty for sells
        api = get_api()
        try:
            position = api.get_position(symbol)
            qty = int(float(position.qty))
        except Exception:
            qty = TRADE_QTY

        logger.info("TRADE  %s — SELL %d shares (confidence=%.0f%%) — %s",
                     symbol, qty, confidence, '; '.join(reasons))
        order = market_sell(symbol, qty)
        if order:
            logger.info("TRADE  %s — SELL FILLED — order_id=%s status=%s", symbol, order.id, order.status)
        else:
            logger.error("TRADE  %s — SELL FAILED", symbol)

    else:
        logger.info("HOLD   %s — no actionable signal", symbol)


# ── Main loop ────────────────────────────────────────────────────────
def run(symbols):
    logger.info("=" * 60)
    logger.info("ENGINE STARTED — symbols=%s  interval=%ds", symbols, CHECK_INTERVAL)
    logger.info("=" * 60)

    while True:
        try:
            logger.info("--- Cycle start ---")
            for symbol in symbols:
                check_and_trade(symbol)
            logger.info("--- Cycle complete — sleeping %ds ---", CHECK_INTERVAL)
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("ENGINE STOPPED by user")
            break

        except Exception as e:
            logger.error("ENGINE ERROR — %s: %s — retrying in %ds", type(e).__name__, e, RETRY_INTERVAL)
            time.sleep(RETRY_INTERVAL)


if __name__ == '__main__':
    # Usage: python engine.py [SYMBOL1 SYMBOL2 ...]
    symbols = sys.argv[1:] if len(sys.argv) > 1 else SYMBOLS
    symbols = [s.upper() for s in symbols]
    run(symbols)
