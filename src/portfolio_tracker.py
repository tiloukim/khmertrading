import os
import sqlite3
from datetime import datetime, timedelta

import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'trades.db')


def init_portfolio_db():
    """Create equity_snapshots table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS equity_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equity REAL,
            cash REAL,
            portfolio_value REAL,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


def record_snapshot(equity, cash, portfolio_value):
    """Insert an equity snapshot."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO equity_snapshots (equity, cash, portfolio_value, timestamp) "
        "VALUES (?, ?, ?, ?)",
        (float(equity), float(cash), float(portfolio_value),
         datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_snapshots_df(days=30):
    """Return equity snapshots from the last N days as a DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    df = pd.read_sql_query(
        "SELECT equity, cash, portfolio_value, timestamp "
        "FROM equity_snapshots WHERE timestamp >= ? ORDER BY timestamp",
        conn,
        params=(cutoff,),
    )
    conn.close()
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


# Initialize on import
init_portfolio_db()
