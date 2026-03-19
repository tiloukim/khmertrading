"""Market scanner — finds the most profitable stocks and crypto based on technical analysis."""

import streamlit as st
from yahoo_data import get_live_price, fetch_yahoo_bars
from strategy import combined_signal, calculate_rsi, calculate_ma, MA_PERIOD


# Symbols to scan
TOP_STOCKS = [
    "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOG", "META", "AMD", "NFLX", "SPY",
    "QQQ", "PLTR", "COIN", "SOFI", "UBER", "CRM", "INTC", "BA", "DIS", "PYPL",
    "SQ", "SHOP", "ROKU", "SNAP", "MARA", "RIOT", "HOOD", "NIO", "RIVN", "LCID",
]

TOP_CRYPTO = [
    "BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "SHIB/USD", "PEPE/USD",
    "AVAX/USD", "LINK/USD", "LTC/USD", "UNI/USD", "AAVE/USD", "DOT/USD",
    "NEAR/USD", "MATIC/USD", "ARB/USD",
]


@st.cache_data(ttl=120)
def scan_symbols(symbols):
    """Scan a list of symbols and return sorted results by opportunity score."""
    results = []

    for symbol in symbols:
        try:
            # Get price data
            price_data = get_live_price(symbol)
            if not price_data or not price_data['price']:
                continue

            price = price_data['price']
            change_pct = price_data['change_pct']

            # Get bars for technical analysis
            bars = fetch_yahoo_bars(symbol, timeframe='1H')
            if bars is None or len(bars) < MA_PERIOD:
                continue

            # Get signal
            sig = combined_signal(bars)
            signal = sig['signal']
            confidence = sig['confidence']
            reasons = sig['reasons']

            # Calculate additional metrics
            rsi = calculate_rsi(bars['close']).iloc[-1]
            ma = calculate_ma(bars['close']).iloc[-1]
            price_vs_ma = ((price - ma) / ma) * 100 if ma > 0 else 0

            # Calculate 7-day momentum (using available bars)
            if len(bars) >= 7:
                week_ago_price = bars['close'].iloc[-7]
                week_change = ((price - week_ago_price) / week_ago_price) * 100
            else:
                week_change = change_pct

            # Volume trend
            if len(bars) >= 20:
                avg_vol = bars['volume'].tail(20).mean()
                current_vol = bars['volume'].iloc[-1]
                vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
            else:
                vol_ratio = 1

            # Opportunity score (higher = better opportunity)
            score = 0

            # BUY signals get positive score
            if signal == 'BUY':
                score += confidence
            elif signal == 'SELL':
                score -= confidence * 0.5  # Penalize sell signals less

            # Oversold = buying opportunity
            if rsi < 30:
                score += 30
            elif rsi < 40:
                score += 15

            # Below MA = potential bounce
            if price_vs_ma < -3:
                score += 20
            elif price_vs_ma < -1:
                score += 10

            # High volume = conviction
            if vol_ratio > 1.5:
                score += 15

            # Positive weekly momentum
            if week_change > 5:
                score += 10
            elif week_change > 2:
                score += 5

            results.append({
                'symbol': symbol,
                'price': price,
                'change_pct': change_pct,
                'week_change': week_change,
                'rsi': rsi,
                'signal': signal,
                'confidence': confidence,
                'score': score,
                'reasons': reasons,
                'vol_ratio': vol_ratio,
                'price_vs_ma': price_vs_ma,
            })

        except Exception as e:
            continue

    # Sort by score (highest first)
    results.sort(key=lambda x: x['score'], reverse=True)
    return results


