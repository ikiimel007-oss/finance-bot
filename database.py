import sqlite3
from datetime import datetime
from config import DATABASE_FILE


def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            UNIQUE(user_id, name)
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            category_id INTEGER NOT NULL,
            note TEXT DEFAULT '',
            date TEXT NOT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        );
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            amount REAL NOT NULL,
            UNIQUE(user_id, category_id, month),
            FOREIGN KEY(category_id) REFERENCES categories(id)
        );
    """)
    conn.commit()
    conn.close()


def default_categories_exist(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM categories WHERE user_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def seed_default_categories(user_id):
    defaults = [
        ("Gaji", "income"),
        ("Freelance", "income"),
        ("Investasi", "income"),
        ("Lainnya (Pemasukan)", "income"),
        ("Makanan", "expense"),
        ("Transport", "expense"),
        ("Belanja", "expense"),
        ("Hiburan", "expense"),
        ("Tagihan", "expense"),
        ("Kesehatan", "expense"),
        ("Pendidikan", "expense"),
        ("Lainnya (Pengeluaran)", "expense"),
    ]
    conn = get_db()
    cur = conn.cursor()
    for name, typ in defaults:
        cur.execute(
            "INSERT OR IGNORE INTO categories (user_id, name, type) VALUES (?, ?, ?)",
            (user_id, name, typ),
        )
    conn.commit()
    conn.close()


def get_categories(user_id, typ=None):
    conn = get_db()
    cur = conn.cursor()
    if typ:
        cur.execute(
            "SELECT * FROM categories WHERE user_id = ? AND type = ? ORDER BY name",
            (user_id, typ),
        )
    else:
        cur.execute(
            "SELECT * FROM categories WHERE user_id = ? ORDER BY type, name", (user_id,)
        )
    rows = cur.fetchall()
    conn.close()
    return rows


def add_category(user_id, name, typ):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)",
            (user_id, name, typ),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def delete_category(user_id, category_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM categories WHERE id = ? AND user_id = ?",
        (category_id, user_id),
    )
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def add_transaction(user_id, amount, typ, category_id, note="", date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (user_id, amount, type, category_id, note, date) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, amount, typ, category_id, note, date_str),
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def get_monthly_report(user_id, year, month):
    month_str = f"{year:04d}-{month:02d}"
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT t.type, t.amount, c.name as category, t.note, t.date
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ? AND t.date LIKE ?
        ORDER BY t.date DESC, t.id DESC
        """,
        (user_id, f"{month_str}%"),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_monthly_summary(user_id, year, month):
    month_str = f"{year:04d}-{month:02d}"
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT type, SUM(amount) as total
        FROM transactions
        WHERE user_id = ? AND date LIKE ?
        GROUP BY type
        """,
        (user_id, f"{month_str}%"),
    )
    rows = cur.fetchall()
    conn.close()
    summary = {"income": 0.0, "expense": 0.0}
    for row in rows:
        summary[row["type"]] = row["total"]
    return summary


def get_category_spending(user_id, year, month):
    month_str = f"{year:04d}-{month:02d}"
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.id, c.name, SUM(t.amount) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ? AND t.date LIKE ? AND t.type = 'expense'
        GROUP BY c.id
        ORDER BY total DESC
        """,
        (user_id, f"{month_str}%"),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def set_budget(user_id, category_id, month, amount):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR REPLACE INTO budgets (user_id, category_id, month, amount) VALUES (?, ?, ?, ?)",
            (user_id, category_id, month, amount),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_budgets(user_id, month):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.id, b.category_id, c.name as category, b.amount
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        WHERE b.user_id = ? AND b.month = ?
        ORDER BY c.name
        """,
        (user_id, month),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_budget(user_id, budget_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM budgets WHERE id = ? AND user_id = ?",
        (budget_id, user_id),
    )
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted
