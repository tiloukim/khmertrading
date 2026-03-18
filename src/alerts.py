import time
import threading
from datetime import datetime
from config import get_api
from notifications import notify

# ── In-memory alert store ────────────────────────────────────────────
# Each alert: { 'symbol': str, 'target': float, 'direction': 'above'|'below', 'triggered': bool }
_alerts = []
_lock = threading.Lock()
_monitor_thread = None
_monitor_running = False

CHECK_INTERVAL = 60  # seconds


def add_alert(symbol: str, target_price: float, direction: str = 'above'):
    """Add a price alert. direction: 'above' or 'below'."""
    direction = direction.lower()
    if direction not in ('above', 'below'):
        raise ValueError("direction must be 'above' or 'below'")

    alert = {
        'symbol': symbol.upper(),
        'target': target_price,
        'direction': direction,
        'triggered': False,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    with _lock:
        _alerts.append(alert)
    print(f"🔔 Alert added: {symbol.upper()} {direction} ${target_price:,.2f}")
    return alert


def remove_alert(index: int):
    """Remove an alert by index."""
    with _lock:
        if 0 <= index < len(_alerts):
            removed = _alerts.pop(index)
            print(f"🗑️  Alert removed: {removed['symbol']} {removed['direction']} ${removed['target']:,.2f}")
            return removed
    return None


def get_alerts():
    """Return a copy of all alerts."""
    with _lock:
        return list(_alerts)


def clear_triggered():
    """Remove all triggered alerts."""
    with _lock:
        before = len(_alerts)
        _alerts[:] = [a for a in _alerts if not a['triggered']]
        removed = before - len(_alerts)
    if removed:
        print(f"🗑️  Cleared {removed} triggered alert(s)")


def _fetch_price(symbol: str):
    """Fetch the current price for a stock or crypto symbol."""
    api = get_api()
    try:
        if '/' in symbol:
            snapshots = api.get_crypto_snapshot(symbol)
            snap = snapshots[symbol] if isinstance(snapshots, dict) else snapshots
            return float(snap.latest_trade.p)
        else:
            snapshot = api.get_snapshot(symbol, feed='iex')
            if snapshot.latest_trade:
                return float(snapshot.latest_trade.price)
            return float(snapshot.daily_bar.close)
    except Exception as e:
        print(f"⚠️  Could not fetch price for {symbol}: {e}")
        return None


def check_alerts():
    """Check all alerts against current prices. Returns list of newly triggered alerts."""
    triggered = []
    with _lock:
        pending = [(i, a) for i, a in enumerate(_alerts) if not a['triggered']]

    # Fetch prices outside the lock
    for i, alert in pending:
        price = _fetch_price(alert['symbol'])
        if price is None:
            continue

        hit = False
        if alert['direction'] == 'above' and price >= alert['target']:
            hit = True
        elif alert['direction'] == 'below' and price <= alert['target']:
            hit = True

        if hit:
            with _lock:
                if not _alerts[i]['triggered']:
                    _alerts[i]['triggered'] = True
                    _alerts[i]['triggered_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    _alerts[i]['triggered_price'] = price
            _print_terminal_alert(alert, price)
            symbol = alert['symbol']
            target = alert['target']
            direction = alert['direction']
            notify("\U0001f6a8 PRICE ALERT: {} hit ${:,.2f} (target: {} ${:,.2f})".format(
                symbol, price, direction, target))
            triggered.append({**alert, 'triggered_price': price})

    return triggered


def _print_terminal_alert(alert: dict, current_price: float):
    """Print a bold, colorful alert to the terminal."""
    symbol = alert['symbol']
    target = alert['target']
    direction = alert['direction']

    print()
    print("\033[1;33m" + "=" * 60 + "\033[0m")
    print("\033[1;31m" + "  🚨🚨🚨  PRICE ALERT TRIGGERED  🚨🚨🚨" + "\033[0m")
    print("\033[1;33m" + "=" * 60 + "\033[0m")
    print(f"\033[1m  Symbol:        {symbol}\033[0m")
    print(f"\033[1m  Target:        ${target:,.2f} ({direction})\033[0m")
    print(f"\033[1m  Current Price: ${current_price:,.2f}\033[0m")
    print(f"\033[1m  Time:          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\033[0m")
    print("\033[1;33m" + "=" * 60 + "\033[0m")
    print()


def _monitor_loop():
    """Background loop that checks alerts every CHECK_INTERVAL seconds."""
    global _monitor_running
    print(f"🔔 Alert monitor started (checking every {CHECK_INTERVAL}s)")
    while _monitor_running:
        with _lock:
            has_pending = any(not a['triggered'] for a in _alerts)
        if has_pending:
            check_alerts()
        time.sleep(CHECK_INTERVAL)
    print("🔔 Alert monitor stopped")


def start_monitor():
    """Start the background alert monitor thread."""
    global _monitor_thread, _monitor_running
    if _monitor_running:
        print("🔔 Monitor already running")
        return
    _monitor_running = True
    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()


def stop_monitor():
    """Stop the background alert monitor thread."""
    global _monitor_running
    _monitor_running = False


# ── CLI Usage ────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python alerts.py watch NVDA above 150")
        print("  python alerts.py watch BTC/USD below 60000")
        print("  python alerts.py watch TSLA above 250 ETH/USD below 2000")
        sys.exit(1)

    # Parse pairs of: SYMBOL above/below PRICE
    args = sys.argv[1:]
    if args[0] == 'watch':
        args = args[1:]

    i = 0
    while i + 2 < len(args):
        symbol = args[i]
        direction = args[i + 1]
        target = float(args[i + 2])
        add_alert(symbol, target, direction)
        i += 3

    if not _alerts:
        print("No alerts added. Check usage.")
        sys.exit(1)

    # Run monitor in foreground
    print(f"\n📡 Monitoring {len(_alerts)} alert(s)... (Ctrl+C to stop)\n")
    start_monitor()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_monitor()
        print("\n👋 Alert monitor stopped.")
