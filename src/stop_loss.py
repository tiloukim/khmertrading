"""Stop-loss guardian — automatically exits positions that drop below threshold.
Rule #1: If a trade goes down more than X%, exit automatically. No stop-loss = gambling."""

import streamlit as st
from datetime import datetime
from config import get_api
from execution import market_sell, is_crypto
from notifications import send_telegram


def check_stop_losses(stop_loss_pct=5.0, dry_run=False):
    """Check all open positions and sell any that have lost more than stop_loss_pct%.

    Parameters
    ----------
    stop_loss_pct : float
        Maximum allowed loss percentage (default 5%)
    dry_run : bool
        If True, only report what would be sold

    Returns
    -------
    list of actions taken
    """
    api = get_api()
    actions = []

    try:
        positions = api.list_positions()
    except Exception as e:
        print(f"Stop-loss check failed: {e}")
        return actions

    for pos in positions:
        try:
            symbol = pos.symbol
            pl_pct = float(pos.unrealized_plpc) * 100  # e.g. -5.2
            pl_dollars = float(pos.unrealized_pl)
            qty = float(pos.qty)
            entry = float(pos.avg_entry_price)
            current = float(pos.current_price)

            # Check if loss exceeds threshold
            if pl_pct <= -stop_loss_pct:
                # Convert BTCUSD back to BTC/USD for sell
                sell_symbol = symbol
                if not '/' in symbol and symbol.endswith('USD') and len(symbol) > 3:
                    sell_symbol = symbol[:-3] + '/USD'

                crypto = '/' in sell_symbol

                if not dry_run:
                    try:
                        sell_qty = qty if crypto else int(qty)
                        order = market_sell(sell_symbol, sell_qty)
                        if order:
                            action = (
                                f"🛑 STOP-LOSS TRIGGERED\n"
                                f"Symbol: {symbol}\n"
                                f"Loss: {pl_pct:+.2f}% (${pl_dollars:+,.2f})\n"
                                f"Entry: ${entry:,.2f} → Current: ${current:,.2f}\n"
                                f"Sold {sell_qty} shares/coins"
                            )
                            actions.append(action)
                    except Exception as e:
                        actions.append(f"⚠️ Stop-loss SELL failed for {symbol}: {e}")
                else:
                    action = (
                        f"🛑 [DRY RUN] Stop-loss would trigger\n"
                        f"Symbol: {symbol}\n"
                        f"Loss: {pl_pct:+.2f}% (${pl_dollars:+,.2f})\n"
                        f"Entry: ${entry:,.2f} → Current: ${current:,.2f}"
                    )
                    actions.append(action)

        except Exception as e:
            continue

    # Send Telegram alert if any stop-losses triggered
    if actions:
        msg = "🚨 KhmerTrading Stop-Loss Alert\n"
        msg += f"📅 {datetime.now().strftime('%b %d, %I:%M %p')}\n"
        msg += f"Threshold: -{stop_loss_pct}%\n\n"
        for a in actions:
            msg += f"{a}\n\n"
        msg += "— Rule #1: No stop-loss = gambling"

        try:
            send_telegram(msg)
        except Exception:
            pass

    return actions


def render_stop_loss_controls():
    """Render stop-loss settings in the sidebar."""

    with st.expander("🛑 Stop-Loss Protection", expanded=False):
        st.caption("Auto-sell positions that drop below your loss limit. Rule #1: No stop-loss = gambling.")

        if 'stop_loss_enabled' not in st.session_state:
            st.session_state['stop_loss_enabled'] = True
        if 'stop_loss_pct' not in st.session_state:
            st.session_state['stop_loss_pct'] = 5.0
        if 'stop_loss_dry_run' not in st.session_state:
            st.session_state['stop_loss_dry_run'] = True

        enabled = st.toggle(
            "Enable Stop-Loss",
            value=st.session_state.get('stop_loss_enabled', True),
            key="sl_toggle",
        )
        st.session_state['stop_loss_enabled'] = enabled

        pct = st.slider(
            "Max loss %",
            min_value=1.0,
            max_value=10.0,
            value=st.session_state.get('stop_loss_pct', 5.0),
            step=0.5,
            key="sl_pct",
            help="Automatically sell if a position drops more than this percentage",
        )
        st.session_state['stop_loss_pct'] = pct

        mode = st.selectbox(
            "Mode",
            ["Dry Run (alert only)", "Live (auto-sell)"],
            key="sl_mode",
        )
        dry_run = "Dry Run" in mode
        st.session_state['stop_loss_dry_run'] = dry_run

        if not dry_run:
            st.warning("Live mode will AUTO-SELL losing positions!")

        if enabled:
            if dry_run:
                st.info(f"🔵 Monitoring positions. Alert if any drop below -{pct}%")
            else:
                st.success(f"🟢 Auto-selling positions that drop below -{pct}%")

            # Run the check
            actions = check_stop_losses(stop_loss_pct=pct, dry_run=dry_run)
            if actions:
                for a in actions:
                    st.warning(a)
            else:
                st.caption("All positions within safe range.")
