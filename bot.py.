# ============================================================
# VirangarVPN - Single File Bot
# Telegram VPN Sales & Management
# ============================================================

import os
import sqlite3
import logging
import threading
import time
import shutil
from datetime import datetime, timedelta
from functools import wraps

import requests
import telebot
from telebot import types
from dotenv import load_dotenv


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0") or 0)

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///virangarvpn.db")
if DB_PATH.startswith("sqlite:///"):
    DB_PATH = DB_PATH.replace("sqlite:///", "", 1)

BOT_NAME = os.getenv("BOT_NAME", "VirangarVPN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is empty")

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    threaded=True,
)


# ============================================================
# DATABASE
# ============================================================

DB_LOCK = threading.Lock()


def connect():
    db = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False
    )
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def db_execute(sql, params=(), fetchone=False, fetchall=False, commit=True):
    with DB_LOCK:
        db = connect()
        cur = db.cursor()
        cur.execute(sql, params)

        result = None

        if fetchone:
            result = cur.fetchone()

        if fetchall:
            result = cur.fetchall()

        if commit:
            db.commit()

        db.close()
        return result


def init_db():
    db = connect()
    cur = db.cursor()

    # ---------------- USERS ----------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT,
        balance INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0,
        is_reseller INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    # ---------------- ADMINS ----------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        role TEXT DEFAULT 'admin',
        is_active INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)

    # ---------------- PANELS ----------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS panels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        username TEXT,
        password TEXT,
        api_token TEXT,
        active INTEGER DEFAULT 1,
        status TEXT DEFAULT 'unknown',
        capacity INTEGER DEFAULT 0,
        assigned_sales INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    # ---------------- PLANS ----------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        volume INTEGER NOT NULL,
        duration INTEGER NOT NULL,
        devices INTEGER DEFAULT 1,
        reseller_price INTEGER DEFAULT 0,
        location TEXT,
        panel_id INTEGER,
        active INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY(panel_id) REFERENCES panels(id) ON DELETE SET NULL
    )
    """)

    # ---------------- SERVICES ----------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_id INTEGER,
        panel_id INTEGER,
        username TEXT,
        config TEXT,
        qr TEXT,
        volume INTEGER DEFAULT 0,
        used_volume INTEGER DEFAULT 0,
        duration INTEGER DEFAULT 0,
        devices INTEGER DEFAULT 1,
        expires_at TEXT,
        status TEXT DEFAULT 'active',
        reseller_id INTEGER,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(plan_id) REFERENCES plans(id),
        FOREIGN KEY(panel_id) REFERENCES panels(id)
    )
    """)

    # ---------------- PAYMENTS ----------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_id INTEGER,
        amount INTEGER NOT NULL,
        method TEXT,
        receipt_file_id TEXT,
        receipt_type TEXT,
        status TEXT DEFAULT 'pending',
        service_id INTEGER,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    # ---------------- TRANSACTIONS ----------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        type TEXT,
        description TEXT,
        reference TEXT,
        created_at TEXT
    )
    """)

    # ---------------- RESELLER PLANS ----------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reseller_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        capacity INTEGER DEFAULT 0,
        duration INTEGER DEFAULT 30,
        active INTEGER DEFAULT 1,
        panel_id INTEGER,
        created_at TEXT
    )
    """)

    # ---------------- RESELLER PANELS ----------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reseller_panels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        reseller_plan_id INTEGER,
        name TEXT,
        balance INTEGER DEFAULT 0,
        expires_at TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)

    # ---------------- TICKETS ----------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT,
        status TEXT DEFAULT 'open',
        created_at TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ticket_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        message TEXT,
        created_at TEXT
    )
    """)

    # ---------------- LICENSES ----------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_name TEXT,
        price INTEGER DEFAULT 0,
        license_key TEXT UNIQUE,
        expires_at TEXT,
        status TEXT DEFAULT 'active',
        created_at TEXT
    )
    """)

    # ---------------- SETTINGS ----------------

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    db.commit()

    # SUPER ADMIN
    if SUPER_ADMIN_ID:
        cur.execute("""
        INSERT OR IGNORE INTO admins
        (telegram_id, role, is_active, created_at)
        VALUES (?, 'superadmin', 1, ?)
        """, (SUPER_ADMIN_ID, now()))

    # DEFAULT SETTINGS
    defaults = {
        "force_join_enabled": "0",
        "force_join_channel": "",
        "force_join_url": "",

        "payment_mode": "manual",
        "manual_payment_enabled": "1",
        "card_number": "",
        "card_holder": "",

        "online_payment_enabled": "0",
        "gateway_provider": "",
        "gateway_api_key": "",
        "gateway_merchant_id": "",

        "trial_enabled": "1",
        "trial_volume": "5",
        "trial_duration": "1",
        "trial_devices": "1",
        "trial_limit": "1",

        "support_username": "",

        "backup_enabled": "1",
        "backup_interval_hours": "24",
        "backup_retention_days": "30",
    }

    for key, value in defaults.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
            (key, value)
        )

    # DEFAULT PLANS
    count = cur.execute("SELECT COUNT(*) FROM plans").fetchone()[0]

    if count == 0:
        default_plans = [
            ("1 ماهه 20GB", 100000, 20, 30, 1, 0),
            ("1 ماهه 50GB", 180000, 50, 30, 2, 0),
            ("2 ماهه 100GB", 320000, 100, 60, 3, 0),
        ]

        for name, price, volume, duration, devices, reseller_price in default_plans:
            cur.execute("""
            INSERT INTO plans
            (name, price, volume, duration, devices,
             reseller_price, active, sort_order, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?)
            """, (
                name,
                price,
                volume,
                duration,
                devices,
                reseller_price,
                now()
            ))

    db.commit()
    db.close()


# ============================================================
# SETTINGS
# ============================================================

def get_setting(key, default=""):
    row = db_execute(
        "SELECT value FROM settings WHERE key=?",
        (key,),
        fetchone=True
    )
    return row["value"] if row else default


def set_setting(key, value):
    db_execute("""
    INSERT INTO settings(key, value)
    VALUES (?, ?)
    ON CONFLICT(key)
    DO UPDATE SET value=excluded.value
    """, (key, str(value)))


# ============================================================
# USERS
# ============================================================

def ensure_user(tg_user):
    existing = db_execute(
        "SELECT * FROM users WHERE telegram_id=?",
        (tg_user.id,),
        fetchone=True
    )

    if existing:
        db_execute("""
        UPDATE users
        SET username=?, first_name=?, updated_at=?
        WHERE telegram_id=?
        """, (
            tg_user.username or "",
            tg_user.first_name or "",
            now(),
            tg_user.id
        ))
        return existing

    db_execute("""
    INSERT INTO users
    (telegram_id, username, first_name, balance,
     is_blocked, is_reseller, created_at, updated_at)
    VALUES (?, ?, ?, 0, 0, 0, ?, ?)
    """, (
        tg_user.id,
        tg_user.username or "",
        tg_user.first_name or "",
        now(),
        now()
    ))

    return db_execute(
        "SELECT * FROM users WHERE telegram_id=?",
        (tg_user.id,),
        fetchone=True
    )


def get_user(tg_id):
    return db_execute(
        "SELECT * FROM users WHERE telegram_id=?",
        (tg_id,),
        fetchone=True
    )


def internal_user_id(tg_id):
    user = get_user(tg_id)
    return user["id"] if user else None


# ============================================================
# ADMIN
# ============================================================

def is_admin(tg_id):
    row = db_execute("""
    SELECT 1 FROM admins
    WHERE telegram_id=? AND is_active=1
    """, (tg_id,), fetchone=True)

    return bool(row)


def is_superadmin(tg_id):
    row = db_execute("""
    SELECT 1 FROM admins
    WHERE telegram_id=? AND role='superadmin' AND is_active=1
    """, (tg_id,), fetchone=True)

    return bool(row)


