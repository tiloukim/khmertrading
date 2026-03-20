"""Market status — shows if market is open/closed and countdown timer."""

import streamlit as st
from datetime import datetime
import pytz

ET = pytz.timezone('US/Eastern')

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MIN = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MIN = 0


def get_market_status():
    """Get current market status with countdown."""
    now = datetime.now(ET)
    weekday = now.weekday()  # 0=Mon, 6=Sun
    hour = now.hour
    minute = now.minute
    current_mins = hour * 60 + minute
    open_mins = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MIN
    close_mins = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MIN

    is_weekend = weekday >= 5

    if is_weekend:
        if weekday == 5:  # Saturday
            days_until = 2
        else:  # Sunday
            days_until = 1
        return {
            'is_open': False,
            'status': 'Closed (Weekend)',
            'countdown': f'Opens Monday 9:30 AM ET',
            'emoji': '🔴',
            'time_et': now.strftime('%I:%M %p ET'),
        }

    if current_mins < open_mins:
        # Pre-market
        mins_left = open_mins - current_mins
        hours_left = mins_left // 60
        mins_remaining = mins_left % 60
        if hours_left > 0:
            countdown = f'Opens in {hours_left}h {mins_remaining}m'
        else:
            countdown = f'Opens in {mins_remaining}m'
        return {
            'is_open': False,
            'status': 'Pre-Market',
            'countdown': countdown,
            'emoji': '🟡',
            'time_et': now.strftime('%I:%M %p ET'),
        }

    elif current_mins >= close_mins:
        # After hours
        if weekday == 4:  # Friday
            countdown = 'Opens Monday 9:30 AM ET'
        else:
            countdown = 'Opens tomorrow 9:30 AM ET'
        return {
            'is_open': False,
            'status': 'After Hours',
            'countdown': countdown,
            'emoji': '🟡',
            'time_et': now.strftime('%I:%M %p ET'),
        }

    else:
        # Market is open
        mins_left = close_mins - current_mins
        hours_left = mins_left // 60
        mins_remaining = mins_left % 60
        if hours_left > 0:
            countdown = f'Closes in {hours_left}h {mins_remaining}m'
        else:
            countdown = f'Closes in {mins_remaining}m'
        return {
            'is_open': True,
            'status': 'Market Open',
            'countdown': countdown,
            'emoji': '🟢',
            'time_et': now.strftime('%I:%M %p ET'),
        }


def render_market_status():
    """Render market status bar."""
    status = get_market_status()

    if status['is_open']:
        bg = '#d1fae5'
        border = '#6ee7b7'
        color = '#065f46'
    elif status['status'] == 'Pre-Market' or status['status'] == 'After Hours':
        bg = '#fef3c7'
        border = '#fcd34d'
        color = '#92400e'
    else:
        bg = '#fee2e2'
        border = '#fca5a5'
        color = '#991b1b'

    st.markdown(
        f'<div style="background:{bg}; border:1px solid {border}; border-radius:10px; padding:8px 14px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:4px;">'
        f'<span style="font-weight:700; color:{color}; font-size:0.85rem;">{status["emoji"]} {status["status"]}</span>'
        f'<span style="color:{color}; font-size:0.75rem;">{status["countdown"]}</span>'
        f'<span style="color:{color}; font-size:0.7rem;">{status["time_et"]} | Crypto: 24/7</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
