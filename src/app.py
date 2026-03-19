import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from config import get_api
from auth import check_auth, get_user_api
from options import options_available, get_options_chain
from reports import send_daily_report
from strategy import (
    fetch_bars, fetch_crypto_bars, calculate_rsi, calculate_ma,
    calculate_macd, calculate_bollinger, calculate_vwap,
    combined_signal, momentum_signal, mean_reversion_signal, breakout_signal,
    RSI_OVERSOLD, RSI_OVERBOUGHT, MA_PERIOD, RSI_PERIOD,
    TIMEFRAME_MAP,
)
from correlation import get_correlation_matrix
from execution import (
    market_buy, market_sell, cancel_all_orders,
    limit_buy, limit_sell, stop_order, bracket_order, is_crypto,
)
from trade_log import get_trades
from portfolio_tracker import record_snapshot, get_snapshots_df
from alerts import add_alert, get_alerts, remove_alert, check_alerts, clear_triggered
from backtest import run_backtest
from sentiment import get_sentiment
from earnings import is_near_earnings
from yahoo_data import get_live_price, fetch_yahoo_bars

# ── Page Config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="KhmerTrading — Private",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Modern CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Global ─────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* ── Hide Streamlit chrome ──────────────────────── */
    #MainMenu, footer { visibility: hidden; }

    /* ── Section headers ───────────────────────────── */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #f1f5f9;
    }

    .page-title {
        font-size: 1.75rem;
        font-weight: 900;
        color: #0f172a;
        letter-spacing: -0.02em;
        margin-bottom: 0;
    }

    .page-subtitle {
        font-size: 0.875rem;
        color: #94a3b8;
        margin-top: -8px;
        margin-bottom: 1.5rem;
    }

    /* ── Metric cards ──────────────────────────────── */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border-radius: 16px;
        padding: 20px 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        color: #0f172a !important;
    }

    /* ── Buttons ───────────────────────────────────── */
    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.875rem;
        padding: 0.5rem 1.25rem;
        transition: all 0.15s ease;
        border: none;
    }
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: white !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
        box-shadow: 0 4px 12px rgba(16,185,129,0.3);
    }
    .stButton > button[kind="secondary"],
    .stButton > button[data-testid="stBaseButton-secondary"] {
        background: #f1f5f9 !important;
        color: #475569 !important;
    }
    .stButton > button[kind="secondary"]:hover,
    .stButton > button[data-testid="stBaseButton-secondary"]:hover {
        background: #e2e8f0 !important;
    }

    /* ── Tabs ──────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #f1f5f9;
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 8px 20px;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: #0f172a !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .stTabs [data-baseweb="tab-border"] { display: none; }
    .stTabs [data-baseweb="tab-highlight"] { display: none; }

    /* ── Dataframes ────────────────────────────────── */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }

    /* ── Sidebar ───────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        color: #0f172a !important;
        font-size: 1.25rem !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #1e293b !important;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown span {
        color: #475569 !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #e2e8f0;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stTextInput label,
    section[data-testid="stSidebar"] .stNumberInput label,
    section[data-testid="stSidebar"] .stMultiSelect label,
    section[data-testid="stSidebar"] .stCheckbox label {
        color: #64748b !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"],
    section[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        color: #0f172a !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        border: 1px solid #cbd5e1;
        color: #334155;
        background: #ffffff;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #f1f5f9;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        border: none;
        color: white;
    }

    /* ── Expander ──────────────────────────────────── */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 0.9rem;
        border-radius: 12px;
    }

    /* ── Divider ───────────────────────────────────── */
    hr {
        border: none;
        border-top: 1px solid #f1f5f9;
        margin: 1.5rem 0;
    }

    /* ── Signal badges ─────────────────────────────── */
    .signal-buy {
        display: inline-block;
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        color: #065f46;
        padding: 6px 16px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .signal-sell {
        display: inline-block;
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        color: #991b1b;
        padding: 6px 16px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .signal-hold {
        display: inline-block;
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
        padding: 6px 16px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.85rem;
    }

    /* ── Alerts ─────────────────────────────────────── */
    .stAlert {
        border-radius: 12px;
    }

    /* ── Status pill (sidebar) ─────────────────────── */
    .status-pill {
        display: inline-block;
        background: #d1fae5;
        color: #065f46 !important;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    /* ── Nav section in main ────────────────────────── */
    .nav-container {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 1rem;
    }

    /* ── Mobile responsive ─────────────────────────── */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1rem;
        }
        .page-title {
            font-size: 1.3rem;
        }
        .page-subtitle {
            font-size: 0.75rem;
        }
        div[data-testid="stMetric"] {
            padding: 12px 10px;
            border-radius: 10px;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 1.1rem !important;
        }
        div[data-testid="stMetric"] label {
            font-size: 0.65rem !important;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 6px 12px;
            font-size: 0.75rem;
        }
        .signal-buy, .signal-sell, .signal-hold {
            font-size: 0.75rem;
            padding: 4px 10px;
        }
    }
</style>
""", unsafe_allow_html=True)

if not check_auth():
    st.stop()

# ── Paper vs Live Mode ──────────────────────────────────────────────
# (trading_mode selectbox is in the sidebar below, but we need the value
#  before connecting, so we initialize session state here)
if 'trading_mode' not in st.session_state:
    st.session_state['trading_mode'] = 'Paper Trading'

# ── Connect to Alpaca ────────────────────────────────────────────────
live_mode = st.session_state.get('trading_mode') == 'Live Trading'
try:
    api = get_user_api(live=live_mode)
    account = api.get_account()
except Exception as e:
    st.error(f"Failed to connect to Alpaca: {e}")
    st.stop()

# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## KhmerTrading")
    st.caption("Family investment dashboard. Monitor markets, analyze strategies, and manage trades.")

    st.markdown("")

    with st.expander("Settings"):
        trading_mode = st.selectbox("Mode", ["Paper Trading", "Live Trading"], key="trading_mode")
        if trading_mode == "Live Trading":
            st.markdown('<span style="color: #dc2626; font-weight: 700;">CAUTION: Live trading uses real money!</span>', unsafe_allow_html=True)
            live_confirmed = st.checkbox("I understand the risks", key="live_confirm")
            if not live_confirmed:
                st.warning("Check the box above to confirm live trading.")
    mode_label = "Live Trading" if trading_mode == "Live Trading" else "Paper Trading"
    pill_bg = "#fee2e2" if trading_mode == "Live Trading" else "#d1fae5"
    pill_color = "#991b1b" if trading_mode == "Live Trading" else "#065f46"
    st.markdown(
        '<span class="status-pill" style="background: {}; color: {} !important;">{}</span>'.format(
            pill_bg, pill_color, mode_label),
        unsafe_allow_html=True,
    )
    st.markdown("")

    # ── Quick Trade
    with st.expander("Quick Trade", expanded=True):
        trade_symbols = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOG", "META", "AMD", "NFLX", "SPY",
                         "QQQ", "PLTR", "COIN", "SOFI", "UBER", "CRM", "INTC", "BA", "DIS", "PYPL",
                         "BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "SHIB/USD", "PEPE/USD",
                         "AVAX/USD", "LINK/USD", "LTC/USD", "UNI/USD"]
        trade_symbol = st.selectbox("Symbol", trade_symbols, index=0)
        # Show live price
        _trade_price = get_live_price(trade_symbol)
        if _trade_price and _trade_price['price']:
            _arrow = "+" if _trade_price['change_pct'] >= 0 else ""
            _color = "#10b981" if _trade_price['change_pct'] >= 0 else "#ef4444"
            st.markdown(f'<span style="font-size:1.1rem; font-weight:700;">${_trade_price["price"]:,.2f}</span> <span style="color:{_color}; font-size:0.85rem;">{_arrow}{_trade_price["change_pct"]:.2f}%</span>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if '/' in trade_symbol:
                trade_qty = st.number_input("Qty", min_value=0.001, max_value=10000.0, value=0.01, step=0.01, format="%.3f", help="Fractional amounts supported for crypto (e.g. 0.5)")
            else:
                trade_qty = st.number_input("Qty", min_value=1, max_value=10000, value=5, help="Number of shares to trade")
        with c2:
            order_type = st.selectbox("Type", ["Market", "Limit", "Stop", "Bracket"])

        trade_limit_price = trade_stop_price = trade_tp_price = trade_sl_price = None

        if order_type == "Limit":
            trade_limit_price = st.number_input("Limit Price", min_value=0.01, value=100.00, key="limit_px")
        elif order_type == "Stop":
            trade_stop_price = st.number_input("Stop Price", min_value=0.01, value=100.00, key="stop_px")
        elif order_type == "Bracket":
            c1, c2 = st.columns(2)
            with c1:
                trade_tp_price = st.number_input("Take Profit", min_value=0.01, value=110.00, key="tp_px")
            with c2:
                trade_sl_price = st.number_input("Stop Loss", min_value=0.01, value=90.00, key="sl_px")
            if is_crypto(trade_symbol):
                st.warning("Bracket orders not supported for crypto.")

        if order_type == "Bracket":
            if st.button("BUY Bracket", use_container_width=True, type="primary"):
                if is_crypto(trade_symbol):
                    st.error("Not supported for crypto")
                else:
                    result = bracket_order(trade_symbol, trade_qty, trade_tp_price, trade_sl_price)
                    if result:
                        st.success(f"Bracket: {trade_qty}x {trade_symbol}")
                    else:
                        st.error("Failed")
                    st.rerun()
        else:
            # Show trade result from previous action
            if 'trade_msg' in st.session_state:
                msg = st.session_state.pop('trade_msg')
                if msg.startswith('OK:'):
                    st.success(msg[3:])
                else:
                    st.error(msg[4:])

            if st.button("BUY", use_container_width=True, type="primary"):
                try:
                    if order_type == "Market":
                        result = market_buy(trade_symbol, trade_qty)
                    elif order_type == "Limit":
                        result = limit_buy(trade_symbol, trade_qty, trade_limit_price)
                    elif order_type == "Stop":
                        result = stop_order(trade_symbol, trade_qty, trade_stop_price, side='buy')
                    else:
                        result = None
                    if result:
                        st.session_state['trade_msg'] = f"OK:Bought {trade_qty}x {trade_symbol} (Order: {result.status})"
                    else:
                        st.session_state['trade_msg'] = "ERR:Buy failed — check symbol and try again"
                except Exception as e:
                    st.session_state['trade_msg'] = f"ERR:Buy failed: {e}"
                st.rerun()
            if st.button("SELL", use_container_width=True):
                try:
                    if order_type == "Market":
                        result = market_sell(trade_symbol, trade_qty)
                    elif order_type == "Limit":
                        result = limit_sell(trade_symbol, trade_qty, trade_limit_price)
                    elif order_type == "Stop":
                        result = stop_order(trade_symbol, trade_qty, trade_stop_price, side='sell')
                    else:
                        result = None
                    if result:
                        st.session_state['trade_msg'] = f"OK:Sold {trade_qty}x {trade_symbol} (Order: {result.status})"
                    else:
                        st.session_state['trade_msg'] = "ERR:Sell failed — check symbol and try again"
                except Exception as e:
                    st.session_state['trade_msg'] = f"ERR:Sell failed: {e}"
                st.rerun()

    # ── Watchlist
    with st.expander("Watchlist", expanded=True):
        all_watchlist_symbols = [
            "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOG", "META", "AMD", "NFLX", "SPY",
            "QQQ", "PLTR", "COIN", "SOFI", "UBER", "CRM", "INTC", "BA", "DIS", "PYPL",
            "SQ", "SHOP", "ROKU", "SNAP", "MARA", "RIOT", "HOOD", "NIO", "RIVN", "LCID",
            "BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "SHIB/USD", "PEPE/USD",
            "AVAX/USD", "LINK/USD", "UNI/USD", "AAVE/USD", "DOT/USD", "LTC/USD",
            "BCH/USD", "XLM/USD", "ALGO/USD", "ATOM/USD", "NEAR/USD", "FIL/USD",
            "APE/USD", "MATIC/USD", "ARB/USD", "OP/USD", "MKR/USD", "GRT/USD",
        ]
        # Initialize watchlist in session state
        if 'watchlist_items' not in st.session_state:
            st.session_state['watchlist_items'] = ["NVDA", "TSLA", "AAPL", "BTC/USD", "ETH/USD", "DOGE/USD"]

        # Add symbol dropdown
        available = [s for s in all_watchlist_symbols if s not in st.session_state['watchlist_items']]
        if available:
            add_sym = st.selectbox("Add symbol", [""] + available, index=0, key="wl_add")
            if add_sym:
                st.session_state['watchlist_items'].append(add_sym)
                st.rerun()

        # Show current watchlist with price and remove buttons
        if st.session_state['watchlist_items']:
            for sym in st.session_state['watchlist_items']:
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.caption(sym)
                with c2:
                    _wp = get_live_price(sym)
                    if _wp and _wp['price']:
                        _wcolor = "#10b981" if _wp['change_pct'] >= 0 else "#ef4444"
                        st.markdown(f'<span style="font-size:0.8rem; font-weight:600;">${_wp["price"]:,.2f}</span> <span style="color:{_wcolor}; font-size:0.7rem;">{_wp["change_pct"]:+.1f}%</span>', unsafe_allow_html=True)
                    else:
                        st.caption("---")
                with c3:
                    if st.button("x", key=f"rm_{sym}"):
                        st.session_state['watchlist_items'].remove(sym)
                        st.rerun()

        watchlist = st.session_state['watchlist_items']

    # ── Price Alerts
    with st.expander("Price Alerts"):
        all_symbols = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOG", "META", "AMD", "NFLX", "SPY",
                       "QQQ", "PLTR", "COIN", "SOFI", "UBER", "CRM", "INTC", "BA", "DIS", "PYPL",
                       "BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "SHIB/USD", "PEPE/USD",
                       "AVAX/USD", "LINK/USD", "LTC/USD", "UNI/USD"]
        alert_symbol = st.selectbox("Symbol", all_symbols, index=all_symbols.index("BTC/USD"), key="alert_sym")
        # Show live price
        _ap = get_live_price(alert_symbol)
        if _ap and _ap['price']:
            _acolor = "#10b981" if _ap['change_pct'] >= 0 else "#ef4444"
            st.markdown(f'<span style="font-size:1rem; font-weight:700;">${_ap["price"]:,.2f}</span> <span style="color:{_acolor}; font-size:0.8rem;">{_ap["change_pct"]:+.2f}%</span>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            alert_price = st.number_input("Target ($)", min_value=0.01, value=100.00, key="alert_price")
        with c2:
            alert_dir = st.selectbox("When", ["above", "below"], key="alert_dir")
        if st.button("Add Alert", use_container_width=True):
            add_alert(alert_symbol, alert_price, alert_dir)
            st.success(f"{alert_symbol} {alert_dir} ${alert_price:,.2f}")
            st.rerun()

        alerts = get_alerts()
        pending = [a for a in alerts if not a['triggered']]
        if pending:
            for a in pending:
                st.caption(f"**{a['symbol']}** {a['direction']} ${a['target']:,.2f}")

    st.markdown("---")

    # ── Controls
    c1, c2 = st.columns(2)
    with c1:
        auto_refresh_on = st.checkbox("Auto-Refresh", value=False)
    with c2:
        if st.button("Refresh", use_container_width=True):
            st.rerun()

    if st.button("Cancel All Orders", use_container_width=True):
        cancel_all_orders()
        st.error("All orders cancelled!")
        st.rerun()

    st.markdown("---")
    if st.button("Send Report", use_container_width=True):
        ok = send_daily_report()
        if ok:
            st.success("Report sent!")
        else:
            st.error("Report not sent. Check SMTP / REPORT_EMAIL config.")

    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        st.session_state["authenticated"] = False
        st.query_params.clear()
        st.rerun()

    st.caption(f"Updated {datetime.now().strftime('%I:%M:%S %p')}")

# ── Auto-Refresh ────────────────────────────────────────────────────
if auto_refresh_on:
    st_autorefresh(interval=60000, key="auto_refresh")


# ════════════════════════════════════════════════════════════════════
#  MAIN CONTENT
# ════════════════════════════════════════════════════════════════════

st.markdown('<p class="page-title">Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p class="page-subtitle">Account overview and market analysis</p>', unsafe_allow_html=True)

# ── Account Overview ─────────────────────────────────────────────────
equity = float(account.equity)
cash = float(account.cash)
buying_power = float(account.buying_power)
portfolio_value = float(account.portfolio_value)
initial = 100000.0
total_pl = equity - initial
total_pl_pct = (total_pl / initial) * 100

record_snapshot(equity, cash, portfolio_value)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Equity", f"${equity:,.2f}", delta=f"{total_pl_pct:+.2f}%", help="Total account value including all positions and cash")
with col2:
    st.metric("Cash", f"${cash:,.2f}", help="Available cash not invested in any position")
with col3:
    st.metric("Portfolio", f"${portfolio_value:,.2f}", help="Total value of all your current positions")
with col4:
    st.metric("Buying Power", f"${buying_power:,.2f}", help="Maximum amount you can use to open new positions")
with col5:
    pl_label = "Profit" if total_pl >= 0 else "Loss"
    st.metric("P/L", f"${total_pl:,.2f}", delta=pl_label, help="Total profit or loss since account start ($100k)")
st.caption("This is paper trading — no real money is at risk." if trading_mode != "Live Trading" else "LIVE TRADING — real money is at risk.")

# ── Portfolio Performance ────────────────────────────────────────────
snap_df = get_snapshots_df(days=30)
if not snap_df.empty and len(snap_df) > 1:
    fig_equity = go.Figure()
    fig_equity.add_trace(go.Scatter(
        x=snap_df['timestamp'], y=snap_df['equity'],
        name='Equity',
        line=dict(color='#10b981', width=2.5),
        fill='tozeroy', fillcolor='rgba(16,185,129,0.06)',
    ))
    fig_equity.add_hline(y=100000, line_dash="dot", line_color="#94a3b8", line_width=1)
    fig_equity.update_layout(
        height=260,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor='#f1f5f9', title=""),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
    )
    st.plotly_chart(fig_equity, use_container_width=True)

# ── Navigation tabs for main content ────────────────────────────────
st.markdown("---")

main_tab1, main_tab2, main_tab3, main_tab4, main_tab5, main_tab6, main_tab7, main_tab8 = st.tabs([
    "Watchlist", "Strategy", "Crypto", "Positions", "Orders", "Alerts", "Backtest", "Options"
])


# ═══════════════════════════════════════════════════════════════════
#  TAB 1: WATCHLIST
# ═══════════════════════════════════════════════════════════════════
with main_tab1:
    st.caption("Real-time prices for your tracked assets")
    if watchlist:
        # Limit columns to avoid squishing
        per_row = min(len(watchlist), 4)
        rows = [watchlist[i:i+per_row] for i in range(0, len(watchlist), per_row)]
        for row in rows:
            cols = st.columns(per_row)
            for j, symbol in enumerate(row):
                with cols[j]:
                    try:
                        data = get_live_price(symbol)
                        if data and data['price']:
                            price = data['price']
                            change_pct = data['change_pct']
                            arrow = "+" if change_pct >= 0 else ""
                            st.metric(symbol, f"${price:,.2f}", delta=f"{arrow}{change_pct:.2f}%")
                        else:
                            st.metric(symbol, "---", delta="unavailable")
                    except Exception as e:
                        st.metric(symbol, "---", delta="unavailable")
        st.caption("Click on the Strategy tab for detailed analysis of each stock.")
    else:
        st.info("Add symbols to your watchlist in the sidebar.")


# ═══════════════════════════════════════════════════════════════════
#  TAB 2: STRATEGY MONITOR
# ═══════════════════════════════════════════════════════════════════
with main_tab2:
    st.caption("AI-powered buy/sell signals based on technical analysis")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        stock_timeframe = st.selectbox("Timeframe", list(TIMEFRAME_MAP.keys()), index=2, key="stock_tf")
    with c2:
        selected_indicators = st.multiselect(
            "Indicators",
            ["RSI", "MA", "MACD", "Bollinger Bands", "VWAP"],
            default=["RSI", "MA"],
            key="indicators",
        )
    with c3:
        strategy_choice = st.selectbox(
            "Strategy",
            ["Combined (RSI+MA+MACD+BB)", "Momentum", "Mean Reversion", "Breakout"],
            key="strategy_sel",
        )

    stock_watchlist = [s for s in watchlist if '/' not in s]

    if stock_watchlist:
        tabs = st.tabs(stock_watchlist)
        for i, symbol in enumerate(stock_watchlist):
            with tabs[i]:
                try:
                    bars = fetch_yahoo_bars(symbol, timeframe=stock_timeframe)
                    if bars is None:
                        bars = fetch_bars(symbol, timeframe=stock_timeframe)
                    if bars is None or len(bars) < MA_PERIOD:
                        st.warning(f"Not enough data for {symbol}")
                        continue

                    bars['rsi'] = calculate_rsi(bars['close'])
                    bars['ma'] = calculate_ma(bars['close'])

                    current_price = bars['close'].iloc[-1]
                    current_rsi = bars['rsi'].iloc[-1]
                    current_ma = bars['ma'].iloc[-1]
                    price_vs_ma = ((current_price - current_ma) / current_ma) * 100

                    if current_rsi < RSI_OVERSOLD and current_price < current_ma:
                        signal, signal_class = "BUY", "signal-buy"
                    elif current_rsi > RSI_OVERBOUGHT:
                        signal, signal_class = "SELL", "signal-sell"
                    else:
                        signal, signal_class = "HOLD", "signal-hold"

                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("Price", f"${current_price:,.2f}")
                    with m2:
                        st.metric("RSI", f"{current_rsi:.1f}")
                    with m3:
                        st.metric("MA", f"${current_ma:,.2f}", delta=f"{price_vs_ma:+.2f}%")
                    with m4:
                        st.markdown(f'<div style="padding-top:24px"><span class="{signal_class}">{signal}</span></div>', unsafe_allow_html=True)

                    # Strategy signal analysis
                    if strategy_choice == "Momentum":
                        cs = momentum_signal(bars)
                        strat_label = "Momentum"
                    elif strategy_choice == "Mean Reversion":
                        cs = mean_reversion_signal(bars)
                        strat_label = "Mean Reversion"
                    elif strategy_choice == "Breakout":
                        cs = breakout_signal(bars)
                        strat_label = "Breakout"
                    else:
                        cs = combined_signal(bars)
                        strat_label = "Combined"

                    cs_signal = cs['signal']
                    cs_confidence = cs['confidence']
                    cs_reasons = cs['reasons']

                    st.markdown("**%s Signal: %s** (confidence: %.0f%%)" % (strat_label, cs_signal, cs_confidence))
                    st.progress(cs_confidence / 100.0)
                    if cs_reasons:
                        for r in cs_reasons:
                            st.markdown("- %s" % r)
                    else:
                        st.caption("No strong indicators triggered.")

                    # ── Earnings warning ──────────────────────────
                    earnings_near, earnings_reason = is_near_earnings(symbol)
                    if earnings_near:
                        st.warning("Earnings Alert: %s" % earnings_reason)

                    # ── News sentiment ────────────────────────────
                    sentiment = get_sentiment(symbol)
                    sent_summary = sentiment['summary']
                    if sent_summary == 'Bullish':
                        sent_class = 'signal-buy'
                    elif sent_summary == 'Bearish':
                        sent_class = 'signal-sell'
                    else:
                        sent_class = 'signal-hold'

                    st.markdown("---")
                    s1, s2 = st.columns([1, 2])
                    with s1:
                        st.markdown(
                            '<div style="padding-top:4px"><span class="%s">Sentiment: %s</span></div>' % (sent_class, sent_summary),
                            unsafe_allow_html=True,
                        )
                    with s2:
                        st.metric("Sentiment Score", "%.2f" % sentiment['score'])

                    if sentiment['articles']:
                        with st.expander("Recent Headlines"):
                            for art in sentiment['articles']:
                                if art['sentiment'] == 'bullish':
                                    color = '#10b981'
                                elif art['sentiment'] == 'bearish':
                                    color = '#ef4444'
                                else:
                                    color = '#94a3b8'
                                st.markdown(
                                    '<span style="color:%s; font-weight:600;">%s</span> &nbsp; '
                                    '<span style="color:#94a3b8; font-size:0.75rem;">%s</span>' % (
                                        color,
                                        art['headline'],
                                        art['timestamp'][:16],
                                    ),
                                    unsafe_allow_html=True,
                                )

                    # Price chart
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=bars['timestamp'],
                        open=bars['open'], high=bars['high'],
                        low=bars['low'], close=bars['close'],
                        name='Price',
                        increasing_line_color='#10b981', decreasing_line_color='#ef4444',
                        increasing_fillcolor='#10b981', decreasing_fillcolor='#ef4444',
                    ))
                    if "MA" in selected_indicators:
                        fig.add_trace(go.Scatter(
                            x=bars['timestamp'], y=bars['ma'],
                            name=f'{MA_PERIOD}-MA', line=dict(color='#f59e0b', width=2, dash='dash')
                        ))
                    if "Bollinger Bands" in selected_indicators:
                        bb = calculate_bollinger(bars['close'])
                        fig.add_trace(go.Scatter(x=bars['timestamp'], y=bb['upper'], name='BB Upper',
                                                 line=dict(color='rgba(99,102,241,0.4)', width=1)))
                        fig.add_trace(go.Scatter(x=bars['timestamp'], y=bb['lower'], name='BB Lower',
                                                 line=dict(color='rgba(99,102,241,0.4)', width=1),
                                                 fill='tonexty', fillcolor='rgba(99,102,241,0.06)'))
                    if "VWAP" in selected_indicators:
                        vwap = calculate_vwap(bars)
                        fig.add_trace(go.Scatter(x=bars['timestamp'], y=vwap, name='VWAP',
                                                 line=dict(color='#8b5cf6', width=2, dash='dot')))
                    fig.update_layout(
                        height=420,
                        margin=dict(l=0, r=0, t=10, b=0),
                        xaxis_rangeslider_visible=False,
                        xaxis=dict(showgrid=False, title=""),
                        yaxis=dict(showgrid=True, gridcolor='#f1f5f9', title=""),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Sub-charts
                    sub_charts = []
                    if "RSI" in selected_indicators:
                        sub_charts.append("RSI")
                    if "MACD" in selected_indicators:
                        sub_charts.append("MACD")

                    if sub_charts:
                        sub_cols = st.columns(len(sub_charts))
                        for j, chart_name in enumerate(sub_charts):
                            with sub_cols[j]:
                                if chart_name == "RSI":
                                    fig_rsi = go.Figure()
                                    fig_rsi.add_trace(go.Scatter(
                                        x=bars['timestamp'], y=bars['rsi'],
                                        name='RSI', line=dict(color='#8b5cf6', width=2),
                                        fill='tozeroy', fillcolor='rgba(139,92,246,0.06)'
                                    ))
                                    fig_rsi.add_hline(y=RSI_OVERSOLD, line_dash="dash", line_color="#10b981", line_width=1)
                                    fig_rsi.add_hline(y=RSI_OVERBOUGHT, line_dash="dash", line_color="#ef4444", line_width=1)
                                    fig_rsi.add_hline(y=50, line_dash="dot", line_color="#e2e8f0", line_width=1)
                                    fig_rsi.update_layout(
                                        height=250,
                                        margin=dict(l=0, r=0, t=10, b=0),
                                        yaxis=dict(range=[0, 100], showgrid=True, gridcolor='#f1f5f9', title=""),
                                        xaxis=dict(showgrid=False, title=""),
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        paper_bgcolor='rgba(0,0,0,0)',
                                        showlegend=False,
                                    )
                                    st.plotly_chart(fig_rsi, use_container_width=True)
                                elif chart_name == "MACD":
                                    macd_data = calculate_macd(bars['close'])
                                    fig_macd = go.Figure()
                                    fig_macd.add_trace(go.Scatter(
                                        x=bars['timestamp'], y=macd_data['macd_line'],
                                        name='MACD', line=dict(color='#3b82f6', width=2)
                                    ))
                                    fig_macd.add_trace(go.Scatter(
                                        x=bars['timestamp'], y=macd_data['signal_line'],
                                        name='Signal', line=dict(color='#f59e0b', width=2)
                                    ))
                                    colors = ['#10b981' if v >= 0 else '#ef4444' for v in macd_data['histogram']]
                                    fig_macd.add_trace(go.Bar(
                                        x=bars['timestamp'], y=macd_data['histogram'],
                                        name='Histogram', marker_color=colors
                                    ))
                                    fig_macd.update_layout(
                                        height=250,
                                        margin=dict(l=0, r=0, t=10, b=0),
                                        xaxis=dict(showgrid=False, title=""),
                                        yaxis=dict(showgrid=True, gridcolor='#f1f5f9', title=""),
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        paper_bgcolor='rgba(0,0,0,0)',
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                    )
                                    st.plotly_chart(fig_macd, use_container_width=True)

                    with st.expander(f"Raw Data — {symbol}"):
                        display = bars[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'rsi', 'ma']].copy()
                        display['timestamp'] = display['timestamp'].astype(str).str[:16]
                        st.dataframe(display.round(2), use_container_width=True, hide_index=True)

                except Exception as e:
                    st.error(f"Error analyzing {symbol}: {e}")
    else:
        st.info("Add stock symbols to your watchlist.")

    # ── Correlation Analysis ──────────────────────────────────────
    if len(stock_watchlist) >= 2:
        with st.expander("Correlation Analysis"):
            try:
                corr_matrix = get_correlation_matrix(stock_watchlist, days=30)
                if corr_matrix is not None and not corr_matrix.empty:
                    symbols_list = list(corr_matrix.columns)
                    fig_corr = go.Figure(data=go.Heatmap(
                        z=corr_matrix.values,
                        x=symbols_list,
                        y=symbols_list,
                        colorscale='RdYlGn',
                        zmin=-1, zmax=1,
                        text=corr_matrix.round(2).values,
                        texttemplate="%{text}",
                        textfont=dict(size=12),
                    ))
                    fig_corr.update_layout(
                        height=400,
                        margin=dict(l=0, r=0, t=10, b=0),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(showgrid=False),
                        yaxis=dict(showgrid=False, autorange='reversed'),
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)
                else:
                    st.info("Not enough data to compute correlations.")
            except Exception as e:
                st.warning("Correlation analysis unavailable: %s" % e)


# ═══════════════════════════════════════════════════════════════════
#  TAB 3: CRYPTO
# ═══════════════════════════════════════════════════════════════════
with main_tab3:
    st.caption("Live cryptocurrency prices and analysis")
    crypto_tf = st.selectbox("Timeframe", list(TIMEFRAME_MAP.keys()), index=2, key="crypto_tf")

    CRYPTO_SYMBOLS = ["BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "SHIB/USD", "PEPE/USD", "AVAX/USD", "LINK/USD", "LTC/USD", "UNI/USD"]
    crypto_tabs = st.tabs(CRYPTO_SYMBOLS)

    for i, symbol in enumerate(CRYPTO_SYMBOLS):
        with crypto_tabs[i]:
            try:
                data = get_live_price(symbol)
                if data and data['price']:
                    price = data['price']
                    prev_close = data['prev_close'] or price
                    change = data['change']
                    change_pct = data['change_pct']
                else:
                    snapshots = api.get_crypto_snapshot(symbol)
                    snapshot = snapshots[symbol] if isinstance(snapshots, dict) else snapshots
                    price = float(snapshot.latest_trade.p)
                    prev_close = float(snapshot.prev_daily_bar.c) if snapshot.prev_daily_bar else price
                    change = price - prev_close
                    change_pct = (change / prev_close * 100) if prev_close != 0 else 0

                m1, m2 = st.columns(2)
                with m1:
                    st.metric(f"{symbol}", f"${price:,.2f}",
                              delta=f"{'+' if change >= 0 else ''}{change_pct:.2f}%")
                with m2:
                    st.metric("Prev Close", f"${prev_close:,.2f}")

                bars = fetch_yahoo_bars(symbol, timeframe=crypto_tf)
                if bars is None:
                    bars = fetch_crypto_bars(symbol, hours=48, timeframe=crypto_tf)
                if bars is not None and len(bars) >= MA_PERIOD:
                    bars['rsi'] = calculate_rsi(bars['close'])
                    bars['ma'] = calculate_ma(bars['close'])

                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=bars['timestamp'],
                        open=bars['open'], high=bars['high'],
                        low=bars['low'], close=bars['close'],
                        name='Price',
                        increasing_line_color='#10b981', decreasing_line_color='#ef4444',
                        increasing_fillcolor='#10b981', decreasing_fillcolor='#ef4444',
                    ))
                    if "MA" in selected_indicators:
                        fig.add_trace(go.Scatter(x=bars['timestamp'], y=bars['ma'],
                                                 name=f'{MA_PERIOD}-MA', line=dict(color='#f59e0b', width=2, dash='dash')))
                    if "Bollinger Bands" in selected_indicators:
                        bb = calculate_bollinger(bars['close'])
                        fig.add_trace(go.Scatter(x=bars['timestamp'], y=bb['upper'], name='BB Upper',
                                                 line=dict(color='rgba(99,102,241,0.4)', width=1)))
                        fig.add_trace(go.Scatter(x=bars['timestamp'], y=bb['lower'], name='BB Lower',
                                                 line=dict(color='rgba(99,102,241,0.4)', width=1),
                                                 fill='tonexty', fillcolor='rgba(99,102,241,0.06)'))
                    if "VWAP" in selected_indicators:
                        vwap = calculate_vwap(bars)
                        fig.add_trace(go.Scatter(x=bars['timestamp'], y=vwap, name='VWAP',
                                                 line=dict(color='#8b5cf6', width=2, dash='dot')))
                    fig.update_layout(
                        height=420,
                        margin=dict(l=0, r=0, t=10, b=0),
                        xaxis_rangeslider_visible=False,
                        xaxis=dict(showgrid=False, title=""),
                        yaxis=dict(showgrid=True, gridcolor='#f1f5f9', title=""),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Sub-charts
                    crypto_sub = []
                    if "RSI" in selected_indicators:
                        crypto_sub.append("RSI")
                    if "MACD" in selected_indicators:
                        crypto_sub.append("MACD")

                    if crypto_sub:
                        sub_cols = st.columns(len(crypto_sub))
                        for j, chart_name in enumerate(crypto_sub):
                            with sub_cols[j]:
                                if chart_name == "RSI":
                                    fig_rsi = go.Figure()
                                    fig_rsi.add_trace(go.Scatter(
                                        x=bars['timestamp'], y=bars['rsi'],
                                        name='RSI', line=dict(color='#8b5cf6', width=2),
                                        fill='tozeroy', fillcolor='rgba(139,92,246,0.06)'
                                    ))
                                    fig_rsi.add_hline(y=RSI_OVERSOLD, line_dash="dash", line_color="#10b981", line_width=1)
                                    fig_rsi.add_hline(y=RSI_OVERBOUGHT, line_dash="dash", line_color="#ef4444", line_width=1)
                                    fig_rsi.update_layout(
                                        height=250,
                                        margin=dict(l=0, r=0, t=10, b=0),
                                        yaxis=dict(range=[0, 100], showgrid=True, gridcolor='#f1f5f9', title=""),
                                        xaxis=dict(showgrid=False, title=""),
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        paper_bgcolor='rgba(0,0,0,0)',
                                        showlegend=False,
                                    )
                                    st.plotly_chart(fig_rsi, use_container_width=True)
                                elif chart_name == "MACD":
                                    macd_data = calculate_macd(bars['close'])
                                    fig_macd = go.Figure()
                                    fig_macd.add_trace(go.Scatter(
                                        x=bars['timestamp'], y=macd_data['macd_line'],
                                        name='MACD', line=dict(color='#3b82f6', width=2)))
                                    fig_macd.add_trace(go.Scatter(
                                        x=bars['timestamp'], y=macd_data['signal_line'],
                                        name='Signal', line=dict(color='#f59e0b', width=2)))
                                    colors = ['#10b981' if v >= 0 else '#ef4444' for v in macd_data['histogram']]
                                    fig_macd.add_trace(go.Bar(
                                        x=bars['timestamp'], y=macd_data['histogram'],
                                        name='Histogram', marker_color=colors))
                                    fig_macd.update_layout(
                                        height=250,
                                        margin=dict(l=0, r=0, t=10, b=0),
                                        xaxis=dict(showgrid=False, title=""),
                                        yaxis=dict(showgrid=True, gridcolor='#f1f5f9', title=""),
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        paper_bgcolor='rgba(0,0,0,0)',
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                    )
                                    st.plotly_chart(fig_macd, use_container_width=True)

                    # Signal
                    current_rsi = bars['rsi'].iloc[-1]
                    current_ma = bars['ma'].iloc[-1]
                    if current_rsi < RSI_OVERSOLD and price < current_ma:
                        st.markdown('<span class="signal-buy">BUY — RSI %.1f oversold, below MA</span>' % current_rsi, unsafe_allow_html=True)
                    elif current_rsi > RSI_OVERBOUGHT:
                        st.markdown('<span class="signal-sell">SELL — RSI %.1f overbought</span>' % current_rsi, unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="signal-hold">HOLD — RSI %.1f</span>' % current_rsi, unsafe_allow_html=True)

                    # ── News sentiment ────────────────────────
                    crypto_sentiment = get_sentiment(symbol)
                    cs_summary = crypto_sentiment['summary']
                    if cs_summary == 'Bullish':
                        cs_class = 'signal-buy'
                    elif cs_summary == 'Bearish':
                        cs_class = 'signal-sell'
                    else:
                        cs_class = 'signal-hold'

                    st.markdown("---")
                    cs1, cs2 = st.columns([1, 2])
                    with cs1:
                        st.markdown(
                            '<div style="padding-top:4px"><span class="%s">Sentiment: %s</span></div>' % (cs_class, cs_summary),
                            unsafe_allow_html=True,
                        )
                    with cs2:
                        st.metric("Sentiment Score", "%.2f" % crypto_sentiment['score'])

                    if crypto_sentiment['articles']:
                        with st.expander("Recent Headlines"):
                            for art in crypto_sentiment['articles']:
                                if art['sentiment'] == 'bullish':
                                    color = '#10b981'
                                elif art['sentiment'] == 'bearish':
                                    color = '#ef4444'
                                else:
                                    color = '#94a3b8'
                                st.markdown(
                                    '<span style="color:%s; font-weight:600;">%s</span> &nbsp; '
                                    '<span style="color:#94a3b8; font-size:0.75rem;">%s</span>' % (
                                        color,
                                        art['headline'],
                                        art['timestamp'][:16],
                                    ),
                                    unsafe_allow_html=True,
                                )
                else:
                    st.warning(f"Not enough data for {symbol}")

            except Exception as e:
                st.error(f"Error loading {symbol}: {e}")


# ═══════════════════════════════════════════════════════════════════
#  TAB 4: POSITIONS
# ═══════════════════════════════════════════════════════════════════
with main_tab4:
    st.caption("Your current holdings and profit/loss")
    try:
        positions = api.list_positions()

        if not positions:
            st.info("No open positions. Use the sidebar to place your first trade.")
        else:
            pos_data = []
            total_pl = 0
            total_mv = 0

            for pos in positions:
                pl = float(pos.unrealized_pl)
                pl_pct = float(pos.unrealized_plpc) * 100
                mv = float(pos.market_value)
                total_pl += pl
                total_mv += mv

                pos_data.append({
                    'Symbol': pos.symbol,
                    'Side': 'Long' if pos.side == 'long' else 'Short',
                    'Qty': float(pos.qty) if '.' in str(pos.qty) else int(pos.qty),
                    'Avg Cost': f"${float(pos.avg_entry_price):,.2f}",
                    'Current': f"${float(pos.current_price):,.2f}",
                    'Value': f"${mv:,.2f}",
                    'P/L': f"${pl:+,.2f}",
                    'P/L %': f"{pl_pct:+.2f}%",
                })

            st.dataframe(pd.DataFrame(pos_data), use_container_width=True, hide_index=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Unrealized P/L", f"${total_pl:+,.2f}")
            with c2:
                st.metric("Market Value", f"${total_mv:,.2f}")
            with c3:
                st.metric("Positions", str(len(positions)))

            # ── Portfolio Allocation Pie Chart ────────────────
            alloc_labels = [p['Symbol'] for p in pos_data]
            alloc_values = [float(pos.market_value) for pos in positions]
            # Add remaining cash
            alloc_labels.append("Cash")
            alloc_values.append(cash)

            pie_colors = [
                '#10b981', '#059669', '#047857', '#065f46',  # greens
                '#3b82f6', '#2563eb', '#1d4ed8',             # blues
                '#8b5cf6', '#7c3aed', '#6d28d9',             # purples
                '#06b6d4', '#0891b2', '#0e7490',             # cyan
            ]

            fig_pie = go.Figure(data=[go.Pie(
                labels=alloc_labels,
                values=alloc_values,
                hole=0.4,
                marker=dict(colors=pie_colors[:len(alloc_labels)]),
                textinfo='label+percent',
                textfont=dict(size=12),
            )])
            fig_pie.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading positions: {e}")


# ═══════════════════════════════════════════════════════════════════
#  TAB 5: ORDERS + TRADE HISTORY
# ═══════════════════════════════════════════════════════════════════
with main_tab5:
    st.caption("Recent order history")
    orders_sub1, orders_sub2 = st.tabs(["Recent Orders", "Trade History"])

    with orders_sub1:
        try:
            orders = api.list_orders(limit=15, status='all')
            if not orders:
                st.info("No orders placed yet.")
            else:
                order_data = []
                for o in orders:
                    filled = f"${float(o.filled_avg_price):,.2f}" if o.filled_avg_price else "---"
                    submitted = str(o.submitted_at)[:19] if o.submitted_at else "---"

                    status_map = {"filled": "Filled", "new": "Pending", "partially_filled": "Partial",
                                  "canceled": "Canceled", "expired": "Expired", "rejected": "Rejected"}

                    order_data.append({
                        'Side': o.side.upper(),
                        'Symbol': o.symbol,
                        'Qty': o.qty,
                        'Type': o.type.upper(),
                        'Fill Price': filled,
                        'Status': status_map.get(o.status, o.status),
                        'Time': submitted,
                    })

                st.dataframe(pd.DataFrame(order_data), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error loading orders: {e}")

    with orders_sub2:
        trade_history = get_trades()
        if trade_history:
            trade_df = pd.DataFrame(trade_history)
            st.dataframe(trade_df, use_container_width=True, hide_index=True)

            csv = trade_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", data=csv, file_name="trade_history.csv", mime="text/csv")
        else:
            st.info("No trades logged yet.")


# ═══════════════════════════════════════════════════════════════════
#  TAB 6: ALERTS
# ═══════════════════════════════════════════════════════════════════
with main_tab6:
    st.caption("Price alerts you've set")
    newly_triggered = check_alerts()
    for t in newly_triggered:
        st.toast(f"ALERT: {t['symbol']} hit ${t['triggered_price']:,.2f}", icon="🚨")

    alerts = get_alerts()

    if not alerts:
        st.info("No price alerts. Add one from the sidebar.")
    else:
        triggered_alerts = [a for a in alerts if a['triggered']]
        pending_alerts = [a for a in alerts if not a['triggered']]

        if triggered_alerts:
            for a in triggered_alerts:
                st.warning(
                    f"**TRIGGERED** — {a['symbol']} went {a['direction']} ${a['target']:,.2f} "
                    f"(${a.get('triggered_price', 0):,.2f} at {a.get('triggered_at', '?')})"
                )
            if st.button("Clear Triggered"):
                clear_triggered()
                st.rerun()

        if pending_alerts:
            alert_data = []
            for i, a in enumerate(alerts):
                if not a['triggered']:
                    alert_data.append({
                        '#': i,
                        'Symbol': a['symbol'],
                        'Direction': a['direction'].upper(),
                        'Target': f"${a['target']:,.2f}",
                        'Created': a.get('created_at', ''),
                    })
            st.dataframe(pd.DataFrame(alert_data), use_container_width=True, hide_index=True)

            c1, c2 = st.columns([1, 3])
            with c1:
                remove_idx = st.number_input("Alert #", min_value=0, max_value=len(alerts) - 1, value=0, key="rm_alert")
            with c2:
                st.markdown("")
                st.markdown("")
                if st.button("Remove"):
                    remove_alert(int(remove_idx))
                    st.rerun()
        elif triggered_alerts:
            st.success("All alerts triggered.")


# ═══════════════════════════════════════════════════════════════════
#  TAB 7: BACKTESTING
# ═══════════════════════════════════════════════════════════════════
with main_tab7:
    st.caption("Test strategies on historical data")

    with st.expander("Parameters", expanded=True):
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            bt_symbol = st.text_input("Symbol", value="NVDA", key="bt_symbol").upper()
        with p2:
            bt_days = st.slider("Days", 30, 365, 90, key="bt_days")
        with p3:
            bt_capital = st.number_input("Capital ($)", min_value=1000, value=100000, key="bt_capital")
        with p4:
            bt_qty = st.number_input("Trade Qty", min_value=1, value=5, key="bt_qty")

        p5, p6, p7, p8 = st.columns(4)
        with p5:
            bt_rsi_period = st.number_input("RSI Period", min_value=2, max_value=50, value=14, key="bt_rsi")
        with p6:
            bt_ma_period = st.number_input("MA Period", min_value=2, max_value=100, value=20, key="bt_ma")
        with p7:
            bt_rsi_oversold = st.number_input("Oversold", min_value=1, max_value=50, value=30, key="bt_oversold")
        with p8:
            bt_rsi_overbought = st.number_input("Overbought", min_value=50, max_value=99, value=70, key="bt_overbought")

    bt_profit_target = st.number_input("Profit Target (%)", min_value=0.1, max_value=50.0, value=2.0, step=0.1, key="bt_pt") / 100.0

    if st.button("Run Backtest", use_container_width=True, type="primary", key="bt_run"):
        with st.spinner("Running backtest..."):
            result = run_backtest(
                symbol=bt_symbol, days=bt_days, initial_capital=float(bt_capital),
                trade_qty=bt_qty, rsi_period=bt_rsi_period, ma_period=bt_ma_period,
                rsi_oversold=float(bt_rsi_oversold), rsi_overbought=float(bt_rsi_overbought),
                profit_target=bt_profit_target,
            )
            if result is not None:
                st.session_state['bt_result'] = result
                st.session_state['bt_symbol_display'] = bt_symbol
            else:
                st.error("Backtest failed — not enough data.")
                if 'bt_result' in st.session_state:
                    del st.session_state['bt_result']

    if 'bt_result' in st.session_state:
        result = st.session_state['bt_result']
        metrics = result['metrics']

        mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
        with mc1:
            st.metric("Return", "%+.2f%%" % metrics['total_return_pct'])
        with mc2:
            st.metric("Final Equity", "$%s" % "{:,.2f}".format(metrics['final_equity']))
        with mc3:
            st.metric("Win Rate", "%.1f%%" % metrics['win_rate'])
        with mc4:
            st.metric("Drawdown", "%.2f%%" % metrics['max_drawdown'])
        with mc5:
            st.metric("Trades", str(metrics['total_trades']))
        with mc6:
            st.metric("Sharpe", "%.2f" % metrics['sharpe_ratio'])

        if result['equity_curve']:
            eq_df = pd.DataFrame(result['equity_curve'])
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(
                x=eq_df['timestamp'], y=eq_df['equity'],
                name='Equity', line=dict(color='#10b981', width=2.5),
                fill='tozeroy', fillcolor='rgba(16,185,129,0.06)',
            ))
            fig_eq.add_hline(y=float(bt_capital), line_dash="dot", line_color="#94a3b8", line_width=1)
            fig_eq.update_layout(
                height=350,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False, title=""),
                yaxis=dict(showgrid=True, gridcolor='#f1f5f9', title=""),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
            )
            st.plotly_chart(fig_eq, use_container_width=True)

        if result['trades']:
            with st.expander("Trade Log"):
                st.dataframe(pd.DataFrame(result['trades']), use_container_width=True, hide_index=True)
        else:
            st.info("No trades triggered during this period.")


# ═══════════════════════════════════════════════════════════════════
#  TAB 8: OPTIONS
# ═══════════════════════════════════════════════════════════════════
with main_tab8:
    st.markdown(
        '<span style="background:#f59e0b; color:#fff; padding:3px 10px; '
        'border-radius:6px; font-size:0.8rem; font-weight:600;">'
        'Coming Soon</span>',
        unsafe_allow_html=True,
    )
    st.markdown("### Options Trading")

    available, msg = options_available()
    st.info(msg)

    st.markdown("""
**What are options?**

Options are financial derivatives that give the buyer the right — but not the
obligation — to buy (call) or sell (put) an underlying asset at a specific
price (strike) before a certain date (expiration).

Key concepts:
- **Call option** — the right to *buy* at the strike price
- **Put option** — the right to *sell* at the strike price
- **Premium** — the price you pay for the option contract
- **Expiration** — the date the option expires
- **Strike price** — the price at which you can exercise

Options can be used for hedging, income generation (covered calls), or
leveraged speculation.
""")

    st.markdown(
        "📚 [Alpaca Options Trading Docs]"
        "(https://docs.alpaca.markets/docs/options-trading)"
    )

    opt_symbol = st.text_input("Check options availability", value="AAPL", key="_opt_symbol")
    if st.button("Check", key="_opt_check"):
        st.warning(get_options_chain(opt_symbol))


# ── Footer ───────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#94a3b8; font-size:0.75rem;">'
    'KhmerTrading v2.0 &nbsp;&middot;&nbsp; Private Family Use Only &nbsp;&middot;&nbsp; Not Financial Advice'
    '</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="text-align:center; color:#cbd5e1; font-size:0.65rem; max-width:600px; margin:0 auto;">'
    'This platform is for private, personal family investment use only. '
    'It is not a registered investment advisor, broker-dealer, or financial service. '
    'No investment advice is being offered. All trading involves risk of loss. '
    'Past performance does not guarantee future results.'
    '</p>',
    unsafe_allow_html=True,
)