def admin_only(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if not is_admin(message.from_user.id):
            bot.send_message(
                message.chat.id,
                "⛔ دسترسی غیرمجاز"
            )
            return
        return func(message, *args, **kwargs)

    return wrapper


# ============================================================
# FORCE JOIN
# ============================================================

def force_join_ok(user_id):
    enabled = get_setting("force_join_enabled", "0") == "1"

    if not enabled:
        return True

    channel = get_setting("force_join_channel", "").strip()

    if not channel:
        return True

    try:
        member = bot.get_chat_member(channel, user_id)

        return member.status in (
            "member",
            "administrator",
            "creator"
        )

    except Exception as e:
        logging.warning("Force join check: %s", e)
        return False


def force_join_markup():
    markup = types.InlineKeyboardMarkup()

    url = get_setting("force_join_url", "").strip()

    if url:
        markup.add(
            types.InlineKeyboardButton(
                "📢 عضویت در کانال",
                url=url
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            "✅ بررسی عضویت",
            callback_data="check_join"
        )
    )

    return markup


# ============================================================
# USER MENU
# ============================================================

def user_keyboard():
    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "🛒 خرید VPN",
        "🛡 سرویس‌های من"
    )

    kb.row(
        "🎁 تست رایگان",
        "💰 کیف پول"
    )

    kb.row(
        "📜 تراکنش‌های من",
        "🤝 پنل نمایندگی"
    )

    kb.row(
        "🎫 خرید لایسنس ربات",
        "🆘 پشتیبانی"
    )

    kb.row(
        "📚 راهنما",
        "⚙️ حساب کاربری"
    )

    return kb


def admin_keyboard():
    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "📊 داشبورد",
        "👥 کاربران"
    )

    kb.row(
        "🖥 پنل‌ها",
        "💎 پلن‌های VPN"
    )

    kb.row(
        "📦 سرویس‌ها",
        "🤝 نمایندگان"
    )

    kb.row(
        "💰 پرداخت‌ها",
        "💳 تنظیمات پرداخت"
    )

    kb.row(
        "🎁 تست رایگان",
        "📢 ارسال همگانی"
    )

    kb.row(
        "📢 عضویت اجباری",
        "🧩 منوی کاربر"
    )

    kb.row(
        "🎫 تیکت‌ها",
        "👑 مدیران"
    )

    kb.row(
        "💾 Backup / Restore",
        "📈 گزارش‌ها"
    )

    kb.row(
        "🛡 امنیت",
        "⚙️ تنظیمات"
    )

    kb.row("🔧 وضعیت سیستم")

    kb.row("🏠 منوی کاربر")

    return kb


# ============================================================
# START
# ============================================================

@bot.message_handler(commands=["start"])
def start(message):
    user = ensure_user(message.from_user)

    if user["is_blocked"]:
        bot.send_message(
            message.chat.id,
            "⛔ حساب شما مسدود شده است."
        )
        return

    if not force_join_ok(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "🔒 برای استفاده از ربات ابتدا عضو کانال شوید.",
            reply_markup=force_join_markup()
        )
        return

    text = (
        f"🔥 <b>{BOT_NAME}</b>\n\n"
        "به ربات خوش آمدید ❤️\n\n"
        "از منوی زیر سرویس موردنظر خود را انتخاب کنید."
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=user_keyboard()
    )


# ============================================================
# FORCE JOIN CALLBACK
# ============================================================

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    if force_join_ok(call.from_user.id):
        bot.answer_callback_query(
            call.id,
            "عضویت تأیید شد ✅"
        )

        bot.send_message(
            call.message.chat.id,
            "🔥 حالا می‌تونی از ربات استفاده کنی.",
            reply_markup=user_keyboard()
        )
    else:
        bot.answer_callback_query(
            call.id,
            "هنوز عضو کانال نیستی ❌",
            show_alert=True
        )


# ============================================================
# BUY VPN
# ============================================================

def plans_keyboard():
    plans = db_execute("""
    SELECT * FROM plans
    WHERE active=1
    ORDER BY sort_order, id
    """, fetchall=True)

    kb = types.InlineKeyboardMarkup()

    for plan in plans:
        kb.add(
            types.InlineKeyboardButton(
                f"💎 {plan['name']} | {plan['price']:,} تومان",
                callback_data=f"plan:{plan['id']}"
            )
        )

    return kb


@bot.message_handler(func=lambda m: m.text == "🛒 خرید VPN")
def buy_vpn(message):
    if not force_join_ok(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "🔒 ابتدا عضو کانال شوید.",
            reply_markup=force_join_markup()
        )
        return

    bot.send_message(
        message.chat.id,
        "💎 <b>انتخاب پلن</b>\n\n"
        "پلن موردنظر خود را انتخاب کنید:",
        reply_markup=plans_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("plan:"))
def select_plan(call):
    plan_id = int(call.data.split(":")[1])

    plan = db_execute(
        "SELECT * FROM plans WHERE id=? AND active=1",
        (plan_id,),
        fetchone=True
    )

    if not plan:
        bot.answer_callback_query(
            call.id,
            "پلن پیدا نشد",
            show_alert=True
        )
        return

    text = (
        "💎 <b>جزئیات پلن</b>\n\n"
        f"📦 نام: {plan['name']}\n"
        f"📊 حجم: {plan['volume']} GB\n"
        f"⏳ مدت: {plan['duration']} روز\n"
        f"📱 دستگاه: {plan['devices']}\n"
        f"💰 قیمت: {plan['price']:,} تومان\n\n"
        "روش پرداخت را انتخاب کنید:"
    )

    kb = types.InlineKeyboardMarkup()

    if get_setting("manual_payment_enabled", "1") == "1":
        kb.add(
            types.InlineKeyboardButton(
                "💳 کارت به کارت",
                callback_data=f"manual:{plan_id}"
            )
        )

    if get_setting("online_payment_enabled", "0") == "1":
        kb.add(
            types.InlineKeyboardButton(
                "🌐 پرداخت آنلاین",
                callback_data=f"online:{plan_id}"
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            "🔙 برگشت",
            callback_data="back_plans"
        )
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


# ============================================================
# MANUAL PAYMENT
# ============================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("manual:"))
def manual_payment(call):
    plan_id = int(call.data.split(":")[1])

    plan = db_execute(
        "SELECT * FROM plans WHERE id=? AND active=1",
        (plan_id,),
        fetchone=True
    )

    if not plan:
        return

    card = get_setting("card_number", "")
    holder = get_setting("card_holder", "")

    if not card:
        bot.answer_callback_query(
            call.id,
            "پرداخت کارت به کارت فعلاً تنظیم نشده.",
            show_alert=True
        )
        return

    text = (
        "💳 <b>پرداخت کارت به کارت</b>\n\n"
        f"💰 مبلغ: <b>{plan['price']:,} تومان</b>\n\n"
        f"💳 شماره کارت:\n<code>{card}</code>\n\n"
        f"👤 به نام: <b>{holder or '---'}</b>\n\n"
        "بعد از انتقال وجه، تصویر رسید را همینجا ارسال کنید."
    )

    bot.send_message(
        call.message.chat.id,
        text
    )

    bot.register_next_step_handler(
        call.message,
        receive_plan_receipt,
        plan_id
    )


def receive_plan_receipt(message, plan_id):
    if not message.photo:
        bot.send_message(
            message.chat.id,
            "❌ لطفاً تصویر رسید را ارسال کن."
        )

        bot.register_next_step_handler(
            message,
            receive_plan_receipt,
            plan_id
        )
        return

    file_id = message.photo[-1].file_id
    user_id = internal_user_id(message.from_user.id)

    plan = db_execute(
        "SELECT * FROM plans WHERE id=?",
        (plan_id,),
        fetchone=True
    )

    if not plan:
        return

    db_execute("""
    INSERT INTO payments
    (user_id, plan_id, amount, method,
     receipt_file_id, receipt_type,
     status, created_at, updated_at)
    VALUES (?, ?, ?, 'manual', ?, 'photo',
            'pending', ?, ?)
    """, (
        user_id,
        plan_id,
        plan["price"],
        file_id,
        now(),
        now()
    ))

    payment = db_execute("""
    SELECT * FROM payments
    WHERE user_id=? AND plan_id=? AND status='pending'
    ORDER BY id DESC LIMIT 1
    """, (user_id, plan_id), fetchone=True)

    notify_admin_payment(payment)

    bot.send_message(
        message.chat.id,
        "✅ رسید شما ثبت شد.\n\n"
        "⏳ پرداخت در انتظار بررسی مدیریت است."
    )


# ============================================================
# ADMIN PAYMENT NOTIFICATION
# ============================================================

def notify_admin_payment(payment):
    if not payment or not SUPER_ADMIN_ID:
        return

    user = db_execute(
        "SELECT * FROM users WHERE id=?",
        (payment["user_id"],),
        fetchone=True
    )

    plan = None

    if payment["plan_id"]:
        plan = db_execute(
            "SELECT * FROM plans WHERE id=?",
            (payment["plan_id"],),
            fetchone=True
        )

    username = (
        f"@{user['username']}"
        if user and user["username"]
        else "بدون یوزرنیم"
    )

    text = (
        "💳 <b>درخواست پرداخت جدید</b>\n\n"
        f"🆔 Payment: <code>{payment['id']}</code>\n"
        f"👤 کاربر: {username}\n"
        f"🆔 Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"💰 مبلغ: {payment['amount']:,} تومان\n"
        f"📦 پلن: {plan['name'] if plan else '---'}\n"
        f"📌 روش: {payment['method']}"
    )

    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton(
            "✅ تأیید",
            callback_data=f"payapprove:{payment['id']}"
        ),
        types.InlineKeyboardButton(
            "❌ رد",
            callback_data=f"payreject:{payment['id']}"
        )
    )

    bot.send_message(
        SUPER_ADMIN_ID,
        text,
        reply_markup=kb
    )

    if payment["receipt_file_id"]:
        try:
            bot.send_photo(
                SUPER_ADMIN_ID,
                payment["receipt_file_id"],
                caption="🧾 رسید پرداخت"
            )
        except Exception:
            pass


