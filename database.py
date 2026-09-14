import os
import sqlite3
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "virangar.db")


def now():
    return datetime.utcnow().replace(microsecond=0).isoformat()


def connect():
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db():
    db = connect()
    cur = db.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        is_blocked INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        role TEXT DEFAULT 'admin',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT NOT NULL,
        title TEXT,
        username TEXT,
        invite_link TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS panels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        base_url TEXT NOT NULL,
        api_key TEXT DEFAULT '',
        username TEXT DEFAULT '',
        password TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS vpn_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        panel_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        price INTEGER NOT NULL DEFAULT 0,
        volume TEXT NOT NULL,
        duration TEXT NOT NULL,
        max_users INTEGER DEFAULT 1,
        description TEXT DEFAULT '',
        active INTEGER DEFAULT 1,
        renewable INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY(panel_id)
            REFERENCES panels(id)
            ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS wallets (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        type TEXT NOT NULL,
        status TEXT NOT NULL,
        description TEXT,
        receipt_file_id TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS purchase_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER,
        user_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        config_name TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        service_id INTEGER,
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        panel_id INTEGER,
        plan_id INTEGER,
        panel_name TEXT,
        price INTEGER,
        duration TEXT,
        volume TEXT,
        config_name TEXT,
        status TEXT,
        config TEXT,
        pg_username TEXT,
        pg_id TEXT,
        created_at TEXT,
        expires_at TEXT,
        payment_method TEXT,
        order_status TEXT
    );

    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT,
        status TEXT DEFAULT 'open',
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS ticket_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        message TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS free_trial_settings (
        id INTEGER PRIMARY KEY CHECK(id = 1),
        is_active INTEGER DEFAULT 1,
        volume_mb INTEGER DEFAULT 200,
        duration_hours INTEGER DEFAULT 24,
        panel_id INTEGER,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS free_trials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        service_id INTEGER,
        panel_id INTEGER,
        volume_mb INTEGER,
        duration_hours INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        expires_at TEXT
    );

    CREATE TABLE IF NOT EXISTS api_panels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        base_url TEXT NOT NULL,
        api_key TEXT DEFAULT '',
        api_type TEXT DEFAULT '',
        username TEXT DEFAULT '',
        password TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS bot_licenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_key TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        plan TEXT DEFAULT 'standard',
        status TEXT DEFAULT 'active',
        starts_at TEXT,
        expires_at TEXT,
        created_at TEXT
    );
    """)

    cur.execute("""
        INSERT OR IGNORE INTO free_trial_settings
        (id, is_active, volume_mb, duration_hours, panel_id, updated_at)
        VALUES (1, 1, 200, 24, NULL, ?)
    """, (now(),))

    db.commit()
    db.close()


def one(sql, params=()):
    db = connect()
    try:
        return db.execute(sql, params).fetchone()
    finally:
        db.close()


def all_rows(sql, params=()):
    db = connect()
    try:
        return db.execute(sql, params).fetchall()
    finally:
        db.close()


def run(sql, params=(), commit=True):
    db = connect()
    try:
        cur = db.execute(sql, params)

        if commit:
            db.commit()

        return cur.lastrowid
    finally:
        db.close()


def add_user(user):
    db = connect()

    try:
        db.execute("""
            INSERT OR IGNORE INTO users
            (id, username, first_name, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            user.id,
            user.username or "",
            user.first_name or "",
            now(),
        ))

        db.execute("""
            UPDATE users
            SET username = ?, first_name = ?
            WHERE id = ?
        """, (
            user.username or "",
            user.first_name or "",
            user.id,
        ))

        db.commit()

    finally:
        db.close()


def get_user(user_id):
    row = one(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    )

    return dict(row) if row else None


def get_all_users():
    rows = all_rows("""
        SELECT *
        FROM users
        ORDER BY id DESC
    """)

    return [dict(x) for x in rows]


def is_admin_db(user_id):
    return bool(
        one(
            "SELECT 1 FROM admins WHERE user_id = ?",
            (user_id,)
        )
    )


