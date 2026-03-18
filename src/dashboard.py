from config import get_api


def show_dashboard():
    api = get_api()
    account = api.get_account()
    positions = api.list_positions()

    # Header
    print("=" * 70)
    print("  KHMERTRADING - Portfolio Dashboard")
    print("=" * 70)

    # Account Summary
    cash = float(account.cash)
    equity = float(account.equity)
    portfolio_value = float(account.portfolio_value)
    buying_power = float(account.buying_power)

    print(f"\n  Account Status:   {account.status}")
    print(f"  Cash:             ${cash:>12,.2f}")
    print(f"  Portfolio Value:  ${portfolio_value:>12,.2f}")
    print(f"  Equity:           ${equity:>12,.2f}")
    print(f"  Buying Power:     ${buying_power:>12,.2f}")

    # Positions
    print(f"\n{'─' * 70}")
    print(f"  Open Positions ({len(positions)})")
    print(f"{'─' * 70}")

    if not positions:
        print(f"\n  No open positions. Your portfolio is empty.")
        print(f"  Use execution.py to place your first trade!")
        print(f"  Example: python execution.py buy AAPL 10")
    else:
        # Table header
        print(f"\n  {'Symbol':<8} {'Qty':>6} {'Avg Cost':>10} {'Current':>10} {'Mkt Value':>12} {'P/L ($)':>10} {'P/L (%)':>9}")
        print(f"  {'─'*8} {'─'*6} {'─'*10} {'─'*10} {'─'*12} {'─'*10} {'─'*9}")

        total_pl = 0
        total_market_value = 0

        for pos in positions:
            symbol = pos.symbol
            qty = int(pos.qty)
            avg_cost = float(pos.avg_entry_price)
            current = float(pos.current_price)
            market_value = float(pos.market_value)
            pl = float(pos.unrealized_pl)
            pl_pct = float(pos.unrealized_plpc) * 100

            total_pl += pl
            total_market_value += market_value

            # Color indicator
            indicator = "▲" if pl >= 0 else "▼"

            print(f"  {symbol:<8} {qty:>6} ${avg_cost:>9,.2f} ${current:>9,.2f} ${market_value:>11,.2f} {indicator}${abs(pl):>8,.2f} {pl_pct:>+8.2f}%")

        # Totals
        print(f"  {'─'*8} {'─'*6} {'─'*10} {'─'*10} {'─'*12} {'─'*10} {'─'*9}")
        total_indicator = "▲" if total_pl >= 0 else "▼"
        total_pl_pct = (total_pl / (total_market_value - total_pl) * 100) if (total_market_value - total_pl) != 0 else 0
        print(f"  {'TOTAL':<8} {'':>6} {'':>10} {'':>10} ${total_market_value:>11,.2f} {total_indicator}${abs(total_pl):>8,.2f} {total_pl_pct:>+8.2f}%")

    # Recent Orders
    print(f"\n{'─' * 70}")
    print(f"  Recent Orders (last 5)")
    print(f"{'─' * 70}")

    orders = api.list_orders(limit=5, status='all')
    if not orders:
        print(f"\n  No orders placed yet.")
    else:
        print(f"\n  {'Side':<6} {'Symbol':<8} {'Qty':>6} {'Type':<8} {'Status':<12} {'Submitted'}")
        print(f"  {'─'*6} {'─'*8} {'─'*6} {'─'*8} {'─'*12} {'─'*20}")
        for o in orders:
            submitted = o.submitted_at[:19] if o.submitted_at else 'N/A'
            print(f"  {o.side.upper():<6} {o.symbol:<8} {o.qty:>6} {o.type:<8} {o.status:<12} {submitted}")

    print(f"\n{'=' * 70}\n")


if __name__ == '__main__':
    show_dashboard()