# ============================================================
# PAYMENT APPROVE
# ============================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("payapprove:"))
def approve_payment(call):
    if not is_superadmin(call.from_user.id):
        bot.answer_callback_query(
            call.id,
            "دسترسی ندارید",
            show_alert=True
        )
        return

    payment_id = int(call.data.split(":")[1])

    payment = db_execute(
        "SELECT * FROM payments WHERE id=?",
        (payment_id,),
        fetchone=True
    )

    if not payment or payment["status"] != "pending":
        bot.answer_callback_query(
            call.id,
            "این پرداخت قبلاً بررسی شده.",
            show_alert=True
        )
        return

    # Wallet topup
    if payment["method"] == "wallet":
        user = db_execute(
            "SELECT * FROM users WHERE id=?",
            (payment["user_id"],),
            fetchone=True
        )

        db_execute("""
        UPDATE users
        SET balance=balance+?
        WHERE id=?
        """, (
            payment["amount"],
            payment["user_id"]
        ))

        db_execute("""
        INSERT INTO transactions
        (user_id, amount, type, description, reference, created_at)
        VALUES (?, ?, 'credit', ?, ?, ?)
        """, (
            payment["user_id"],
            payment["amount"],
            "شارژ کیف پول",
            f"payment:{payment_id}",
            now()
        ))

        db_execute("""
        UPDATE payments
        SET status='approved', updated_at=?
        WHERE id=?
        """, (now(), payment_id))

        if user:
            bot.send_message(
                user["telegram_id"],
                f"✅ پرداخت تأیید شد.\n\n"
                f"💰 مبلغ <b>{payment['amount']:,}</b> تومان "
                f"به کیف پول شما اضافه شد."
            )

        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )

        bot.answer_callback_query(call.id, "کیف پول شارژ شد ✅")
        return

    # VPN service
    plan = db_execute(
        "SELECT * FROM plans WHERE id=?",
        (payment["plan_id"],),
        fetchone=True
    )

    user = db_execute(
        "SELECT * FROM users WHERE id=?",
        (payment["user_id"],),
        fetchone=True
    )

    if not plan or not user:
        bot.answer_callback_query(
            call.id,
            "اطلاعات پرداخت ناقص است.",
            show_alert=True
        )
        return

    panel = None

    if plan["panel_id"]:
        panel = db_execute(
            "SELECT * FROM panels WHERE id=? AND active=1",
            (plan["panel_id"],),
            fetchone=True
        )

    if not panel:
        panel = db_execute("""
        SELECT * FROM panels
        WHERE active=1
        ORDER BY assigned_sales ASC, id ASC
        LIMIT 1
        """, fetchone=True)

    if not panel:
        bot.answer_callback_query(
            call.id,
            "هیچ پنل فعالی برای ساخت سرویس وجود ندارد.",
            show_alert=True
        )
        return

    # Important:
    # Real PasarGuard service creation requires the actual
    # PasarGuard API endpoint/schema.
    result = pasarguard_create_service(
        panel=panel,
        telegram_user=user,
        plan=plan
    )

    if not result["success"]:
        bot.answer_callback_query(
            call.id,
            "ساخت سرویس انجام نشد.",
            show_alert=True
        )

        bot.send_message(
            SUPER_ADMIN_ID,
            "⚠️ پرداخت تأیید نشد چون ساخت سرویس PasarGuard موفق نبود.\n\n"
            f"Payment: {payment_id}\n"
            f"خطا: {result['error']}"
        )
        return

    service = create_local_service(
        user=user,
        plan=plan,
        panel=panel,
        result=result
    )

    db_execute("""
    UPDATE payments
    SET status='approved',
        service_id=?,
        updated_at=?
    WHERE id=?
    """, (
        service["id"],
        now(),
        payment_id
    ))

    bot.send_message(
        user["telegram_id"],
        "🎉 <b>پرداخت شما تأیید شد!</b>\n\n"
        "🛡 سرویس شما با موفقیت ساخته شد.\n\n"
        f"📦 پلن: {plan['name']}\n"
        f"⏳ مدت: {plan['duration']} روز\n"
        f"📊 حجم: {plan['volume']} GB\n\n"
        f"🔐 کانفیگ:\n"
        f"<code>{service['config']}</code>"
    )

    bot.answer_callback_query(
        call.id,
        "پرداخت و سرویس تأیید شد ✅"
    )


# ============================================================
# PAYMENT REJECT
# ============================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("payreject:"))
def reject_payment(call):
    if not is_superadmin(call.from_user.id):
        return

    payment_id = int(call.data.split(":")[1])

    payment = db_execute(
        "SELECT * FROM payments WHERE id=?",
        (payment_id,),
        fetchone=True
    )

    if not payment or payment["status"] != "pending":
        bot.answer_callback_query(
            call.id,
            "این پرداخت قبلاً بررسی شده.",
            show_alert=True
        )
        return

    db_execute("""
    UPDATE payments
    SET status='rejected', updated_at=?
    WHERE id=?
    """, (now(), payment_id))

    user = db_execute(
        "SELECT * FROM users WHERE id=?",
        (payment["user_id"],),
        fetchone=True
    )

    if user:
        bot.send_message(
            user["telegram_id"],
            "❌ رسید پرداخت شما رد شد.\n\n"
            "در صورت اشتباه، دوباره اقدام کنید."
        )

    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=None
    )

    bot.answer_callback_query(
        call.id,
        "پرداخت رد شد ❌"
    )


# ============================================================
# ONLINE PAYMENT
# ============================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("online:"))
def online_payment(call):
    plan_id = int(call.data.split(":")[1])

    provider = get_setting("gateway_provider", "")

    if not provider:
        bot.answer_callback_query(
            call.id,
            "درگاه پرداخت تنظیم نشده.",
            show_alert=True
        )
        return

    bot.send_message(
        call.message.chat.id,
        "🌐 درگاه آنلاین فعال است، اما اتصال نهایی "
        "به API درگاه انتخابی نیاز به مشخصات همان درگاه دارد."
    )


# ============================================================
# WALLET
# ============================================================

@bot.message_handler(func=lambda m: m.text == "💰 کیف پول")
def wallet(message):
    user = get_user(message.from_user.id)

    balance = user["balance"] if user else 0

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "💳 شارژ کیف پول",
            callback_data="wallet_topup"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📜 تاریخچه تراکنش",
            callback_data="wallet_history"
        )
    )

    bot.send_message(
        message.chat.id,
        f"💰 <b>کیف پول</b>\n\n"
        f"موجودی: <b>{balance:,} تومان</b>",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "wallet_topup")
def wallet_topup(call):
    bot.send_message(
        call.message.chat.id,
        "💳 مبلغ شارژ را به تومان وارد کن:"
    )

    bot.register_next_step_handler(
        call.message,
        wallet_amount
    )


def wallet_amount(message):
    try:
        amount = int(
            message.text.replace(",", "").replace(" ", "")
        )

        if amount <= 0:
            raise ValueError

    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ مبلغ نامعتبر است."
        )
        return

    card = get_setting("card_number", "")
    holder = get_setting("card_holder", "")

    if not card:
        bot.send_message(
            message.chat.id,
            "❌ پرداخت کارت به کارت تنظیم نشده."
        )
        return

    bot.send_message(
        message.chat.id,
        f"💳 مبلغ <b>{amount:,} تومان</b> را به کارت زیر انتقال بده:\n\n"
        f"<code>{card}</code>\n"
        f"👤 {holder}\n\n"
        "سپس تصویر رسید را ارسال کن."
    )

    bot.register_next_step_handler(
        message,
        wallet_receipt,
        amount
    )


