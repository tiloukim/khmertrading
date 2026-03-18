import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'trades.db')


def init_db():
    """Create trades table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            side TEXT,
            qty REAL,
            order_type TEXT,
            order_id TEXT,
            status TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_trade(symbol, side, qty, order_type, order_id, status):
    """Insert a trade record."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO trades (symbol, side, qty, order_type, order_id, status, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (symbol, side, float(qty), order_type, str(order_id), status,
         datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_trades(limit=50):
    """Return recent trades as a list of dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()
