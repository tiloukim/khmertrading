"""Stock and crypto news fetcher using Yahoo Finance."""

import streamlit as st
import yfinance as yf


@st.cache_data(ttl=300)
def get_stock_news(symbol, max_items=5):
    """Fetch recent news for a symbol from Yahoo Finance.
    Returns list of dicts with title, link, publisher, date.
    """
    try:
        # Convert crypto symbol format
        yf_symbol = symbol
        if '/' in symbol:
            yf_symbol = symbol.replace('/', '-')

        ticker = yf.Ticker(yf_symbol)
        news = ticker.news

        if not news:
            return []

        results = []
        for item in news[:max_items]:
            results.append({
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'publisher': item.get('publisher', ''),
                'date': item.get('providerPublishTime', ''),
                'type': item.get('type', ''),
            })

        return results
    except Exception as e:
        print(f"News fetch error for {symbol}: {e}")
        return []


@st.cache_data(ttl=300)
def get_market_news(max_items=8):
    """Fetch general market news from major tickers."""
    all_news = []
    seen_titles = set()

    for symbol in ['SPY', 'QQQ', 'BTC-USD']:
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news or []
            for item in news[:5]:
                title = item.get('title', '')
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    all_news.append({
                        'title': title,
                        'link': item.get('link', ''),
                        'publisher': item.get('publisher', ''),
                        'date': item.get('providerPublishTime', ''),
                    })
        except Exception:
            continue

    return all_news[:max_items]


def render_news_section():
    """Render market news section."""
    st.markdown("### Market News")
    st.caption("Latest headlines from Yahoo Finance")

    news = get_market_news()
    if news:
        for item in news:
            publisher = item.get('publisher', '')
            st.markdown(
                f'<div style="padding:6px 0; border-bottom:1px solid #f1f5f9;">'
                f'<a href="{item["link"]}" target="_blank" style="text-decoration:none; color:#0f172a; font-size:0.85rem; font-weight:500;">{item["title"]}</a>'
                f'<br><span style="color:#94a3b8; font-size:0.7rem;">{publisher}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No news available right now.")


def render_symbol_news(symbol):
    """Render news for a specific symbol."""
    news = get_stock_news(symbol)
    if news:
        for item in news:
            publisher = item.get('publisher', '')
            st.markdown(
                f'<div style="padding:4px 0; border-bottom:1px solid #f1f5f9;">'
                f'<a href="{item["link"]}" target="_blank" style="text-decoration:none; color:#0f172a; font-size:0.8rem; font-weight:500;">{item["title"]}</a>'
                f'<br><span style="color:#94a3b8; font-size:0.65rem;">{publisher}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("No recent news for this symbol.")