def wallet_receipt(message, amount):
    if not message.photo:
        bot.send_message(
            message.chat.id,
            "❌ فقط تصویر رسید را ارسال کن."
        )
        bot.register_next_step_handler(
            message,
            wallet_receipt,
            amount
        )
        return

    user_id = internal_user_id(message.from_user.id)

    file_id = message.photo[-1].file_id

    db_execute("""
    INSERT INTO payments
    (user_id, plan_id, amount, method,
     receipt_file_id, receipt_type,
     status, created_at, updated_at)
    VALUES (?, NULL, ?, 'wallet', ?, 'photo',
            'pending', ?, ?)
    """, (
        user_id,
        amount,
        file_id,
        now(),
        now()
    ))

    payment = db_execute("""
    SELECT * FROM payments
    WHERE user_id=? AND method='wallet'
    ORDER BY id DESC LIMIT 1
    """, (user_id,), fetchone=True)

    notify_admin_payment(payment)

    bot.send_message(
        message.chat.id,
        "✅ رسید شارژ کیف پول ثبت شد.\n\n"
        "⏳ منتظر تأیید مدیریت باشید."
    )


@bot.callback_query_handler(func=lambda call: call.data == "wallet_history")
def wallet_history(call):
    user_id = internal_user_id(call.from_user.id)

    rows = db_execute("""
    SELECT * FROM transactions
    WHERE user_id=?
    ORDER BY id DESC
    LIMIT 20
    """, (user_id,), fetchall=True)

    if not rows:
        bot.send_message(
            call.message.chat.id,
            "📭 هنوز تراکنشی ثبت نشده."
        )
        return

    lines = ["📜 <b>تراکنش‌های کیف پول</b>\n"]

    for row in rows:
        sign = "+" if row["amount"] >= 0 else ""

        lines.append(
            f"• {sign}{row['amount']:,} تومان\n"
            f"  {row['description']}\n"
            f"  {row['created_at']}\n"
        )

    bot.send_message(
        call.message.chat.id,
        "\n".join(lines)
    )


# ============================================================
# MY SERVICES
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🛡 سرویس‌های من")
def my_services(message):
    user_id = internal_user_id(message.from_user.id)

    services = db_execute("""
    SELECT services.*, plans.name AS plan_name
    FROM services
    LEFT JOIN plans ON plans.id=services.plan_id
    WHERE services.user_id=?
    ORDER BY services.id DESC
    """, (user_id,), fetchall=True)

    if not services:
        bot.send_message(
            message.chat.id,
            "📭 شما هنوز سرویسی ندارید."
        )
        return

    kb = types.InlineKeyboardMarkup()

    for service in services:
        status = "🟢" if service["status"] == "active" else "🔴"

        kb.add(
            types.InlineKeyboardButton(
                f"{status} {service['plan_name'] or 'سرویس'}",
                callback_data=f"service:{service['id']}"
            )
        )

    bot.send_message(
        message.chat.id,
        "🛡 <b>سرویس‌های من</b>\n\n"
        "سرویس را انتخاب کن:",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("service:"))
def service_details(call):
    service_id = int(call.data.split(":")[1])

    user_id = internal_user_id(call.from_user.id)

    service = db_execute("""
    SELECT services.*, plans.name AS plan_name
    FROM services
    LEFT JOIN plans ON plans.id=services.plan_id
    WHERE services.id=? AND services.user_id=?
    """, (
        service_id,
        user_id
    ), fetchone=True)

    if not service:
        bot.answer_callback_query(
            call.id,
            "سرویس پیدا نشد.",
            show_alert=True
        )
        return

    remaining = max(
        0,
        service["volume"] - service["used_volume"]
    )

    text = (
        "🛡 <b>جزئیات سرویس</b>\n\n"
        f"📦 پلن: {service['plan_name'] or '---'}\n"
        f"📊 حجم کل: {service['volume']} GB\n"
        f"📈 باقی‌مانده: {remaining} GB\n"
        f"📱 دستگاه: {service['devices']}\n"
        f"⏳ انقضا: {service['expires_at'] or '---'}\n"
        f"📌 وضعیت: {service['status']}\n"
    )

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🔐 کانفیگ",
            callback_data=f"config:{service_id}"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🔄 تمدید",
            callback_data=f"renew:{service_id}"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📊 افزایش حجم",
            callback_data=f"increase:{service_id}"
        )
    )

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("config:"))
def service_config(call):
    service_id = int(call.data.split(":")[1])
    user_id = internal_user_id(call.from_user.id)

    service = db_execute("""
    SELECT * FROM services
    WHERE id=? AND user_id=?
    """, (service_id, user_id), fetchone=True)

    if not service:
        return

    config = service["config"] or "کانفیگ هنوز موجود نیست."

    bot.send_message(
        call.message.chat.id,
        f"🔐 <b>کانفیگ سرویس</b>\n\n"
        f"<code>{config}</code>"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("renew:"))
def renew_service(call):
    bot.send_message(
        call.message.chat.id,
        "🔄 تمدید سرویس از داخل سیستم پرداخت انجام می‌شود.\n\n"
        "در مرحله بعد پلن تمدید را انتخاب می‌کنیم."
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("increase:"))
def increase_service(call):
    bot.send_message(
        call.message.chat.id,
        "📊 افزایش حجم آماده مدیریت است.\n\n"
        "در مرحله بعد حجم‌های قابل خرید نمایش داده می‌شوند."
    )


# ============================================================
# FREE TRIAL
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🎁 تست رایگان")
def free_trial(message):
    user = get_user(message.from_user.id)

    if get_setting("trial_enabled", "1") != "1":
        bot.send_message(
            message.chat.id,
            "❌ تست رایگان غیرفعال است."
        )
        return

    existing = db_execute("""
    SELECT id FROM services
    WHERE user_id=? AND plan_id IS NULL
    LIMIT 1
    """, (user["id"],), fetchone=True)

    if existing:
        bot.send_message(
            message.chat.id,
            "❌ شما قبلاً از تست رایگان استفاده کرده‌اید."
        )
        return

    volume = int(get_setting("trial_volume", "5"))
    duration = int(get_setting("trial_duration", "1"))
    devices = int(get_setting("trial_devices", "1"))

    panel = db_execute("""
    SELECT * FROM panels
    WHERE active=1
    ORDER BY assigned_sales ASC, id ASC
    LIMIT 1
    """, fetchone=True)

    if not panel:
        bot.send_message(
            message.chat.id,
            "❌ در حال حاضر پنل فعالی برای تست وجود ندارد."
        )
        return

    fake_plan = {
        "id": None,
        "name": "Free Trial",
        "price": 0,
        "volume": volume,
        "duration": duration,
        "devices": devices
    }

    result = pasarguard_create_service(
        panel=panel,
        telegram_user=user,
        plan=fake_plan
    )

    if not result["success"]:
        bot.send_message(
            message.chat.id,
            "❌ ساخت تست رایگان انجام نشد."
        )
        return

    service = create_local_service(
        user=user,
        plan=fake_plan,
        panel=panel,
        result=result
    )

    bot.send_message(
        message.chat.id,
        "🎁 <b>تست رایگان فعال شد!</b>\n\n"
        f"📊 حجم: {volume} GB\n"
        f"⏳ مدت: {duration} روز\n"
        f"📱 دستگاه: {devices}\n\n"
        f"🔐 کانفیگ:\n"
        f"<code>{service['config']}</code>"
    )


# ============================================================
# TRANSACTIONS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "📜 تراکنش‌های من")
def my_transactions(message):
    user_id = internal_user_id(message.from_user.id)

    rows = db_execute("""
    SELECT * FROM transactions
    WHERE user_id=?
    ORDER BY id DESC
    LIMIT 30
    """, (user_id,), fetchall=True)

    if not rows:
        bot.send_message(
            message.chat.id,
            "📭 تراکنشی ندارید."
        )
        return

    text = ["📜 <b>تراکنش‌های من</b>\n"]

    for row in rows:
        text.append(
            f"🧾 {row['description']}\n"
            f"💰 {row['amount']:,} تومان\n"
            f"📅 {row['created_at']}\n"
            f"🔖 {row['reference'] or '---'}\n"
        )

    bot.send_message(
        message.chat.id,
        "\n".join(text)
    )


# ============================================================
# RESELLER
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🤝 پنل نمایندگی")
def reseller_menu(message):
    user = get_user(message.from_user.id)

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🛒 خرید پنل نمایندگی",
            callback_data="reseller_buy"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🖥 پنل‌های من",
            callback_data="reseller_panels"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "👥 کاربران من",
            callback_data="reseller_users"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📈 آمار فروش",
            callback_data="reseller_stats"
        )
    )

    bot.send_message(
        message.chat.id,
        "🤝 <b>پنل نمایندگی</b>\n\n"
        "از این قسمت می‌توانید نمایندگی خود را مدیریت کنید.",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "reseller_buy")
