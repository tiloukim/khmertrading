"""Stock and crypto news fetcher using Yahoo Finance."""

import streamlit as st
import yfinance as yf


def _parse_news_item(item):
    """Parse a Yahoo Finance news item (handles both old and new API format)."""
    # New format: nested under 'content'
    if 'content' in item:
        content = item['content']
        title = content.get('title', '')
        publisher = content.get('provider', {}).get('displayName', '')
        link = ''
        click_url = content.get('clickThroughUrl', {})
        if click_url:
            link = click_url.get('url', '')
        if not link:
            canon = content.get('canonicalUrl', {})
            link = canon.get('url', '') if canon else ''
        return {'title': title, 'link': link, 'publisher': publisher}

    # Old format: flat dict
    return {
        'title': item.get('title', ''),
        'link': item.get('link', ''),
        'publisher': item.get('publisher', ''),
    }


@st.cache_data(ttl=300)
def get_stock_news(symbol, max_items=5):
    """Fetch recent news for a symbol from Yahoo Finance."""
    try:
        yf_symbol = symbol.replace('/', '-') if '/' in symbol else symbol
        ticker = yf.Ticker(yf_symbol)
        news = ticker.news

        if not news:
            return []

        results = []
        for item in news[:max_items]:
            parsed = _parse_news_item(item)
            if parsed['title']:
                results.append(parsed)

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
                parsed = _parse_news_item(item)
                title = parsed['title']
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    all_news.append(parsed)
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
            link = item.get('link', '')
            title = item.get('title', '')
            if link:
                st.markdown(
                    f'<div style="padding:6px 0; border-bottom:1px solid #f1f5f9;">'
                    f'<a href="{link}" target="_blank" style="text-decoration:none; color:#0f172a; font-size:0.85rem; font-weight:500;">{title}</a>'
                    f'<br><span style="color:#94a3b8; font-size:0.7rem;">{publisher}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="padding:6px 0; border-bottom:1px solid #f1f5f9;">'
                    f'<span style="color:#0f172a; font-size:0.85rem; font-weight:500;">{title}</span>'
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
            link = item.get('link', '')
            title = item.get('title', '')
            if link:
                st.markdown(
                    f'<div style="padding:4px 0; border-bottom:1px solid #f1f5f9;">'
                    f'<a href="{link}" target="_blank" style="text-decoration:none; color:#0f172a; font-size:0.8rem; font-weight:500;">{title}</a>'
                    f'<br><span style="color:#94a3b8; font-size:0.65rem;">{publisher}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="padding:4px 0; border-bottom:1px solid #f1f5f9;">'
                    f'<span style="color:#0f172a; font-size:0.8rem; font-weight:500;">{title}</span>'
                    f'<br><span style="color:#94a3b8; font-size:0.65rem;">{publisher}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.caption("No recent news for this symbol.")
