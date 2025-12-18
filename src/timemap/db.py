import sqlite3
import os
import calendar
from datetime import date, timedelta
from typing import List, Tuple, Set

DB_PATH = os.path.expanduser("~/.local/share/timemap.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id INTEGER PRIMARY KEY, date TEXT, type TEXT, content TEXT, 
                  is_done INTEGER DEFAULT 0, finish_date TEXT)''')

    # MIGRATION: Ensure columns exist
    c.execute("PRAGMA table_info(items)")
    columns = [info[1] for info in c.fetchall()]
    if 'is_done' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN is_done INTEGER DEFAULT 0")
    if 'finish_date' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN finish_date TEXT")

    conn.commit()
    return conn


def add_item(item_type: str, content: str, target_date: str = None):
    if target_date is None:
        target_date = date.today().isoformat()
    conn = get_db()
    conn.execute("INSERT INTO items (date, type, content, is_done, finish_date) VALUES (?, ?, ?, 0, NULL)",
                 (target_date, item_type, content))
    conn.commit()
    conn.close()


def get_items_for_date(target_date: str) -> List[Tuple]:
    conn = get_db()
    c = conn.cursor()

    # 1. Non-todo items
    c.execute("SELECT id, type, content, is_done, finish_date FROM items WHERE date = ? AND type != 'todo'", (target_date,))
    items = c.fetchall()

    # 2. Todo items
    c.execute("""
        SELECT id, type, content, is_done, finish_date FROM items 
        WHERE type = 'todo' 
          AND date <= ? 
          AND (is_done = 0 OR finish_date >= ?)
    """, (target_date, target_date))

    items.extend(c.fetchall())
    conn.close()
    return items


def toggle_todo_status(item_id: int, action_date: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT is_done FROM items WHERE id = ?", (item_id,))
    row = c.fetchone()
    if row:
        if row[0] == 0:
            c.execute(
                "UPDATE items SET is_done = 1, finish_date = ? WHERE id = ?", (action_date, item_id))
        else:
            c.execute(
                "UPDATE items SET is_done = 0, finish_date = NULL WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def get_marked_days(year: int, month: int) -> Set[int]:
    """
    Returns a set of day numbers (1-31) in the specified month that contain items.
    """
    conn = get_db()
    c = conn.cursor()
    marked_days = set()

    # 1. Files/Notes in this specific month
    # SQLite LIKE '2023-12-%'
    search_pattern = f"{year}-{month:02d}-%"
    c.execute(
        "SELECT date FROM items WHERE type != 'todo' AND date LIKE ?", (search_pattern,))
    for row in c.fetchall():
        try:
            d = date.fromisoformat(row[0])
            marked_days.add(d.day)
        except ValueError:
            pass

    # 2. Todos active in this month
    # Calculate month bounds
    _, last_day = calendar.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)

    c.execute("SELECT date, finish_date, is_done FROM items WHERE type = 'todo'")
    todos = c.fetchall()

    for create_str, finish_str, is_done in todos:
        try:
            create_date = date.fromisoformat(create_str)

            # Optimization: If created after this month, skip
            if create_date > month_end:
                continue

            # Determine effective finish date (if any)
            finish_date = None
            if is_done and finish_str:
                finish_date = date.fromisoformat(finish_str)

            # Optimization: If finished before this month started, skip
            if finish_date and finish_date < month_start:
                continue

            # Calculate overlap
            start_marker = max(create_date, month_start)

            if finish_date:
                end_marker = min(finish_date, month_end)
            else:
                end_marker = month_end

            # Mark the days
            if start_marker <= end_marker:
                curr = start_marker
                while curr <= end_marker:
                    marked_days.add(curr.day)
                    curr += timedelta(days=1)

        except ValueError:
            continue

    conn.close()
    return marked_days