def reseller_buy(call):
    plans = db_execute("""
    SELECT * FROM reseller_plans
    WHERE active=1
    ORDER BY id
    """, fetchall=True)

    if not plans:
        bot.send_message(
            call.message.chat.id,
            "📭 پلن نمایندگی موجود نیست."
        )
        return

    kb = types.InlineKeyboardMarkup()

    for plan in plans:
        kb.add(
            types.InlineKeyboardButton(
                f"🤝 {plan['name']} | {plan['price']:,}",
                callback_data=f"rplan:{plan['id']}"
            )
        )

    bot.send_message(
        call.message.chat.id,
        "🤝 پلن نمایندگی را انتخاب کنید:",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("rplan:"))
def reseller_plan(call):
    plan_id = int(call.data.split(":")[1])

    plan = db_execute(
        "SELECT * FROM reseller_plans WHERE id=? AND active=1",
        (plan_id,),
        fetchone=True
    )

    if not plan:
        return

    bot.send_message(
        call.message.chat.id,
        f"🤝 <b>{plan['name']}</b>\n\n"
        f"💰 قیمت: {plan['price']:,} تومان\n"
        f"👥 ظرفیت: {plan['capacity']}\n"
        f"⏳ مدت: {plan['duration']} روز\n\n"
        "خرید پنل نمایندگی در مرحله پرداخت انجام می‌شود."
    )


# ============================================================
# LICENSE
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🎫 خرید لایسنس ربات")
def license_menu(message):
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🎫 خرید لایسنس",
            callback_data="license_buy"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📜 لایسنس‌های من",
            callback_data="license_my"
        )
    )

    bot.send_message(
        message.chat.id,
        "🎫 <b>لایسنس ربات</b>",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "license_buy")
def license_buy(call):
    bot.send_message(
        call.message.chat.id,
        "🎫 پلن‌های لایسنس در حال تنظیم هستند."
    )


@bot.callback_query_handler(func=lambda call: call.data == "license_my")
def license_my(call):
    user_id = internal_user_id(call.from_user.id)

    rows = db_execute("""
    SELECT * FROM licenses
    WHERE user_id=?
    ORDER BY id DESC
    """, (user_id,), fetchall=True)

    if not rows:
        bot.send_message(
            call.message.chat.id,
            "📭 لایسنسی ندارید."
        )
        return

    text = ["🎫 <b>لایسنس‌های من</b>\n"]

    for row in rows:
        text.append(
            f"🔑 <code>{row['license_key']}</code>\n"
            f"📅 {row['expires_at']}\n"
            f"📌 {row['status']}\n"
        )

    bot.send_message(
        call.message.chat.id,
        "\n".join(text)
    )


# ============================================================
# SUPPORT
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🆘 پشتیبانی")
def support(message):
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🎫 تیکت جدید",
            callback_data="ticket_new"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📂 تیکت‌های من",
            callback_data="ticket_list"
        )
    )

    support_username = get_setting(
        "support_username",
        ""
    ).strip()

    if support_username:
        if support_username.startswith("@"):
            username = support_username[1:]
        else:
            username = support_username

        kb.add(
            types.InlineKeyboardButton(
                "👨‍💻 ارتباط مستقیم",
                url=f"https://t.me/{username}"
            )
        )

    bot.send_message(
        message.chat.id,
        "🆘 <b>مرکز پشتیبانی</b>\n\n"
        "برای ارتباط با پشتیبانی تیکت ایجاد کنید.",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "ticket_new")
def ticket_new(call):
    bot.send_message(
        call.message.chat.id,
        "🎫 موضوع یا متن مشکل خود را ارسال کنید:"
    )

    bot.register_next_step_handler(
        call.message,
        create_ticket
    )


def create_ticket(message):
    user_id = internal_user_id(message.from_user.id)

    db_execute("""
    INSERT INTO tickets
    (user_id, subject, status, created_at, updated_at)
    VALUES (?, ?, 'open', ?, ?)
    """, (
        user_id,
        message.text or "بدون موضوع",
        now(),
        now()
    ))

    ticket = db_execute("""
    SELECT * FROM tickets
    WHERE user_id=?
    ORDER BY id DESC LIMIT 1
    """, (user_id,), fetchone=True)

    db_execute("""
    INSERT INTO ticket_messages
    (ticket_id, sender_id, message, created_at)
    VALUES (?, ?, ?, ?)
    """, (
        ticket["id"],
        message.from_user.id,
        message.text or "",
        now()
    ))

    bot.send_message(
        message.chat.id,
        f"✅ تیکت <b>#{ticket['id']}</b> ایجاد شد.\n\n"
        "پشتیبانی به‌زودی پاسخ می‌دهد."
    )

    if SUPER_ADMIN_ID:
        bot.send_message(
            SUPER_ADMIN_ID,
            f"🎫 <b>تیکت جدید #{ticket['id']}</b>\n\n"
            f"👤 Telegram ID: {message.from_user.id}\n"
            f"📝 {message.text}"
        )


@bot.callback_query_handler(func=lambda call: call.data == "ticket_list")
def ticket_list(call):
    user_id = internal_user_id(call.from_user.id)

    tickets = db_execute("""
    SELECT * FROM tickets
    WHERE user_id=?
    ORDER BY id DESC
    LIMIT 20
    """, (user_id,), fetchall=True)

    if not tickets:
        bot.send_message(
            call.message.chat.id,
            "📭 تیکتی ندارید."
        )
        return

    text = ["🎫 <b>تیکت‌های من</b>\n"]

    for ticket in tickets:
        text.append(
            f"#{ticket['id']} — {ticket['subject']}\n"
            f"📌 {ticket['status']}\n"
        )

    bot.send_message(
        call.message.chat.id,
        "\n".join(text)
    )


# ============================================================
# GUIDE
# ============================================================

@bot.message_handler(func=lambda m: m.text == "📚 راهنما")
def guide(message):
    bot.send_message(
        message.chat.id,
        "📚 <b>راهنمای VirangarVPN</b>\n\n"
        "🛒 خرید VPN\n"
        "از بخش خرید، پلن موردنظر را انتخاب کنید.\n\n"
        "🛡 سرویس‌های من\n"
        "مشاهده و مدیریت سرویس‌های فعال.\n\n"
        "💰 کیف پول\n"
        "شارژ حساب و مشاهده تراکنش‌ها.\n\n"
        "🤝 نمایندگی\n"
        "مدیریت پنل و کاربران نمایندگی.\n\n"
        "🆘 پشتیبانی\n"
        "ایجاد و پیگیری تیکت."
    )


# ============================================================
# ACCOUNT
# ============================================================

@bot.message_handler(func=lambda m: m.text == "⚙️ حساب کاربری")
def account(message):
    user = get_user(message.from_user.id)

    username = (
        f"@{user['username']}"
        if user and user["username"]
        else "بدون یوزرنیم"
    )

    bot.send_message(
        message.chat.id,
        "⚙️ <b>حساب کاربری</b>\n\n"
        f"🆔 Telegram ID: <code>{message.from_user.id}</code>\n"
        f"👤 Username: {username}\n"
        f"💰 موجودی: {user['balance']:,} تومان\n"
        f"📅 عضویت: {user['created_at']}"
    )


# ============================================================
# ADMIN PANEL
# ============================================================

@bot.message_handler(commands=["admin"])
def admin_command(message):
    if not is_admin(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "⛔ دسترسی ندارید."
        )
        return

    bot.send_message(
        message.chat.id,
        "👑 <b>پنل مدیریت VirangarVPN</b>",
        reply_markup=admin_keyboard()
    )


@bot.message_handler(func=lambda m: m.text == "📊 داشبورد")
@admin_only
def admin_dashboard(message):
    users = db_execute(
        "SELECT COUNT(*) c FROM users",
        fetchone=True
    )["c"]

    active_users = db_execute("""
    SELECT COUNT(DISTINCT user_id) c
    FROM services
    WHERE status='active'
    """, fetchone=True)["c"]

    services = db_execute(
        "SELECT COUNT(*) c FROM services WHERE status='active'",
        fetchone=True
    )["c"]

    revenue = db_execute("""
    SELECT COALESCE(SUM(amount),0) total
    FROM payments
    WHERE status='approved'
    """, fetchone=True)["total"]

    panels = db_execute(
        "SELECT COUNT(*) c FROM panels WHERE active=1",
        fetchone=True
    )["c"]

    bot.send_message(
        message.chat.id,
        "📊 <b>داشبورد</b>\n\n"
        f"👥 کاربران: {users}\n"
        f"🟢 کاربران فعال: {active_users}\n"
        f"📦 سرویس فعال: {services}\n"
        f"🖥 پنل فعال: {panels}\n"
        f"💰 درآمد: {revenue:,} تومان"
    )


