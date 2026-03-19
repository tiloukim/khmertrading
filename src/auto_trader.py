"""Auto-trading bot that runs on each page refresh.
Checks signals and executes trades based on strategy."""

import streamlit as st
from datetime import datetime
from strategy import combined_signal, MA_PERIOD
from yahoo_data import fetch_yahoo_bars
from execution import market_buy, market_sell, is_crypto
from notifications import send_telegram
from config import get_api


def check_and_trade(symbols, trade_qty_stocks=5, trade_qty_crypto=0.01, dry_run=False):
    """Check signals for all symbols and execute trades if conditions are met.

    Returns list of actions taken.
    """
    actions = []
    api = get_api()

    # Get current positions
    try:
        positions = {p.symbol: p for p in api.list_positions()}
    except Exception:
        positions = {}

    for symbol in symbols:
        try:
            # Fetch bars
            bars = fetch_yahoo_bars(symbol, timeframe='1H')
            if bars is None or len(bars) < MA_PERIOD:
                continue

            # Get signal
            result = combined_signal(bars)
            signal = result['signal']
            confidence = result['confidence']
            reasons = result['reasons']

            # Only act on high-confidence signals
            if confidence < 50:
                continue

            # Convert symbol for position lookup (BTC/USD -> BTCUSD)
            pos_symbol = symbol.replace('/', '')
            has_position = pos_symbol in positions
            crypto = is_crypto(symbol)
            qty = trade_qty_crypto if crypto else trade_qty_stocks

            action = None

            if signal == 'BUY' and not has_position:
                # Buy if we don't already have a position
                if not dry_run:
                    try:
                        order = market_buy(symbol, qty)
                        if order:
                            action = f"🟢 AUTO BUY {qty}x {symbol} (confidence: {confidence:.0f}%)"
                    except Exception as e:
                        action = f"⚠️ BUY {symbol} failed: {e}"
                else:
                    action = f"🟢 [DRY RUN] Would BUY {qty}x {symbol} (confidence: {confidence:.0f}%)"

            elif signal == 'SELL' and has_position:
                # Sell if we have a position
                pos = positions[pos_symbol]
                sell_qty = float(pos.qty) if crypto else int(float(pos.qty))
                if not dry_run:
                    try:
                        order = market_sell(symbol, sell_qty)
                        if order:
                            pl = float(pos.unrealized_pl)
                            action = f"🔴 AUTO SELL {sell_qty}x {symbol} (P/L: ${pl:+,.2f})"
                    except Exception as e:
                        action = f"⚠️ SELL {symbol} failed: {e}"
                else:
                    action = f"🔴 [DRY RUN] Would SELL {sell_qty}x {symbol} (confidence: {confidence:.0f}%)"

            if action:
                actions.append(action)

        except Exception as e:
            continue

    # Send Telegram notification if any trades were made
    if actions:
        msg = "🤖 KhmerTrading AI Bot\n"
        msg += f"📅 {datetime.now().strftime('%b %d, %I:%M %p')}\n\n"
        for a in actions:
            msg += f"{a}\n"
        msg += "\n— Auto Trading"
        try:
            send_telegram(msg)
        except Exception:
            pass

    return actions


def render_auto_trade_controls():
    """Render auto-trading controls in the sidebar. Returns True if auto-trade is active."""

    with st.expander("🤖 Auto Trading", expanded=False):
        st.caption("Let the AI bot trade automatically based on signals")

        # Initialize state
        if 'auto_trade_enabled' not in st.session_state:
            st.session_state['auto_trade_enabled'] = False
        if 'auto_trade_mode' not in st.session_state:
            st.session_state['auto_trade_mode'] = 'Dry Run'

        mode = st.selectbox(
            "Mode",
            ["Dry Run (no real trades)", "Live Auto Trading"],
            key="auto_trade_mode_select",
        )

        stock_symbols = st.multiselect(
            "Stock symbols",
            ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOG", "META", "AMD"],
            default=["NVDA", "TSLA", "AAPL"],
            key="auto_stocks",
        )

        crypto_symbols = st.multiselect(
            "Crypto symbols",
            ["BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD"],
            default=["BTC/USD", "ETH/USD"],
            key="auto_crypto",
        )

        c1, c2 = st.columns(2)
        with c1:
            stock_qty = st.number_input("Stock qty", min_value=1, value=5, key="auto_stock_qty")
        with c2:
            crypto_qty = st.number_input("Crypto qty", min_value=0.001, value=0.01, step=0.01, format="%.3f", key="auto_crypto_qty")

        if mode == "Live Auto Trading":
            st.warning("Live mode will execute REAL trades!")
            confirm = st.checkbox("I understand the risks", key="auto_confirm")
        else:
            confirm = True

        enabled = st.toggle("Enable Auto Trading", value=st.session_state.get('auto_trade_enabled', False), key="auto_toggle")
        st.session_state['auto_trade_enabled'] = enabled

        dry_run = "Dry Run" in mode

        if enabled and confirm:
            if dry_run:
                st.info("🔵 Auto Trading ON (Dry Run)")
            else:
                st.success("🟢 Auto Trading ON (Live)")

            # Run the check
            all_symbols = stock_symbols + crypto_symbols
            if all_symbols:
                actions = check_and_trade(
                    all_symbols,
                    trade_qty_stocks=stock_qty,
                    trade_qty_crypto=crypto_qty,
                    dry_run=dry_run,
                )
                if actions:
                    st.markdown("**Recent actions:**")
                    for a in actions:
                        st.caption(a)
                else:
                    st.caption("No signals triggered. Checking again on next refresh.")
        elif enabled and not confirm:
            st.error("Check the risk confirmation box to enable live trading.")
            st.session_state['auto_trade_enabled'] = False

    return st.session_state.get('auto_trade_enabled', False)