def render_scanner():
    """Render the market scanner UI."""
    st.caption("AI scans 45+ stocks and crypto to find the best trading opportunities")

    scan_tab1, scan_tab2, scan_tab3 = st.tabs(["Top Opportunities", "Stock Scanner", "Crypto Scanner"])

    with scan_tab1:
        st.markdown("### Best Opportunities Right Now")
        st.caption("Combined ranking of stocks and crypto by AI opportunity score")

        with st.spinner("Scanning markets..."):
            all_results = scan_symbols(TOP_STOCKS + TOP_CRYPTO)

        if all_results:
            # Top BUY opportunities
            buys = [r for r in all_results if r['signal'] == 'BUY' and r['score'] > 30]
            if buys:
                st.markdown("#### 🟢 Strong BUY Signals")
                for r in buys[:5]:
                    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                    with col1:
                        st.markdown(f"**{r['symbol']}**")
                        st.caption(f"${r['price']:,.2f}")
                    with col2:
                        day_color = "#10b981" if r['change_pct'] >= 0 else "#ef4444"
                        week_color = "#10b981" if r['week_change'] >= 0 else "#ef4444"
                        st.markdown(
                            f'<span style="color:{day_color}; font-size:0.85rem;">{r["change_pct"]:+.2f}% today</span><br>'
                            f'<span style="color:{week_color}; font-size:0.75rem;">{r["week_change"]:+.1f}% this week</span>',
                            unsafe_allow_html=True,
                        )
                    with col3:
                        st.markdown(f'<span style="font-size:0.85rem;">RSI {r["rsi"]:.0f}</span>', unsafe_allow_html=True)
                    with col4:
                        st.markdown(f'<span style="color:#10b981; font-weight:700;">Score {r["score"]:.0f}</span>', unsafe_allow_html=True)
                    if r['reasons']:
                        with st.expander(f"Why {r['symbol']}?"):
                            for reason in r['reasons']:
                                st.caption(f"• {reason}")
                    st.markdown("---")
            else:
                st.info("No strong BUY signals detected right now. Market may be neutral or overbought.")

            # Top SELL warnings (for positions you might hold)
            sells = [r for r in all_results if r['signal'] == 'SELL' and r['confidence'] > 40]
            if sells:
                st.markdown("#### 🔴 SELL Warnings")
                for r in sells[:5]:
                    st.markdown(
                        f"**{r['symbol']}** — ${r['price']:,.2f} — "
                        f"RSI {r['rsi']:.0f} — Confidence {r['confidence']:.0f}%"
                    )

            # Market overview
            st.markdown("#### 📊 Market Overview")
            buy_count = len([r for r in all_results if r['signal'] == 'BUY'])
            sell_count = len([r for r in all_results if r['signal'] == 'SELL'])
            hold_count = len([r for r in all_results if r['signal'] == 'HOLD'])
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Scanned", len(all_results))
            with c2:
                st.metric("BUY Signals", buy_count)
            with c3:
                st.metric("SELL Signals", sell_count)
            with c4:
                st.metric("HOLD", hold_count)

    with scan_tab2:
        st.markdown("### Stock Scanner")
        with st.spinner("Scanning stocks..."):
            stock_results = scan_symbols(TOP_STOCKS)

        if stock_results:
            for r in stock_results:
                if r['signal'] == 'BUY':
                    signal_html = '<span style="background:#d1fae5; color:#065f46; padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:700;">BUY</span>'
                elif r['signal'] == 'SELL':
                    signal_html = '<span style="background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:700;">SELL</span>'
                else:
                    signal_html = '<span style="background:#fef3c7; color:#92400e; padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:700;">HOLD</span>'

                day_color = "#10b981" if r['change_pct'] >= 0 else "#ef4444"

                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.markdown(f"**{r['symbol']}** — ${r['price']:,.2f}")
                with col2:
                    st.markdown(f'<span style="color:{day_color};">{r["change_pct"]:+.2f}%</span> | RSI {r["rsi"]:.0f}', unsafe_allow_html=True)
                with col3:
                    st.markdown(signal_html, unsafe_allow_html=True)
                with col4:
                    st.caption(f"Score: {r['score']:.0f}")

    with scan_tab3:
        st.markdown("### Crypto Scanner")
        with st.spinner("Scanning crypto..."):
            crypto_results = scan_symbols(TOP_CRYPTO)

        if crypto_results:
            for r in crypto_results:
                if r['signal'] == 'BUY':
                    signal_html = '<span style="background:#d1fae5; color:#065f46; padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:700;">BUY</span>'
                elif r['signal'] == 'SELL':
                    signal_html = '<span style="background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:700;">SELL</span>'
                else:
                    signal_html = '<span style="background:#fef3c7; color:#92400e; padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:700;">HOLD</span>'

                day_color = "#10b981" if r['change_pct'] >= 0 else "#ef4444"

                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.markdown(f"**{r['symbol']}** — ${r['price']:,.2f}")
                with col2:
                    st.markdown(f'<span style="color:{day_color};">{r["change_pct"]:+.2f}%</span> | RSI {r["rsi"]:.0f}', unsafe_allow_html=True)
                with col3:
                    st.markdown(signal_html, unsafe_allow_html=True)
                with col4:
                    st.caption(f"Score: {r['score']:.0f}")
