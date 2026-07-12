import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_FILE = "finance.db"

USE_PG = DATABASE_URL is not None


def get_db():
    if USE_PG:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    import sqlite3
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _exec(conn, sql, params=None):
    cur = conn.cursor()
    if USE_PG:
        sql = sql.replace("?", "%s")
        sql = sql.replace("INSERT OR IGNORE", "INSERT")
        sql = sql.replace("INSERT OR REPLACE", "INSERT")
        sql = sql.replace("AUTOINCREMENT", "GENERATED ALWAYS AS IDENTITY")
    cur.execute(sql, params or ())
    return cur


def _commit(conn):
    conn.commit()


def _close(conn):
    conn.close()


def init_db():
    conn = get_db()
    cur = conn.cursor()
    if USE_PG:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                UNIQUE(user_id, name)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                category_id INTEGER NOT NULL REFERENCES categories(id),
                note TEXT DEFAULT '',
                date TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                month TEXT NOT NULL,
                amount REAL NOT NULL,
                UNIQUE(user_id, category_id, month)
            )
        """)
    else:
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
    _commit(conn)
    _close(conn)


def default_categories_exist(user_id):
    conn = get_db()
    cur = _exec(conn, "SELECT COUNT(*) AS cnt FROM categories WHERE user_id = ?", (user_id,))
    count = cur.fetchone()
    if USE_PG:
        count = count[0]
    else:
        count = count[0]
    _close(conn)
    return count > 0


def seed_default_categories(user_id):
    conn = get_db()
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
    for name, typ in defaults:
        try:
            cur = _exec(conn, "INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)", (user_id, name, typ))
            _commit(conn)
        except Exception:
            if not USE_PG:
                pass
    _close(conn)


def get_categories(user_id, typ=None):
    conn = get_db()
    if typ:
        cur = _exec(conn, "SELECT * FROM categories WHERE user_id = ? AND type = ? ORDER BY name", (user_id, typ))
    else:
        cur = _exec(conn, "SELECT * FROM categories WHERE user_id = ? ORDER BY type, name", (user_id,))
    if USE_PG:
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    else:
        rows = cur.fetchall()
    _close(conn)
    return rows


def add_category(user_id, name, typ):
    conn = get_db()
    try:
        cur = _exec(conn, "INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)", (user_id, name, typ))
        _commit(conn)
        if USE_PG:
            return cur.fetchone()[0]
        else:
            return cur.lastrowid
    except Exception:
        return None
    finally:
        _close(conn)


def delete_category(user_id, category_id):
    conn = get_db()
    cur = _exec(conn, "DELETE FROM categories WHERE id = ? AND user_id = ?", (category_id, user_id))
    _commit(conn)
    deleted = cur.rowcount > 0
    _close(conn)
    return deleted


def add_transaction(user_id, amount, typ, category_id, note="", date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    cur = _exec(conn, "INSERT INTO transactions (user_id, amount, type, category_id, note, date) VALUES (?, ?, ?, ?, ?, ?)", (user_id, amount, typ, category_id, note, date_str))
    _commit(conn)
    if USE_PG:
        cur = _exec(conn, "SELECT LASTVAL()")
        tid = cur.fetchone()[0]
    else:
        tid = cur.lastrowid
    _close(conn)
    return tid


def get_monthly_report(user_id, year, month):
    month_str = f"{year:04d}-{month:02d}"
    conn = get_db()
    cur = _exec(conn, """
        SELECT t.type, t.amount, c.name AS category, t.note, t.date
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ? AND t.date LIKE ?
        ORDER BY t.date DESC, t.id DESC
    """, (user_id, f"{month_str}%"))
    if USE_PG:
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    else:
        rows = cur.fetchall()
    _close(conn)
    return rows


def get_monthly_summary(user_id, year, month):
    month_str = f"{year:04d}-{month:02d}"
    conn = get_db()
    cur = _exec(conn, """
        SELECT type, SUM(amount) AS total
        FROM transactions
        WHERE user_id = ? AND date LIKE ?
        GROUP BY type
    """, (user_id, f"{month_str}%"))
    rows = cur.fetchall()
    _close(conn)
    summary = {"income": 0.0, "expense": 0.0}
    for row in rows:
        val = row["total"] if not USE_PG else row[1]
        summary[row["type"] if not USE_PG else row[0]] = float(val)
    return summary


def get_category_spending(user_id, year, month):
    month_str = f"{year:04d}-{month:02d}"
    conn = get_db()
    cur = _exec(conn, """
        SELECT c.id, c.name, SUM(t.amount) AS total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ? AND t.date LIKE ? AND t.type = 'expense'
        GROUP BY c.id
        ORDER BY total DESC
    """, (user_id, f"{month_str}%"))
    if USE_PG:
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    else:
        rows = cur.fetchall()
    _close(conn)
    return rows


def set_budget(user_id, category_id, month, amount):
    conn = get_db()
    try:
        if USE_PG:
            cur = _exec(conn, """
                INSERT INTO budgets (user_id, category_id, month, amount)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (user_id, category_id, month)
                DO UPDATE SET amount = EXCLUDED.amount
            """, (user_id, category_id, month, amount))
        else:
            cur = _exec(conn, "INSERT OR REPLACE INTO budgets (user_id, category_id, month, amount) VALUES (?, ?, ?, ?)", (user_id, category_id, month, amount))
        _commit(conn)
        return True
    except Exception:
        return False
    finally:
        _close(conn)


def get_budgets(user_id, month):
    conn = get_db()
    cur = _exec(conn, """
        SELECT b.id, b.category_id, c.name AS category, b.amount
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        WHERE b.user_id = ? AND b.month = ?
        ORDER BY c.name
    """, (user_id, month))
    if USE_PG:
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    else:
        rows = cur.fetchall()
    _close(conn)
    return rows


def delete_budget(user_id, budget_id):
    conn = get_db()
    cur = _exec(conn, "DELETE FROM budgets WHERE id = ? AND user_id = ?", (budget_id, user_id))
    _commit(conn)
    deleted = cur.rowcount > 0
    _close(conn)
    return deleted
