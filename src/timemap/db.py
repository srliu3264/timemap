import sqlite3
import os
from datetime import date
from typing import List, Tuple

DB_PATH = os.path.expanduser("~/.local/share/timemap.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id INTEGER PRIMARY KEY, date TEXT, type TEXT, content TEXT, is_done INTEGER DEFAULT 0)''')

    # MIGRATION: Check if is_done exists (for old databases)
    c.execute("PRAGMA table_info(items)")
    columns = [info[1] for info in c.fetchall()]
    if 'is_done' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN is_done INTEGER DEFAULT 0")

    conn.commit()
    return conn


def add_item(item_type: str, content: str, target_date: str = None):
    if target_date is None:
        target_date = date.today().isoformat()

    conn = get_db()
    conn.execute("INSERT INTO items (date, type, content, is_done) VALUES (?, ?, ?, 0)",
                 (target_date, item_type, content))
    conn.commit()
    conn.close()


def get_items_for_date(target_date: str) -> List[Tuple]:
    conn = get_db()
    c = conn.cursor()
    # Get files and notes for specific date
    c.execute(
        "SELECT id, type, content, is_done FROM items WHERE date = ? AND type != 'todo'", (target_date,))
    items = c.fetchall()

    # Get ALL todos
    c.execute("SELECT id, type, content, is_done FROM items WHERE type = 'todo'")
    items.extend(c.fetchall())
    conn.close()
    return items


def toggle_todo_status(item_id: int):
    conn = get_db()
    conn.execute(
        "UPDATE items SET is_done = 1 - is_done WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
