import sqlite3
import os
import calendar
from datetime import date, timedelta, datetime
from typing import List, Tuple, Set
import platform

if platform.system() == "Windows":
    base_dir = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    DB_PATH = os.path.join(base_dir, "timemap", "timemap.db")
else:
    DB_PATH = os.path.expanduser("~/.local/share/timemap.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id INTEGER PRIMARY KEY, date TEXT, type TEXT, content TEXT,
                  is_done INTEGER DEFAULT 0, finish_date TEXT, alias TEXT, mood TEXT, deleted_at TEXT)''')

    # MIGRATIONS
    c.execute("PRAGMA table_info(items)")
    columns = [info[1] for info in c.fetchall()]
    if 'is_done' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN is_done INTEGER DEFAULT 0")
    if 'finish_date' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN finish_date TEXT")
    if 'alias' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN alias TEXT")
    if 'mood' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN mood TEXT")
    if 'deleted_at' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN deleted_at TEXT")

    c.execute('''CREATE TABLE IF NOT EXISTS tags
                 (id INTEGER PRIMARY KEY, name TEXT UNIQUE, color TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS item_tags
                 (item_id INTEGER, tag_id INTEGER, 
                  FOREIGN KEY(item_id) REFERENCES items(id),
                  FOREIGN KEY(tag_id) REFERENCES tags(id),
                  PRIMARY KEY(item_id, tag_id))''')

    conn.commit()
    return conn


def _cleanup_orphaned_tags(conn):
    """Helper to delete tags that have 0 references in the item_tags table."""
    conn.execute(
        "DELETE FROM tags WHERE id NOT IN (SELECT DISTINCT tag_id FROM item_tags)")


def add_item(item_type: str, content: str, target_date: str = None, alias: str = None, mood: str = None):
    if target_date is None:
        target_date = date.today().isoformat()
    conn = get_db()
    conn.execute("INSERT INTO items (date, type, content, is_done, finish_date, alias, mood) VALUES (?, ?, ?, 0, NULL, ?, ?)",
                 (target_date, item_type, content, alias, mood))
    conn.commit()
    conn.close()


def get_items_for_date(target_date: str) -> List[Tuple]:
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id, type, content, is_done, finish_date, alias, mood FROM items WHERE date = ? AND type != 'todo' AND deleted_at IS NULL", (target_date,))
    items = c.fetchall()

    c.execute("""
        SELECT id, type, content, is_done, finish_date, alias, mood FROM items
        WHERE type = 'todo'
          AND date <= ?
          AND (is_done = 0 OR finish_date >= ?)
          AND deleted_at IS NULL
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


def soft_delete_item(item_id: int):
    """
    Keeps only the 3 most recent delted items.
    Permanently deletes anything older. 
    """
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()

    c.execute("UPDATE items SET deleted_at = ? WHERE id = ?", (now, item_id))
    c.execute(
        "SELECT id FROM items WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC")
    deleted_rows = c.fetchall()
    if len(deleted_rows) > 3:
        to_remove = deleted_rows[3:]
        for row in to_remove:
            c.execute("DELETE FROM item_tags WHERE item_id = ?", (row[0],))
            c.execute("DELETE FROM items WHERE id = ?", (row[0],))
        _cleanup_orphaned_tags(conn)
    conn.commit()
    conn.close()


def recover_last_deleted():
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM items WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC LIMIT 1")
    row = c.fetchone()
    if row:
        c.execute("UPDATE items SET deleted_at = NULL WHERE id = ?", (row[0],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


def empty_trash():
    conn = get_db()
    conn.execute(
        "DELETE FROM item_tags WHERE item_id IN (SELECT id FROM items WHERE deleted_at IS NOT NULL)")
    conn.execute("DELETE FROM items WHERE deleted_at IS NOT NULL")
    _cleanup_orphaned_tags(conn)
    conn.commit()
    conn.close()


def delete_item(item_id: int):
    conn = get_db()
    conn.execute("DELETE FROM item_tags WHERE item_id = ?", (item_id,))
    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    _cleanup_orphaned_tags(conn)
    conn.commit()
    conn.close()


def update_item_content(item_id: int, new_content: str):
    conn = get_db()
    conn.execute("UPDATE items SET content = ? WHERE id = ?",
                 (new_content, item_id))
    conn.commit()
    conn.close()


def update_item_alias(item_id: int, new_alias: str):
    conn = get_db()
    conn.execute("UPDATE items SET alias = ? WHERE id = ?",
                 (new_alias, item_id))
    conn.commit()
    conn.close()


def update_diary_item(item_id: int, title: str, mood: str, content: str):
    conn = get_db()
    conn.execute("UPDATE items SET alias = ?, mood = ?, content = ? WHERE id = ?",
                 (title, mood, content, item_id))
    conn.commit()
    conn.close()


def get_marked_days(year: int, month: int) -> Set[int]:
    conn = get_db()
    c = conn.cursor()
    marked_days = set()

    search_pattern = f"{year}-{month:02d}-%"
    c.execute(
        "SELECT date FROM items WHERE type != 'todo' AND date LIKE ?", (search_pattern,))
    for row in c.fetchall():
        try:
            marked_days.add(date.fromisoformat(row[0]).day)
        except ValueError:
            pass

    _, last_day = calendar.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)

    c.execute("SELECT date, finish_date, is_done FROM items WHERE type = 'todo'")
    todos = c.fetchall()

    for create_str, finish_str, is_done in todos:
        try:
            create_date = date.fromisoformat(create_str)
            if create_date > month_end:
                continue
            finish_date = date.fromisoformat(finish_str) if (
                is_done and finish_str) else None
            if finish_date and finish_date < month_start:
                continue

            start = max(create_date, month_start)
            end = min(finish_date, month_end) if finish_date else month_end

            if start <= end:
                curr = start
                while curr <= end:
                    marked_days.add(curr.day)
                    curr += timedelta(days=1)
        except ValueError:
            continue
    conn.close()
    return marked_days


def get_all_entries():
    """
    Fetches all items for export.
    Returns list of tuples: (type, date, alias, content, mood)
    """
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT type, date, alias, content, mood FROM items ORDER BY date")
    rows = c.fetchall()
    conn.close()
    return rows


def get_month_stats(year: int, month: int) -> dict:
    """
    Returns a dict where key is day (int) and value is a dict of counts.
    """
    conn = get_db()
    c = conn.cursor()
    stats = {}

    _, last_day = calendar.monthrange(year, month)
    for d in range(1, last_day + 1):
        stats[d] = {'diary': 0, 'file': 0, 'todo': 0, 'note': 0}

    search_pattern = f"{year}-{month:02d}-%"
    c.execute("""
        SELECT date, type, count(*)
        FROM items
        WHERE type IN ('diary', 'file', 'note')
            AND date LIKE ?
            AND deleted_at IS NULL
        GROUP BY date, type
    """, (search_pattern,))

    for date_str, type_, count in c.fetchall():
        try:
            d_obj = date.fromisoformat(date_str)
            if d_obj.day in stats:
                stats[d_obj.day][type_] = count
        except ValueError:
            pass

    c.execute(
        "SELECT date, mood FROM items WHERE type='diary' AND date LIKE ? AND deleted_at IS NULL", (search_pattern,))
    for date_str, mood in c.fetchall():
        try:
            d_obj = date.fromisoformat(date_str)
            if d_obj.day in stats and mood:
                stats[d_obj.day]['diary_mood'] = mood
        except ValueError:
            pass
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)

    c.execute("SELECT date, finish_date, is_done FROM items WHERE type = 'todo' AND date <= ? AND deleted_at IS NULL",
              (month_end.isoformat(),))

    for create_str, finish_str, is_done in c.fetchall():
        try:
            create_date = date.fromisoformat(create_str)
            finish_date = date.fromisoformat(finish_str) if (
                is_done and finish_str) else None

            start = max(create_date, month_start)
            end = min(finish_date, month_end) if finish_date else month_end

            if start <= end:
                curr = start
                while curr <= end:
                    stats[curr.day]['todo'] += 1
                    curr += timedelta(days=1)
        except ValueError:
            continue

    conn.close()
    return stats


def get_year_stats(year: int) -> dict:
    """
    Returns aggregated stats for the given year.
    Structure: {
        'diary': [count_jan, count_feb, ...],
        'note': [...],
        'file': [...],
        'todo_created': [...],
        'todo_done': [...],
        'total_todos': int,
        'finished_todos': int
    }
    """
    conn = get_db()
    c = conn.cursor()

    stats = {
        'diary': [0] * 12,
        'note': [0] * 12,
        'file': [0] * 12,
        'todo_created': [0] * 12,
        'todo_done': [0] * 12,
        'total_todos': 0,
        'finished_todos': 0
    }

    search_pattern = f"{year}-%"

    c.execute("""
        SELECT type, date, is_done 
        FROM items 
        WHERE date LIKE ? AND deleted_at IS NULL
    """, (search_pattern,))

    for type_, date_str, is_done in c.fetchall():
        try:
            d = date.fromisoformat(date_str)
            month_idx = d.month - 1  # 0-11

            if type_ == 'diary':
                stats['diary'][month_idx] += 1
            elif type_ == 'note':
                stats['note'][month_idx] += 1
            elif type_ == 'file':
                stats['file'][month_idx] += 1
            elif type_ == 'todo':
                stats['todo_created'][month_idx] += 1
                stats['total_todos'] += 1
        except ValueError:
            pass

    c.execute("""
        SELECT finish_date FROM items 
        WHERE type = 'todo' 
          AND is_done = 1 
          AND finish_date LIKE ? 
          AND deleted_at IS NULL
    """, (search_pattern,))

    for (finish_date_str,) in c.fetchall():
        try:
            d = date.fromisoformat(finish_date_str)
            month_idx = d.month - 1
            stats['todo_done'][month_idx] += 1
            stats['finished_todos'] += 1
        except ValueError:
            pass

    conn.close()
    return stats


def update_item_tags(item_id: int, tags_list: List[str]):
    """
    Rewrites tags for an item. 
    1. Removes ALL existing tags for this item.
    2. Adds the new tags provided (if any).
    """
    conn = get_db()
    c = conn.cursor()

    c.execute("DELETE FROM item_tags WHERE item_id = ?", (item_id,))

    colors = ["red", "green", "blue", "magenta", "yellow", "cyan",
              "#ff5555", "#50fa7b", "#f1fa8c", "#bd93f9", "#ff79c6", "#8be9fd"]

    for tag_name in tags_list:
        clean_tag = tag_name.strip()
        if not clean_tag:
            continue

        c.execute("SELECT id FROM tags WHERE name = ?", (clean_tag,))
        row = c.fetchone()

        if row:
            tag_id = row[0]
        else:
            import random
            color = random.choice(colors)
            c.execute("INSERT INTO tags (name, color) VALUES (?, ?)",
                      (clean_tag, color))
            tag_id = c.lastrowid

        c.execute(
            "INSERT INTO item_tags (item_id, tag_id) VALUES (?, ?)", (item_id, tag_id))
    _cleanup_orphaned_tags(conn)

    conn.commit()
    conn.close()


def get_tags_for_item(item_id: int) -> List[Tuple]:
    """Returns list of (name, color) for an item."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT t.name, t.color 
        FROM tags t 
        JOIN item_tags it ON t.id = it.tag_id 
        WHERE it.item_id = ?
    """, (item_id,))
    tags = c.fetchall()
    conn.close()
    return tags


def get_all_tags() -> List[Tuple]:
    """Returns list of (id, name, count)"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT t.id, t.name, COUNT(it.item_id) as count
        FROM tags t
        JOIN item_tags it ON t.id = it.tag_id
        JOIN items i ON it.item_id = i.id
        WHERE i.deleted_at IS NULL
        GROUP BY t.id, t.name
        ORDER BY count DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows


def get_items_by_tag(tag_id: int) -> List[Tuple]:
    """Returns items for a specific tag."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT i.id, i.type, i.content, i.is_done, i.finish_date, i.alias, i.mood, i.date
        FROM items i
        JOIN item_tags it ON i.id = it.item_id
        WHERE it.tag_id = ? AND i.deleted_at IS NULL
        ORDER BY i.date
    """, (tag_id,))
    rows = c.fetchall()
    conn.close()
    return rows