# ============================================================
# ADMIN USERS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "👥 کاربران")
@admin_only
def admin_users(message):
    count = db_execute(
        "SELECT COUNT(*) c FROM users",
        fetchone=True
    )["c"]

    bot.send_message(
        message.chat.id,
        f"👥 <b>مدیریت کاربران</b>\n\n"
        f"تعداد کاربران: {count}\n\n"
        "برای جستجو، Telegram ID کاربر را ارسال کنید."
    )

    bot.register_next_step_handler(
        message,
        admin_user_search
    )


def admin_user_search(message):
    try:
        tg_id = int(message.text.strip())
    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ آیدی نامعتبر."
        )
        return

    user = get_user(tg_id)

    if not user:
        bot.send_message(
            message.chat.id,
            "❌ کاربر پیدا نشد."
        )
        return

    services = db_execute("""
    SELECT COUNT(*) c FROM services
    WHERE user_id=?
    """, (user["id"],), fetchone=True)["c"]

    text = (
        "👤 <b>اطلاعات کاربر</b>\n\n"
        f"🆔 {user['telegram_id']}\n"
        f"👤 @{user['username'] or '---'}\n"
        f"💰 موجودی: {user['balance']:,}\n"
        f"📦 سرویس‌ها: {services}\n"
        f"🚫 مسدود: {'بله' if user['is_blocked'] else 'خیر'}"
    )

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🚫 مسدود/رفع مسدودی",
            callback_data=f"blockuser:{tg_id}"
        )
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("blockuser:"))
def block_user(call):
    if not is_superadmin(call.from_user.id):
        return

    tg_id = int(call.data.split(":")[1])

    user = get_user(tg_id)

    if not user:
        return

    new_status = 0 if user["is_blocked"] else 1

    db_execute("""
    UPDATE users
    SET is_blocked=?, updated_at=?
    WHERE telegram_id=?
    """, (
        new_status,
        now(),
        tg_id
    ))

    bot.answer_callback_query(
        call.id,
        "انجام شد ✅"
    )


# ============================================================
# ADMIN PANELS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🖥 پنل‌ها")
@admin_only
def admin_panels(message):
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "➕ افزودن پنل",
            callback_data="panel_add"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📋 لیست پنل‌ها",
            callback_data="panel_list"
        )
    )

    bot.send_message(
        message.chat.id,
        "🖥 <b>مدیریت پنل‌های PasarGuard</b>\n\n"
        "اتصال پنل‌ها از این قسمت مدیریت می‌شود.",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "panel_add")
def panel_add(call):
    if not is_admin(call.from_user.id):
        return

    bot.send_message(
        call.message.chat.id,
        "🖥 نام پنل را ارسال کنید:"
    )

    bot.register_next_step_handler(
        call.message,
        panel_add_name
    )


def panel_add_name(message):
    name = message.text.strip()

    bot.send_message(
        message.chat.id,
        "🌐 آدرس پنل/API را ارسال کنید:"
    )

    bot.register_next_step_handler(
        message,
        panel_add_url,
        name
    )


def panel_add_url(message, name):
    url = message.text.strip()

    bot.send_message(
        message.chat.id,
        "👤 Username پنل را ارسال کنید:"
    )

    bot.register_next_step_handler(
        message,
        panel_add_username,
        name,
        url
    )


def panel_add_username(message, name, url):
    username = message.text.strip()

    bot.send_message(
        message.chat.id,
        "🔐 Password پنل را ارسال کنید:"
    )

    bot.register_next_step_handler(
        message,
        panel_add_password,
        name,
        url,
        username
    )


def panel_add_password(message, name, url, username):
    password = message.text.strip()

    db_execute("""
    INSERT INTO panels
    (name, url, username, password,
     active, status, capacity,
     assigned_sales, created_at, updated_at)
    VALUES (?, ?, ?, ?, 1, 'unknown', 0, 0, ?, ?)
    """, (
        name,
        url,
        username,
        password,
        now(),
        now()
    ))

    bot.send_message(
        message.chat.id,
        "✅ پنل با موفقیت به دیتابیس اضافه شد.\n\n"
        "🖥 مدیریت این پنل از داخل ربات انجام می‌شود."
    )


@bot.callback_query_handler(func=lambda call: call.data == "panel_list")
def panel_list(call):
    if not is_admin(call.from_user.id):
        return

    panels = db_execute("""
    SELECT * FROM panels
    ORDER BY id
    """, fetchall=True)

    if not panels:
        bot.send_message(
            call.message.chat.id,
            "📭 هنوز پنلی اضافه نشده."
        )
        return

    kb = types.InlineKeyboardMarkup()

    for panel in panels:
        status = "🟢" if panel["active"] else "🔴"

        kb.add(
            types.InlineKeyboardButton(
                f"{status} {panel['name']}",
                callback_data=f"panel:{panel['id']}"
            )
        )

    bot.send_message(
        call.message.chat.id,
        "🖥 <b>پنل‌ها</b>",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("panel:"))
def panel_details(call):
    if not is_admin(call.from_user.id):
        return

    panel_id = int(call.data.split(":")[1])

    panel = db_execute(
        "SELECT * FROM panels WHERE id=?",
        (panel_id,),
        fetchone=True
    )

    if not panel:
        return

    users = db_execute("""
    SELECT COUNT(*) c
    FROM services
    WHERE panel_id=?
    """, (panel_id,), fetchone=True)["c"]

    text = (
        f"🖥 <b>{panel['name']}</b>\n\n"
        f"🆔 ID: {panel['id']}\n"
        f"🌐 URL: {panel['url']}\n"
        f"📌 وضعیت: {panel['status']}\n"
        f"👥 سرویس‌ها: {users}\n"
        f"📊 ظرفیت: {panel['capacity']}\n"
        f"🟢 فعال: {'بله' if panel['active'] else 'خیر'}"
    )

    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton(
            "🔌 تست اتصال",
            callback_data=f"paneltest:{panel_id}"
        ),
        types.InlineKeyboardButton(
            "🔄 فعال/غیرفعال",
            callback_data=f"paneltoggle:{panel_id}"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🗑 حذف پنل",
            callback_data=f"paneldelete:{panel_id}"
        )
    )

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=kb
    )


# ============================================================
# PANEL TEST
# ============================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("paneltest:"))
def panel_test(call):
    if not is_admin(call.from_user.id):
        return

    panel_id = int(call.data.split(":")[1])

    panel = db_execute(
        "SELECT * FROM panels WHERE id=?",
        (panel_id,),
        fetchone=True
    )

    if not panel:
        return

    result = pasarguard_test_panel(panel)

    status = "online" if result["success"] else "offline"

    db_execute("""
    UPDATE panels
    SET status=?, updated_at=?
    WHERE id=?
    """, (
        status,
        now(),
        panel_id
    ))

    if result["success"]:
        bot.answer_callback_query(
            call.id,
            "اتصال موفق بود ✅",
            show_alert=True
        )
    else:
        bot.answer_callback_query(
            call.id,
            f"اتصال ناموفق: {result['error']}",
            show_alert=True
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("paneltoggle:"))
def panel_toggle(call):
    if not is_admin(call.from_user.id):
        return

    panel_id = int(call.data.split(":")[1])

    panel = db_execute(
        "SELECT active FROM panels WHERE id=?",
        (panel_id,),
        fetchone=True
    )

    if not panel:
        return

    new_status = 0 if panel["active"] else 1

    db_execute("""
    UPDATE panels
    SET active=?, updated_at=?
    WHERE id=?
    """, (
        new_status,
        now(),
        panel_id
    ))

    bot.answer_callback_query(
        call.id,
        "تغییر کرد ✅"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("paneldelete:"))
def panel_delete(call):
    if not is_superadmin(call.from_user.id):
        return

    panel_id = int(call.data.split(":")[1])

    db_execute(
        "DELETE FROM panels WHERE id=?",
        (panel_id,)
    )

    bot.answer_callback_query(
        call.id,
        "پنل حذف شد 🗑"
    )


# ============================================================
# ADMIN PLANS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "💎 پلن‌های VPN")
@admin_only
def admin_plans(message):
    plans = db_execute("""
    SELECT * FROM plans
    ORDER BY sort_order, id
    """, fetchall=True)

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "➕ افزودن پلن",
            callback_data="plan_admin_add"
        )
    )

    for plan in plans:
        status = "🟢" if plan["active"] else "🔴"

        kb.add(
            types.InlineKeyboardButton(
                f"{status} {plan['name']}",
                callback_data=f"planadmin:{plan['id']}"
            )
        )

    bot.send_message(
        message.chat.id,
        "💎 <b>مدیریت پلن‌ها</b>",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("planadmin:"))
