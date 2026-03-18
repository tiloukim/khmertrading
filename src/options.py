"""Options trading helpers (informational only).

The alpaca-trade-api SDK does NOT support options.
Options trading requires upgrading to the newer alpaca-py SDK.
"""

from typing import Tuple


def options_available():
    # type: () -> Tuple[bool, str]
    """Check whether options trading is available.

    Returns (False, message) because the current alpaca-trade-api SDK
    does not support options.
    """
    return (
        False,
        "Options trading is not available with the current alpaca-trade-api SDK. "
        "To trade options, upgrade to the newer alpaca-py package "
        "(pip install alpaca-py) and use the alpaca.trading.client module.",
    )


def get_options_chain(symbol):
    # type: (str) -> str
    """Return an informational message about options for *symbol*.

    The alpaca-trade-api (old SDK) does not expose an options endpoint,
    so this function cannot fetch real chain data.
    """
    return (
        "Options chain for {symbol} is not available. "
        "The alpaca-trade-api SDK does not support options. "
        "To access options chains, upgrade to alpaca-py and use "
        "alpaca.trading.client.TradingClient.get_option_contracts(). "
        "See https://docs.alpaca.markets/docs/options-trading for details."
    ).format(symbol=symbol)
