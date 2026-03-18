import pandas as pd
from strategy import fetch_bars


def get_correlation_matrix(symbols, days=30):
    """Calculate price correlation matrix for a list of stock symbols.

    Parameters
    ----------
    symbols : list[str]
        Stock symbols (crypto symbols with '/' are skipped).
    days : int
        Number of trading days to use.

    Returns
    -------
    pd.DataFrame or None
        Correlation matrix with symbols as both index and columns.
    """
    # Skip crypto symbols — different data format
    stock_symbols = [s for s in symbols if '/' not in s]
    if len(stock_symbols) < 2:
        return None

    price_data = {}
    for symbol in stock_symbols:
        try:
            bars = fetch_bars(symbol, hours=days, timeframe='1D')
            if bars is not None and len(bars) >= 5:
                prices = bars.set_index('timestamp')['close']
                prices.name = symbol
                price_data[symbol] = prices
        except Exception:
            continue

    if len(price_data) < 2:
        return None

    df = pd.DataFrame(price_data)
    # Forward-fill then drop remaining NaN rows so symbols with
    # slightly different trading calendars still align
    df = df.ffill().dropna()

    if len(df) < 5:
        return None

    return df.corr()
