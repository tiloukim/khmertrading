import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import get_api, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, REPORT_EMAIL
from trade_log import get_trades
from alerts import get_alerts


def generate_daily_report():
    # type: () -> str
    """Generate a formatted daily report string."""
    lines = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines.append("=" * 60)
    lines.append("  KhmerTrading Daily Report")
    lines.append("  Generated: {}".format(now))
    lines.append("=" * 60)
    lines.append("")

    # Account summary
    try:
        api = get_api()
        account = api.get_account()
        equity = float(account.equity)
        cash = float(account.cash)
        portfolio_value = float(account.portfolio_value)
        initial = 100000.0
        total_pl = equity - initial
        total_pl_pct = (total_pl / initial) * 100

        lines.append("--- Account Summary ---")
        lines.append("  Equity:         ${:,.2f}".format(equity))
        lines.append("  Cash:           ${:,.2f}".format(cash))
        lines.append("  Portfolio:      ${:,.2f}".format(portfolio_value))
        lines.append("  P/L:            ${:,.2f} ({:+.2f}%)".format(total_pl, total_pl_pct))
        lines.append("")

        # Open positions
        positions = api.list_positions()
        lines.append("--- Open Positions ({}) ---".format(len(positions)))
        if positions:
            for pos in positions:
                sym = pos.symbol
                qty = pos.qty
                entry = float(pos.avg_entry_price)
                current = float(pos.current_price)
                unrealized = float(pos.unrealized_pl)
                lines.append("  {} | Qty: {} | Entry: ${:,.2f} | Now: ${:,.2f} | P/L: ${:,.2f}".format(
                    sym, qty, entry, current, unrealized))
        else:
            lines.append("  No open positions")
        lines.append("")
    except Exception as e:
        lines.append("  [Could not fetch account data: {}]".format(e))
        lines.append("")

    # Recent trades
    trades = get_trades(limit=10)
    lines.append("--- Recent Trades ({}) ---".format(len(trades)))
    if trades:
        for t in trades:
            lines.append("  {} {} {} x{} ({}) - {}".format(
                t.get('timestamp', '?')[:19],
                t.get('side', '?').upper(),
                t.get('symbol', '?'),
                t.get('qty', '?'),
                t.get('order_type', '?'),
                t.get('status', '?'),
            ))
    else:
        lines.append("  No recent trades")
    lines.append("")

    # Active alerts
    alerts = get_alerts()
    pending = [a for a in alerts if not a.get('triggered', False)]
    triggered = [a for a in alerts if a.get('triggered', False)]
    lines.append("--- Alerts (Pending: {}, Triggered: {}) ---".format(len(pending), len(triggered)))
    for a in pending:
        lines.append("  [PENDING] {} {} ${:,.2f}".format(
            a['symbol'], a['direction'], a['target']))
    for a in triggered:
        lines.append("  [TRIGGERED] {} {} ${:,.2f}".format(
            a['symbol'], a['direction'], a['target']))
    if not alerts:
        lines.append("  No active alerts")
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def send_email_report(to_email, subject, body):
    # type: (str, str, str) -> bool
    """Send an email report via SMTP. Returns True on success."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        return False

    try:
        port = int(SMTP_PORT) if SMTP_PORT else 587
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_HOST, port)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP error: {e}")
        raise


def send_daily_report():
    # type: () -> bool
    """Generate and send the daily report via email and/or Telegram. Returns True if any channel succeeds."""
    from notifications import send_telegram

    report = generate_daily_report()
    success = False

    # Try Telegram
    try:
        if send_telegram(report):
            success = True
    except Exception:
        pass

    # Try Email
    if REPORT_EMAIL:
        try:
            subject = "KhmerTrading Report - {}".format(datetime.now().strftime('%Y-%m-%d'))
            if send_email_report(REPORT_EMAIL, subject, report):
                success = True
        except Exception:
            pass

    return success
