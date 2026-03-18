"""News sentiment analysis using Alpaca's built-in news API."""

from config import get_api

BULLISH_KEYWORDS = [
    "surge", "rally", "beat", "upgrade", "bullish", "growth", "profit",
    "record", "soar", "gain", "buy", "outperform", "breakout", "strong",
]

BEARISH_KEYWORDS = [
    "crash", "plunge", "miss", "downgrade", "bearish", "loss", "decline",
    "fall", "sell", "underperform", "weak", "cut", "layoff", "warning",
]


def _score_text(text):
    # type: (str) -> int
    """Score a block of text: +1 per bullish keyword, -1 per bearish keyword."""
    lower = text.lower()
    score = 0
    for kw in BULLISH_KEYWORDS:
        if kw in lower:
            score += 1
    for kw in BEARISH_KEYWORDS:
        if kw in lower:
            score -= 1
    return score


def _clean_symbol(symbol):
    # type: (str) -> str
    """Strip /USD for crypto symbols so the news API can find them."""
    if "/" in symbol:
        return symbol.split("/")[0]
    return symbol


def get_sentiment(symbol, limit=10):
    # type: (str, int) -> dict
    """Return sentiment analysis dict for a symbol.

    Returns:
        {
            'score': float (-1 to 1 normalized),
            'articles': list of {'headline', 'timestamp', 'sentiment', 'score'},
            'summary': str ('Bullish' | 'Bearish' | 'Neutral'),
        }
    """
    neutral_default = {
        'score': 0.0,
        'articles': [],
        'summary': 'Neutral',
    }

    try:
        api = get_api()
        clean = _clean_symbol(symbol)
        news = api.get_news(clean, limit=limit)

        if not news:
            return neutral_default

        articles = []
        total_score = 0

        for article in news:
            headline = getattr(article, 'headline', '') or ''
            summary = getattr(article, 'summary', '') or ''
            timestamp = str(getattr(article, 'created_at', ''))

            text = headline + ' ' + summary
            article_score = _score_text(text)
            total_score += article_score

            if article_score > 0:
                sentiment_label = 'bullish'
            elif article_score < 0:
                sentiment_label = 'bearish'
            else:
                sentiment_label = 'neutral'

            articles.append({
                'headline': headline,
                'timestamp': timestamp,
                'sentiment': sentiment_label,
                'score': article_score,
            })

        # Normalize: divide by (limit * 3) and clamp to [-1, 1]
        raw = total_score / (limit * 3) if limit > 0 else 0.0
        normalized = max(-1.0, min(1.0, raw))

        if normalized > 0.15:
            summary_label = 'Bullish'
        elif normalized < -0.15:
            summary_label = 'Bearish'
        else:
            summary_label = 'Neutral'

        return {
            'score': normalized,
            'articles': articles,
            'summary': summary_label,
        }

    except Exception:
        return neutral_default