def plan_admin_details(call):
    if not is_admin(call.from_user.id):
        return

    plan_id = int(call.data.split(":")[1])

    plan = db_execute(
        "SELECT * FROM plans WHERE id=?",
        (plan_id,),
        fetchone=True
    )

    if not plan:
        return

    text = (
        f"💎 <b>{plan['name']}</b>\n\n"
        f"💰 قیمت: {plan['price']:,}\n"
        f"📊 حجم: {plan['volume']} GB\n"
        f"⏳ مدت: {plan['duration']} روز\n"
        f"📱 دستگاه: {plan['devices']}\n"
        f"🤝 قیمت نماینده: {plan['reseller_price']:,}\n"
        f"📍 لوکیشن: {plan['location'] or '---'}\n"
        f"🖥 Panel ID: {plan['panel_id'] or '---'}"
    )

    bot.send_message(
        call.message.chat.id,
        text
    )


# ============================================================
# ADMIN SERVICES
# ============================================================

@bot.message_handler(func=lambda m: m.text == "📦 سرویس‌ها")
@admin_only
def admin_services(message):
    count = db_execute(
        "SELECT COUNT(*) c FROM services",
        fetchone=True
    )["c"]

    active = db_execute("""
    SELECT COUNT(*) c FROM services
    WHERE status='active'
    """, fetchone=True)["c"]

    bot.send_message(
        message.chat.id,
        "📦 <b>مدیریت سرویس‌ها</b>\n\n"
        f"کل سرویس‌ها: {count}\n"
        f"سرویس فعال: {active}\n\n"
        "جستجوی سرویس با ID در نسخه مدیریت کامل انجام می‌شود."
    )


# ============================================================
# ADMIN RESELLERS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🤝 نمایندگان")
@admin_only
def admin_resellers(message):
    count = db_execute("""
    SELECT COUNT(*) c FROM users
    WHERE is_reseller=1
    """, fetchone=True)["c"]

    bot.send_message(
        message.chat.id,
        "🤝 <b>مدیریت نمایندگان</b>\n\n"
        f"تعداد نمایندگان: {count}"
    )


# ============================================================
# ADMIN PAYMENTS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "💰 پرداخت‌ها")
@admin_only
def admin_payments(message):
    pending = db_execute("""
    SELECT COUNT(*) c FROM payments
    WHERE status='pending'
    """, fetchone=True)["c"]

    approved = db_execute("""
    SELECT COALESCE(SUM(amount),0) total
    FROM payments
    WHERE status='approved'
    """, fetchone=True)["total"]

    bot.send_message(
        message.chat.id,
        "💰 <b>مدیریت پرداخت‌ها</b>\n\n"
        f"⏳ در انتظار بررسی: {pending}\n"
        f"✅ مجموع پرداخت تأییدشده: {approved:,} تومان"
    )


# ============================================================
# ADMIN PAYMENT SETTINGS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "💳 تنظیمات پرداخت")
@admin_only
def payment_settings(message):
    mode = get_setting("payment_mode", "manual")

    card = get_setting("card_number", "")
    holder = get_setting("card_holder", "")

    manual = get_setting(
        "manual_payment_enabled",
        "1"
    )

    online = get_setting(
        "online_payment_enabled",
        "0"
    )

    bot.send_message(
        message.chat.id,
        "💳 <b>تنظیمات پرداخت</b>\n\n"
        f"⚙️ حالت: {mode}\n"
        f"💳 کارت به کارت: {'فعال' if manual == '1' else 'غیرفعال'}\n"
        f"🌐 آنلاین: {'فعال' if online == '1' else 'غیرفعال'}\n"
        f"💳 کارت: {card or 'تنظیم نشده'}\n"
        f"👤 صاحب کارت: {holder or 'تنظیم نشده'}\n\n"
        "برای تغییر شماره کارت از دستور /setcard استفاده کنید."
    )


@bot.message_handler(commands=["setcard"])
@admin_only
def setcard(message):
    bot.send_message(
        message.chat.id,
        "💳 شماره کارت را ارسال کنید:"
    )

    bot.register_next_step_handler(
        message,
        setcard_number
    )


def setcard_number(message):
    set_setting(
        "card_number",
        message.text.strip()
    )

    bot.send_message(
        message.chat.id,
        "👤 نام صاحب کارت را ارسال کنید:"
    )

    bot.register_next_step_handler(
        message,
        setcard_holder
    )


def setcard_holder(message):
    set_setting(
        "card_holder",
        message.text.strip()
    )

    bot.send_message(
        message.chat.id,
        "✅ اطلاعات کارت ذخیره شد."
    )


# ============================================================
# ADMIN TRIAL
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🎁 تست رایگان", content_types=["text"])
def admin_trial_conflict(message):
    # User version handler takes precedence only when not admin.
    # Admin gets this informational handler.
    if not is_admin(message.from_user.id):
        return

    bot.send_message(
        message.chat.id,
        "🎁 <b>تنظیمات تست رایگان</b>\n\n"
        f"وضعیت: {get_setting('trial_enabled')}\n"
        f"حجم: {get_setting('trial_volume')} GB\n"
        f"مدت: {get_setting('trial_duration')} روز\n"
        f"دستگاه: {get_setting('trial_devices')}\n"
        f"محدودیت: {get_setting('trial_limit')}"
    )


# ============================================================
# BROADCAST
# ============================================================

@bot.message_handler(func=lambda m: m.text == "📢 ارسال همگانی")
@admin_only
def broadcast(message):
    bot.send_message(
        message.chat.id,
        "📢 متن پیام همگانی را ارسال کنید:"
    )

    bot.register_next_step_handler(
        message,
        broadcast_send
    )


def broadcast_send(message):
    users = db_execute("""
    SELECT telegram_id FROM users
    WHERE is_blocked=0
    """, fetchall=True)

    sent = 0

    for user in users:
        try:
            bot.send_message(
                user["telegram_id"],
                message.text
            )
            sent += 1
            time.sleep(0.04)
        except Exception:
            pass

    bot.send_message(
        message.chat.id,
        f"✅ ارسال انجام شد.\n"
        f"تعداد موفق: {sent}"
    )


# ============================================================
# FORCE JOIN ADMIN
# ============================================================

@bot.message_handler(func=lambda m: m.text == "📢 عضویت اجباری")
@admin_only
def admin_force_join(message):
    enabled = get_setting(
        "force_join_enabled",
        "0"
    )

    channel = get_setting(
        "force_join_channel",
        ""
    )

    url = get_setting(
        "force_join_url",
        ""
    )

    bot.send_message(
        message.chat.id,
        "📢 <b>عضویت اجباری</b>\n\n"
        f"وضعیت: {'فعال' if enabled == '1' else 'غیرفعال'}\n"
        f"کانال: {channel or '---'}\n"
        f"لینک: {url or '---'}\n\n"
        "برای تغییر از /setforcejoin استفاده کنید."
    )


@bot.message_handler(commands=["setforcejoin"])
@admin_only
def setforcejoin(message):
    bot.send_message(
        message.chat.id,
        "📢 آیدی کانال را ارسال کنید:"
    )

    bot.register_next_step_handler(
        message,
        setforce_channel
    )


def setforce_channel(message):
    set_setting(
        "force_join_channel",
        message.text.strip()
    )

    bot.send_message(
        message.chat.id,
        "🔗 لینک کانال را ارسال کنید:"
    )

    bot.register_next_step_handler(
        message,
        setforce_url
    )


def setforce_url(message):
    set_setting(
        "force_join_url",
        message.text.strip()
    )

    set_setting(
        "force_join_enabled",
        "1"
    )

    bot.send_message(
        message.chat.id,
        "✅ عضویت اجباری فعال شد."
    )


# ============================================================
# ADMIN TICKETS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🎫 تیکت‌ها")
@admin_only
def admin_tickets(message):
    tickets = db_execute("""
    SELECT tickets.*, users.telegram_id
    FROM tickets
    JOIN users ON users.id=tickets.user_id
    ORDER BY tickets.id DESC
    LIMIT 30
    """, fetchall=True)

    if not tickets:
        bot.send_message(
            message.chat.id,
            "📭 تیکتی وجود ندارد."
        )
        return

    lines = ["🎫 <b>آخرین تیکت‌ها</b>\n"]

    for ticket in tickets:
        lines.append(
            f"#{ticket['id']} | "
            f"{ticket['status']} | "
            f"{ticket['telegram_id']}\n"
            f"{ticket['subject']}\n"
        )

    bot.send_message(
        message.chat.id,
        "\n".join(lines)
    )


