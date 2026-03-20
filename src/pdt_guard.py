"""PDT (Pattern Day Trader) Guard — tracks day trades and warns before hitting the 4-trade limit.
Crypto trades are excluded since PDT rule doesn't apply to crypto."""

import streamlit as st
from datetime import datetime, timedelta
from config import get_api


@st.cache_data(ttl=120)
def get_day_trade_count():
    """Count day trades in the last 5 business days.
    A day trade = buying and selling the same stock on the same day.
    Crypto is excluded from PDT rules.
    """
    api = get_api()
    day_trades = []

    try:
        # Get account info
        account = api.get_account()
        daytrade_count = int(account.daytrade_count) if hasattr(account, 'daytrade_count') else None
        pdt_flag = account.pattern_day_trader if hasattr(account, 'pattern_day_trader') else False
        equity = float(account.equity)

        # If Alpaca provides the count directly, use it
        if daytrade_count is not None:
            return {
                'count': daytrade_count,
                'limit': 3,  # Max 3 day trades in 5 days (4th triggers PDT)
                'remaining': max(0, 3 - daytrade_count),
                'pdt_flagged': pdt_flag,
                'equity': equity,
                'safe': equity >= 25000,
            }

        # Fallback: count manually from recent orders
        end = datetime.utcnow()
        start = end - timedelta(days=7)

        orders = api.list_orders(
            status='filled',
            after=start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            limit=100,
        )

        # Group by symbol and date
        trades_by_day = {}
        for order in orders:
            symbol = order.symbol
            # Skip crypto
            if 'USD' in symbol and len(symbol) > 5:
                continue

            filled_at = str(order.filled_at)[:10] if order.filled_at else None
            if not filled_at:
                continue

            key = f"{symbol}_{filled_at}"
            if key not in trades_by_day:
                trades_by_day[key] = {'buys': 0, 'sells': 0}

            if order.side == 'buy':
                trades_by_day[key]['buys'] += 1
            else:
                trades_by_day[key]['sells'] += 1

        # A day trade = same symbol bought AND sold on same day
        count = 0
        for key, data in trades_by_day.items():
            if data['buys'] > 0 and data['sells'] > 0:
                count += min(data['buys'], data['sells'])

        return {
            'count': count,
            'limit': 3,
            'remaining': max(0, 3 - count),
            'pdt_flagged': pdt_flag,
            'equity': equity,
            'safe': equity >= 25000,
        }

    except Exception as e:
        print(f"PDT check error: {e}")
        return {
            'count': 0,
            'limit': 3,
            'remaining': 3,
            'pdt_flagged': False,
            'equity': 0,
            'safe': True,
        }


def render_pdt_warning():
    """Show PDT day-trade counter in the sidebar."""
    data = get_day_trade_count()
    count = data['count']
    remaining = data['remaining']
    limit = data['limit']

    if data['pdt_flagged']:
        st.error("⛔ PDT FLAGGED — Your account is restricted from day trading.")
        return

    if not data['safe']:
        st.warning(f"⚠️ Equity ${data['equity']:,.0f} is below $25K — PDT rule applies strictly!")

    if remaining == 0:
        st.markdown(
            '<div style="background:#fee2e2; border:1px solid #fca5a5; border-radius:10px; padding:8px 10px; margin:4px 0;">'
            '<span style="font-weight:700; color:#991b1b; font-size:0.8rem;">⛔ Day Trade Limit Reached</span><br>'
            f'<span style="font-size:0.7rem; color:#991b1b;">{count}/{limit+1} trades used — DO NOT day trade stocks today</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    elif remaining == 1:
        st.markdown(
            '<div style="background:#fef3c7; border:1px solid #fcd34d; border-radius:10px; padding:8px 10px; margin:4px 0;">'
            '<span style="font-weight:700; color:#92400e; font-size:0.8rem;">⚠️ 1 Day Trade Left</span><br>'
            f'<span style="font-size:0.7rem; color:#92400e;">{count}/3 used in 5 days — be careful with stocks</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="background:#d1fae5; border:1px solid #6ee7b7; border-radius:10px; padding:8px 10px; margin:4px 0;">'
            f'<span style="font-weight:700; color:#065f46; font-size:0.8rem;">✅ {remaining} Day Trades Left</span><br>'
            f'<span style="font-size:0.7rem; color:#065f46;">{count}/3 used in 5 days — crypto unlimited</span>'
            '</div>',
            unsafe_allow_html=True,
        )
