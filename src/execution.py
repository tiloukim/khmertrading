from config import get_api
from trade_log import log_trade
from notifications import notify


def is_crypto(symbol: str) -> bool:
    """Check if a symbol is a crypto pair (e.g. BTC/USD, ETH/USD)."""
    return '/' in symbol


def market_buy(symbol: str, qty, fractional: bool = False):
    """Place a market buy order. Supports both stocks and crypto."""
    api = get_api()
    crypto = is_crypto(symbol)
    try:
        order_params = dict(
            symbol=symbol.upper(),
            side='buy',
            type='market',
            time_in_force='gtc' if crypto else 'day',
        )
        # Crypto supports fractional qty (e.g. 0.001 BTC)
        if fractional or crypto:
            order_params['qty'] = str(qty)
        else:
            order_params['qty'] = int(qty)

        order = api.submit_order(**order_params)
        label = "CRYPTO BUY" if crypto else "BUY"
        print(f"✅ {label} order placed: {qty} x {symbol.upper()}")
        print(f"   Order ID: {order.id}")
        print(f"   Status:   {order.status}")
        log_trade(symbol.upper(), 'buy', qty, 'market', order.id, order.status)
        notify("\U0001f4c8 ORDER: buy {} x {} [market] - {}".format(qty, symbol.upper(), order.status))
        return order
    except Exception as e:
        print(f"❌ BUY failed for {symbol}: {e}")
        return None


def market_sell(symbol: str, qty, fractional: bool = False):
    """Place a market sell order. Supports both stocks and crypto."""
    api = get_api()
    crypto = is_crypto(symbol)
    try:
        order_params = dict(
            symbol=symbol.upper(),
            side='sell',
            type='market',
            time_in_force='gtc' if crypto else 'day',
        )
        if fractional or crypto:
            order_params['qty'] = str(qty)
        else:
            order_params['qty'] = int(qty)

        order = api.submit_order(**order_params)
        label = "CRYPTO SELL" if crypto else "SELL"
        print(f"✅ {label} order placed: {qty} x {symbol.upper()}")
        print(f"   Order ID: {order.id}")
        print(f"   Status:   {order.status}")
        log_trade(symbol.upper(), 'sell', qty, 'market', order.id, order.status)
        notify("\U0001f4c8 ORDER: sell {} x {} [market] - {}".format(qty, symbol.upper(), order.status))
        return order
    except Exception as e:
        print(f"❌ SELL failed for {symbol}: {e}")
        return None


def limit_buy(symbol, qty, limit_price):
    """Place a limit buy order."""
    api = get_api()
    crypto = is_crypto(symbol)
    try:
        order_params = dict(
            symbol=symbol.upper(),
            side='buy',
            type='limit',
            limit_price=str(limit_price),
            time_in_force='gtc' if crypto else 'day',
            qty=str(qty) if crypto else int(qty),
        )
        order = api.submit_order(**order_params)
        print(f"✅ LIMIT BUY placed: {qty} x {symbol.upper()} @ ${limit_price}")
        print(f"   Order ID: {order.id}  Status: {order.status}")
        log_trade(symbol.upper(), 'buy', qty, 'limit', order.id, order.status)
        notify("\U0001f4c8 ORDER: buy {} x {} [limit] - {}".format(qty, symbol.upper(), order.status))
        return order
    except Exception as e:
        print(f"❌ LIMIT BUY failed for {symbol}: {e}")
        return None


def limit_sell(symbol, qty, limit_price):
    """Place a limit sell order."""
    api = get_api()
    crypto = is_crypto(symbol)
    try:
        order_params = dict(
            symbol=symbol.upper(),
            side='sell',
            type='limit',
            limit_price=str(limit_price),
            time_in_force='gtc' if crypto else 'day',
            qty=str(qty) if crypto else int(qty),
        )
        order = api.submit_order(**order_params)
        print(f"✅ LIMIT SELL placed: {qty} x {symbol.upper()} @ ${limit_price}")
        print(f"   Order ID: {order.id}  Status: {order.status}")
        log_trade(symbol.upper(), 'sell', qty, 'limit', order.id, order.status)
        notify("\U0001f4c8 ORDER: sell {} x {} [limit] - {}".format(qty, symbol.upper(), order.status))
        return order
    except Exception as e:
        print(f"❌ LIMIT SELL failed for {symbol}: {e}")
        return None


def stop_order(symbol, qty, stop_price, side='sell'):
    """Place a stop order (default sell side)."""
    api = get_api()
    crypto = is_crypto(symbol)
    try:
        order_params = dict(
            symbol=symbol.upper(),
            side=side,
            type='stop',
            stop_price=str(stop_price),
            time_in_force='gtc' if crypto else 'day',
            qty=str(qty) if crypto else int(qty),
        )
        order = api.submit_order(**order_params)
        print(f"✅ STOP {side.upper()} placed: {qty} x {symbol.upper()} @ ${stop_price}")
        print(f"   Order ID: {order.id}  Status: {order.status}")
        log_trade(symbol.upper(), side, qty, 'stop', order.id, order.status)
        notify("\U0001f4c8 ORDER: {} {} x {} [stop] - {}".format(side, qty, symbol.upper(), order.status))
        return order
    except Exception as e:
        print(f"❌ STOP {side.upper()} failed for {symbol}: {e}")
        return None


def bracket_order(symbol, qty, take_profit_price, stop_loss_price):
    """Place a bracket order (buy + take-profit + stop-loss)."""
    api = get_api()
    crypto = is_crypto(symbol)
    try:
        order_params = dict(
            symbol=symbol.upper(),
            side='buy',
            type='market',
            time_in_force='gtc' if crypto else 'day',
            order_class='bracket',
            qty=str(qty) if crypto else int(qty),
            take_profit={'limit_price': str(take_profit_price)},
            stop_loss={'stop_price': str(stop_loss_price)},
        )
        order = api.submit_order(**order_params)
        print(f"✅ BRACKET order placed: {qty} x {symbol.upper()}")
        print(f"   TP=${take_profit_price}  SL=${stop_loss_price}")
        print(f"   Order ID: {order.id}  Status: {order.status}")
        log_trade(symbol.upper(), 'buy', qty, 'bracket', order.id, order.status)
        notify("\U0001f4c8 ORDER: buy {} x {} [bracket] - {}".format(qty, symbol.upper(), order.status))
        return order
    except Exception as e:
        print(f"❌ BRACKET failed for {symbol}: {e}")
        return None


def cancel_all_orders():
    """PANIC BUTTON: Cancel all open orders immediately."""
    api = get_api()
    try:
        cancelled = api.cancel_all_orders()
        count = len(cancelled) if cancelled else 0
        print(f"🛑 PANIC: Cancelled {count} open order(s)")
        return cancelled
    except Exception as e:
        print(f"❌ Cancel all failed: {e}")
        return None


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: python execution.py <buy|sell|cancel> <SYMBOL> [QTY]")
        print("       python execution.py cancel all")
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == 'cancel':
        cancel_all_orders()
    elif action == 'buy' and len(sys.argv) >= 4:
        market_buy(sys.argv[2], int(sys.argv[3]))
    elif action == 'sell' and len(sys.argv) >= 4:
        market_sell(sys.argv[2], int(sys.argv[3]))
    else:
        print("Invalid command. Use: buy AAPL 10 | sell AAPL 10 | cancel all")