# ============================================================
# ADMIN MANAGEMENT
# ============================================================

@bot.message_handler(func=lambda m: m.text == "👑 مدیران")
@admin_only
def admin_admins(message):
    admins = db_execute("""
    SELECT * FROM admins
    ORDER BY id
    """, fetchall=True)

    lines = ["👑 <b>مدیران</b>\n"]

    for admin in admins:
        lines.append(
            f"🆔 {admin['telegram_id']}\n"
            f"🎖 {admin['role']}\n"
            f"📌 {'فعال' if admin['is_active'] else 'غیرفعال'}\n"
        )

    lines.append(
        "\nبرای افزودن مدیر: /addadmin TELEGRAM_ID"
    )

    bot.send_message(
        message.chat.id,
        "\n".join(lines)
    )


@bot.message_handler(commands=["addadmin"])
def add_admin(message):
    if not is_superadmin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2:
        bot.send_message(
            message.chat.id,
            "استفاده:\n/addadmin TELEGRAM_ID"
        )
        return

    try:
        tg_id = int(parts[1])
    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ آیدی نامعتبر."
        )
        return

    db_execute("""
    INSERT OR REPLACE INTO admins
    (telegram_id, role, is_active, created_at)
    VALUES (?, 'admin', 1, ?)
    """, (
        tg_id,
        now()
    ))

    bot.send_message(
        message.chat.id,
        "✅ مدیر اضافه شد."
    )


# ============================================================
# BACKUP / RESTORE
# ============================================================

@bot.message_handler(func=lambda m: m.text == "💾 Backup / Restore")
@admin_only
def backup_menu(message):
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "💾 Backup",
            callback_data="backup_create"
        )
    )

    bot.send_message(
        message.chat.id,
        "💾 <b>Backup / Restore</b>",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: call.data == "backup_create")
def backup_create(call):
    if not is_superadmin(call.from_user.id):
        return

    backup_dir = "backups"

    os.makedirs(
        backup_dir,
        exist_ok=True
    )

    filename = (
        f"virangarvpn_"
        f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
    )

    path = os.path.join(
        backup_dir,
        filename
    )

    shutil.copy2(
        DB_PATH,
        path
    )

    with open(path, "rb") as file:
        bot.send_document(
            call.message.chat.id,
            file,
            caption="💾 Backup دیتابیس"
        )

    bot.answer_callback_query(
        call.id,
        "Backup ساخته شد ✅"
    )


# ============================================================
# REPORTS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "📈 گزارش‌ها")
@admin_only
def reports(message):
    sales = db_execute("""
    SELECT COUNT(*) c
    FROM payments
    WHERE status='approved'
    """, fetchone=True)["c"]

    revenue = db_execute("""
    SELECT COALESCE(SUM(amount),0) total
    FROM payments
    WHERE status='approved'
    """, fetchone=True)["total"]

    services = db_execute("""
    SELECT COUNT(*) c
    FROM services
    WHERE status='active'
    """, fetchone=True)["c"]

    bot.send_message(
        message.chat.id,
        "📈 <b>گزارش</b>\n\n"
        f"🛒 فروش موفق: {sales}\n"
        f"💰 درآمد: {revenue:,} تومان\n"
        f"📦 سرویس فعال: {services}"
    )


# ============================================================
# SECURITY
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🛡 امنیت")
@admin_only
def security(message):
    bot.send_message(
        message.chat.id,
        "🛡 <b>امنیت</b>\n\n"
        "✅ کنترل دسترسی مدیران فعال است.\n"
        "✅ کاربران مسدودشده امکان استفاده ندارند.\n"
        "✅ عملیات مدیریت نیازمند دسترسی است."
    )


# ============================================================
# SETTINGS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "⚙️ تنظیمات")
@admin_only
def settings_menu(message):
    bot.send_message(
        message.chat.id,
        "⚙️ <b>تنظیمات سیستم</b>\n\n"
        f"🤖 نام: {BOT_NAME}\n"
        f"💾 دیتابیس: {DB_PATH}\n"
        f"🛡 Force Join: {get_setting('force_join_enabled')}\n"
        f"🎁 Trial: {get_setting('trial_enabled')}\n"
        f"💳 Payment: {get_setting('payment_mode')}"
    )


# ============================================================
# SYSTEM STATUS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🔧 وضعیت سیستم")
@admin_only
def system_status(message):
    try:
        db_execute(
            "SELECT 1",
            fetchone=True
        )

        db_status = "🟢 OK"

    except Exception:
        db_status = "🔴 ERROR"

    panels = db_execute("""
    SELECT COUNT(*) c FROM panels
    WHERE active=1
    """, fetchone=True)["c"]

    bot.send_message(
        message.chat.id,
        "🔧 <b>وضعیت سیستم</b>\n\n"
        f"🤖 Bot: 🟢 Running\n"
        f"💾 Database: {db_status}\n"
        f"🖥 Active Panels: {panels}\n"
        f"🐍 Python: {os.sys.version.split()[0]}"
    )


# ============================================================
# USER MENU FROM ADMIN
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🏠 منوی کاربر")
@admin_only
def back_user_menu(message):
    bot.send_message(
        message.chat.id,
        "🏠 منوی کاربر",
        reply_markup=user_keyboard()
    )


# ============================================================
# PASARGUARD CLIENT
# ============================================================

def pasarguard_test_panel(panel):
    """
    این قسمت عمداً endpoint جعلی ندارد.

    چون endpoint و authentication دقیق PasarGuard
    باید مطابق نسخه/API واقعی پنل تنظیم شود.
    """

    url = (panel["url"] or "").rstrip("/")

    if not url:
        return {
            "success": False,
            "error": "Panel URL is empty"
        }

    try:
        response = requests.get(
            url,
            timeout=8,
            verify=False
        )

        if response.status_code < 500:
            return {
                "success": True,
                "error": ""
            }

        return {
            "success": False,
            "error": f"HTTP {response.status_code}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def pasarguard_create_service(
    panel,
    telegram_user,
    plan
):
    """
    مهم:

    این تابع محل اتصال واقعی به PasarGuard است.

    endpoint ساخت کاربر/سرویس در نسخه‌های مختلف
    می‌تواند متفاوت باشد.

    تا API واقعی پنل مشخص نباشد، کانفیگ ساختگی تولید نمی‌کنیم.
    """

    return {
        "success": False,
        "error": (
            "PasarGuard API endpoint for service creation "
            "is not configured."
        )
    }


# ============================================================
# LOCAL SERVICE
# ============================================================

def create_local_service(
    user,
    plan,
    panel,
    result
):
    config = result.get(
        "config",
        ""
    )

    qr = result.get(
        "qr",
        ""
    )

    expires = (
        datetime.utcnow()
        + timedelta(days=int(plan["duration"]))
    ).strftime("%Y-%m-%d %H:%M:%S")

    username = result.get(
        "username",
        f"tg_{user['telegram_id']}"
    )

    db_execute("""
    INSERT INTO services
    (user_id, plan_id, panel_id,
     username, config, qr,
     volume, used_volume,
     duration, devices,
     expires_at, status,
     created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, 'active', ?, ?)
    """, (
        user["id"],
        plan["id"],
        panel["id"],
        username,
        config,
        qr,
        plan["volume"],
        plan["duration"],
        plan["devices"],
        expires,
        now(),
        now()
    ))

    service = db_execute("""
    SELECT * FROM services
    WHERE user_id=?
    ORDER BY id DESC
    LIMIT 1
    """, (
        user["id"],
    ), fetchone=True)

    return service


# ============================================================
# FALLBACK
# ============================================================

@bot.message_handler(func=lambda message: True)
def fallback(message):
    if not message.text:
        return

    if message.text.startswith("/"):
        return

    user = get_user(message.from_user.id)

    if user and user["is_blocked"]:
        bot.send_message(
            message.chat.id,
            "⛔ حساب شما مسدود است."
        )
        return

    bot.send_message(
        message.chat.id,
        "از منوی زیر استفاده کنید.",
        reply_markup=(
            admin_keyboard()
            if is_admin(message.from_user.id)
            else user_keyboard()
        )
    )


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":
    init_db()

    print("=" * 50)
    print("VirangarVPN Bot is running...")
    print(f"Database: {DB_PATH}")
    print(f"Super Admin: {SUPER_ADMIN_ID}")
    print("=" * 50)

    bot.infinity_polling(
        skip_pending=True,
        allowed_updates=[
            "message",
            "callback_query"
        ]
    )
