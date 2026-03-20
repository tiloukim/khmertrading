"""Scheduled Telegram reports — sends automatically at key times."""

import streamlit as st
from datetime import datetime
import pytz
from reports import generate_daily_report
from notifications import send_telegram


ET = pytz.timezone('US/Eastern')

# Report schedule (Eastern Time)
REPORT_TIMES = {
    'morning': {'hour': 9, 'minute': 30, 'label': 'Morning Market Open'},
    'close': {'hour': 16, 'minute': 5, 'label': 'Market Close Summary'},
}


def _today_key(name):
    """Generate a unique key for today's report."""
    now = datetime.now(ET)
    return f"report_sent_{name}_{now.strftime('%Y-%m-%d')}"


def check_and_send_scheduled_reports():
    """Check if it's time to send a scheduled report. Call this on each page load/refresh."""
    now = datetime.now(ET)
    current_hour = now.hour
    current_minute = now.minute
    weekday = now.weekday()  # 0=Monday, 6=Sunday

    # Skip weekends for stock reports (crypto is 24/7 but reports are less useful on weekends)
    if weekday > 4:
        return

    for name, schedule in REPORT_TIMES.items():
        key = _today_key(name)

        # Already sent today?
        if st.session_state.get(key):
            continue

        # Check if within the time window (within 10 minutes of scheduled time)
        target_hour = schedule['hour']
        target_minute = schedule['minute']

        # Convert to minutes since midnight for easy comparison
        current_mins = current_hour * 60 + current_minute
        target_mins = target_hour * 60 + target_minute

        if 0 <= (current_mins - target_mins) <= 10:
            # Time to send!
            try:
                report = generate_daily_report()
                header = f"📋 {schedule['label']} Report\n"
                header += f"📅 {now.strftime('%b %d, %Y %I:%M %p ET')}\n\n"
                full_msg = header + report

                if send_telegram(full_msg):
                    st.session_state[key] = True
                    print(f"Scheduled report '{name}' sent at {now.strftime('%I:%M %p ET')}")
            except Exception as e:
                print(f"Scheduled report '{name}' failed: {e}")