def add_admin(user_id, role="admin"):
    return run("""
        INSERT OR REPLACE INTO admins
        (user_id, role, created_at)
        VALUES (?, ?, ?)
    """, (
        user_id,
        role,
        now(),
    ))


def get_admins():
    rows = all_rows("""
        SELECT
            a.user_id,
            a.role,
            a.created_at,
            u.username,
            u.first_name
        FROM admins a
        LEFT JOIN users u
            ON u.id = a.user_id
        ORDER BY a.user_id
    """)

    return [dict(x) for x in rows]


def get_channels(active_only=False):
    sql = "SELECT * FROM channels"

    if active_only:
        sql += " WHERE is_active = 1"

    sql += " ORDER BY id ASC"

    rows = all_rows(sql)

    return [dict(x) for x in rows]


def get_panels(active_only=False):
    sql = "SELECT * FROM panels"

    if active_only:
        sql += " WHERE is_active = 1"

    sql += " ORDER BY id ASC"

    rows = all_rows(sql)

    return [dict(x) for x in rows]


def get_panel(panel_id):
    row = one(
        "SELECT * FROM panels WHERE id = ?",
        (panel_id,)
    )

    return dict(row) if row else None


def get_balance(user_id):
    row = one("""
        SELECT balance
        FROM wallets
        WHERE user_id = ?
    """, (user_id,))

    return int(row["balance"]) if row else 0


def add_balance(user_id, amount):
    db = connect()

    try:
        db.execute("""
            INSERT OR IGNORE INTO wallets
            (user_id, balance)
            VALUES (?, 0)
        """, (user_id,))

        db.execute("""
            UPDATE wallets
            SET balance = balance + ?
            WHERE user_id = ?
        """, (
            amount,
            user_id,
        ))

        db.commit()

    finally:
        db.close()


def add_transaction(
    user_id,
    amount,
    tx_type,
    status,
    description="",
    receipt_file_id=None
):
    return run("""
        INSERT INTO transactions
        (user_id, amount, type, status, description,
         receipt_file_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        amount,
        tx_type,
        status,
        description,
        receipt_file_id,
        now(),
    ))


def get_transactions(user_id):
    rows = all_rows("""
        SELECT *
        FROM transactions
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    return [dict(x) for x in rows]


def get_user_services(user_id):
    rows = all_rows("""
        SELECT *
        FROM services
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    return [dict(x) for x in rows]


def create_ticket(user_id, subject):
    ticket_id = run("""
        INSERT INTO tickets
        (user_id, subject, status, created_at, updated_at)
        VALUES (?, ?, 'open', ?, ?)
    """, (
        user_id,
        subject,
        now(),
        now(),
    ))

    return ticket_id


def get_user_tickets(user_id):
    rows = all_rows("""
        SELECT *
        FROM tickets
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    return [dict(x) for x in rows]


def add_ticket_message(ticket_id, sender_id, message):
    return run("""
        INSERT INTO ticket_messages
        (ticket_id, sender_id, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        ticket_id,
        sender_id,
        message,
        now(),
    ))


def get_ticket_messages(ticket_id):
    rows = all_rows("""
        SELECT *
        FROM ticket_messages
        WHERE ticket_id = ?
        ORDER BY id ASC
    """, (ticket_id,))

    return [dict(x) for x in rows]


def get_payment_settings():
    keys = (
        "card_number",
        "card_holder",
        "support_username",
    )

    result = {}

    for key in keys:
        row = one(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        )

        result[key] = row["value"] if row else ""

    return result


def set_setting(key, value):
    run("""
        INSERT OR REPLACE INTO settings
        (key, value)
        VALUES (?, ?)
    """, (
        key,
        value,
    ))


def get_stats():
    total = one(
        "SELECT COUNT(*) AS n FROM users"
    )["n"]

    active = one("""
        SELECT COUNT(*) AS n
        FROM services
        WHERE status = 'active'
    """)["n"]

    today = datetime.utcnow().date().isoformat()

    today_count = one("""
        SELECT COUNT(*) AS n
        FROM users
        WHERE substr(created_at, 1, 10) = ?
    """, (today,))["n"]

    return {
        "total": total,
        "active": active,
        "today": today_count,
    }
