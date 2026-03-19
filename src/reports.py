import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import get_api, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, REPORT_EMAIL
from trade_log import get_trades
from alerts import get_alerts


def generate_daily_report():
    # type: () -> str
    """Generate a clean, emoji-formatted daily report for Telegram."""
    now = datetime.now().strftime('%b %d, %Y  %I:%M %p')
    lines = []

    lines.append("📊 KhmerTrading Report")
    lines.append("📅 {}".format(now))
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
        pl_emoji = "🟢" if total_pl >= 0 else "🔴"

        lines.append("💰 Account Summary")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("Equity:    ${:,.2f}".format(equity))
        lines.append("Cash:       ${:,.2f}".format(cash))
        lines.append("Portfolio: ${:,.2f}".format(portfolio_value))
        lines.append("{} P/L:       ${:,.2f} ({:+.2f}%)".format(pl_emoji, total_pl, total_pl_pct))
        lines.append("")

        # Open positions
        positions = api.list_positions()
        lines.append("📈 Positions ({})".format(len(positions)))
        lines.append("━━━━━━━━━━━━━━━━━━")
        if positions:
            for pos in positions:
                sym = pos.symbol
                qty = float(pos.qty) if '.' in str(pos.qty) else int(pos.qty)
                current = float(pos.current_price)
                unrealized = float(pos.unrealized_pl)
                pos_emoji = "🟢" if unrealized >= 0 else "🔴"
                lines.append("{} {} × {}  →  ${:,.2f}  ({:+,.2f})".format(
                    pos_emoji, sym, qty, current, unrealized))
        else:
            lines.append("No open positions")
        lines.append("")
    except Exception as e:
        lines.append("⚠️ Could not fetch account: {}".format(e))
        lines.append("")

    # Recent trades
    trades = get_trades(limit=5)
    if trades:
        lines.append("🔄 Recent Trades")
        lines.append("━━━━━━━━━━━━━━━━━━")
        for t in trades:
            side = t.get('side', '?').upper()
            side_emoji = "🟢 BUY" if side == "BUY" else "🔴 SELL"
            lines.append("{}  {} × {}".format(
                side_emoji,
                t.get('symbol', '?'),
                t.get('qty', '?'),
            ))
        lines.append("")

    # Active alerts
    alerts = get_alerts()
    pending = [a for a in alerts if not a.get('triggered', False)]
    triggered = [a for a in alerts if a.get('triggered', False)]
    if pending or triggered:
        lines.append("🔔 Alerts")
        lines.append("━━━━━━━━━━━━━━━━━━")
        for a in triggered:
            lines.append("⚡ {} hit ${:,.2f}".format(a['symbol'], a['target']))
        for a in pending:
            lines.append("⏳ {} {} ${:,.2f}".format(a['symbol'], a['direction'], a['target']))
        lines.append("")

    lines.append("— KhmerTrading • Private Family Use Only")

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
        else:
            print("Telegram send_telegram returned False")
    except Exception as e:
        print(f"Telegram exception: {e}")

    # Skip email for now — Railway SMTP is unreliable
    # Email can be re-enabled later if needed

    return success
