"""Earnings calendar detection using Alpaca news API."""

from datetime import datetime, timedelta
from config import get_api

EARNINGS_KEYWORDS = [
    "earnings", "quarterly", "revenue report", "q1", "q2", "q3", "q4",
]


def _clean_symbol(symbol):
    # type: (str) -> str
    if "/" in symbol:
        return symbol.split("/")[0]
    return symbol


def get_earnings_dates(symbol):
    # type: (str) -> list
    """Scan recent news for earnings-related articles.

    Returns list of dicts: {'headline', 'date', 'is_earnings_related'}
    """
    try:
        api = get_api()
        clean = _clean_symbol(symbol)
        news = api.get_news(clean, limit=20)

        if not news:
            return []

        results = []
        for article in news:
            headline = getattr(article, 'headline', '') or ''
            created = str(getattr(article, 'created_at', ''))
            lower_headline = headline.lower()

            is_earnings = any(kw in lower_headline for kw in EARNINGS_KEYWORDS)

            results.append({
                'headline': headline,
                'date': created,
                'is_earnings_related': is_earnings,
            })

        return results

    except Exception:
        return []


def is_near_earnings(symbol, days_threshold=3):
    # type: (str, int) -> tuple
    """Check if any earnings-related news appeared within days_threshold days.

    Returns (bool, reason_string).
    """
    try:
        articles = get_earnings_dates(symbol)
        cutoff = datetime.utcnow() - timedelta(days=days_threshold)

        for article in articles:
            if not article['is_earnings_related']:
                continue

            # Try to parse the date
            date_str = article['date']
            article_dt = None
            for fmt in ('%Y-%m-%d %H:%M:%S%z', '%Y-%m-%dT%H:%M:%S%z',
                        '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
                try:
                    article_dt = datetime.strptime(date_str[:19], fmt.replace('%z', ''))
                    break
                except (ValueError, IndexError):
                    continue

            if article_dt is None:
                # If we can't parse the date but it's earnings-related,
                # still flag it (recent news from the API is likely recent)
                return (True, "Earnings-related news found: %s" % article['headline'])

            if article_dt >= cutoff:
                return (True, "Earnings-related news (%s): %s" % (
                    date_str[:10], article['headline']))

        return (False, "")

    except Exception:
        return (False, "")


def should_pause_trading(symbol):
    # type: (str) -> tuple
    """Returns (bool, reason) -- True if trading should be paused near earnings."""
    near, reason = is_near_earnings(symbol)
    if near:
        return (True, "Pausing trade for %s — %s" % (symbol, reason))
    return (False, "")
