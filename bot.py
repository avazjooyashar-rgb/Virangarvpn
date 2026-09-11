# ============================================================
# VirangarVPN
# Single-file Telegram VPN Sales & Management Bot
# ============================================================

import os
import sqlite3
import logging
import uuid
import threading
from datetime import datetime, timedelta

import telebot
from telebot import types
from dotenv import load_dotenv

# ============================================================
# CONFIG
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0") or 0)

CARD_NUMBER = os.getenv("CARD_NUMBER", "").strip()
CARD_HOLDER = os.getenv("CARD_HOLDER", "").strip()

SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").strip()

PAYMENT_MODE = os.getenv("PAYMENT_MODE", "manual").lower().strip()

FORCE_JOIN_ENABLED = os.getenv(
    "FORCE_JOIN_ENABLED", "false"
).lower() == "true"

FORCE_JOIN_CHANNEL = os.getenv(
    "FORCE_JOIN_CHANNEL", ""
).strip()

FORCE_JOIN_CHANNEL_URL = os.getenv(
    "FORCE_JOIN_CHANNEL_URL", ""
).strip()

DB_FILE = "virangarvpn.db"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured in .env")

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ============================================================
# DATABASE
# ============================================================

db_lock = threading.Lock()


def db():
    connection = sqlite3.connect(
        DB_FILE,
        check_same_thread=False
    )
    connection.row_factory = sqlite3.Row
    return connection


def execute(sql, params=(), fetchone=False, fetchall=False):
    with db_lock:
        con = db()
        cur = con.cursor()

        cur.execute(sql, params)

        result = None

        if fetchone:
            result = cur.fetchone()

        elif fetchall:
            result = cur.fetchall()

        con.commit()
        con.close()

        return result


def init_db():
    execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            balance INTEGER DEFAULT 0,
            is_blocked INTEGER DEFAULT 0,
            is_reseller INTEGER DEFAULT 0,
            trial_used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            volume_gb INTEGER NOT NULL,
            duration_days INTEGER NOT NULL,
            devices INTEGER DEFAULT 1,
            reseller_price INTEGER DEFAULT 0,
            location TEXT DEFAULT '',
            panel_id INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT DEFAULT '',
            username TEXT DEFAULT '',
            password TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER DEFAULT 0,
            panel_id INTEGER DEFAULT 0,
            config TEXT DEFAULT '',
            volume_gb INTEGER DEFAULT 0,
            used_gb REAL DEFAULT 0,
            duration_days INTEGER DEFAULT 0,
            devices INTEGER DEFAULT 1,
            expires_at TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER DEFAULT 0,
            amount INTEGER NOT NULL,
            method TEXT DEFAULT 'manual',
            receipt_file_id TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            processed_at TEXT DEFAULT ''
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            created_at TEXT NOT NULL
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS ticket_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS reseller_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            capacity_gb INTEGER NOT NULL,
            duration_days INTEGER NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS reseller_panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            capacity_gb INTEGER NOT NULL,
            used_gb REAL DEFAULT 0,
            expires_at TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            license_key TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
    """)

    # Default VPN plans
    count = execute(
        "SELECT COUNT(*) AS c FROM plans",
        fetchone=True
    )["c"]

    if count == 0:
        execute("""
            INSERT INTO plans
            (name, price, volume_gb, duration_days, devices,
             reseller_price, location, active, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
        """, (
            "اقتصادی 30GB",
            100000,
            30,
            30,
            1,
            80000,
            "Germany"
        ))

        execute("""
            INSERT INTO plans
            (name, price, volume_gb, duration_days, devices,
             reseller_price, location, active, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 2)
        """, (
            "حرفه‌ای 60GB",
            160000,
            60,
            30,
            2,
            130000,
            "Germany"
        ))

        execute("""
            INSERT INTO plans
            (name, price, volume_gb, duration_days, devices,
             reseller_price, location, active, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 3)
        """, (
            "پریمیوم 120GB",
            280000,
            120,
            60,
            3,
            230000,
            "Germany"
        ))

    # Default reseller plan
    count = execute(
        "SELECT COUNT(*) AS c FROM reseller_plans",
        fetchone=True
    )["c"]

    if count == 0:
        execute("""
            INSERT INTO reseller_plans
            (name, price, capacity_gb, duration_days)
            VALUES (?, ?, ?, ?)
        """, (
            "نمایندگی 500GB",
            1500000,
            500,
            30
        ))

    # Default settings
    defaults = {
        "bot_name": "VirangarVPN",
        "trial_volume": "5",
        "trial_days": "2",
        "trial_devices": "1",
        "license_price": "500000",
        "license_days": "30",
    }

    for key, value in defaults.items():
        execute(
            "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
            (key, value)
        )


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def money(value):
    return f"{int(value):,} تومان"


def get_user(tg_id):
    return execute(
        "SELECT * FROM users WHERE telegram_id=?",
        (tg_id,),
        fetchone=True
    )


def ensure_user(user):
    existing = get_user(user.id)

    if not existing:
        execute("""
            INSERT INTO users
            (telegram_id, username, first_name, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            user.id,
            user.username or "",
            user.first_name or "",
            now()
        ))
    else:
        execute("""
            UPDATE users
            SET username=?, first_name=?
            WHERE telegram_id=?
        """, (
            user.username or "",
            user.first_name or "",
            user.id
        ))


def is_admin(user_id):
    return user_id == SUPER_ADMIN_ID


def is_blocked(user_id):
    user = get_user(user_id)
    return bool(user and user["is_blocked"])


def get_setting(key, default=""):
    row = execute(
        "SELECT value FROM settings WHERE key=?",
        (key,),
        fetchone=True
    )

    return row["value"] if row else default


def set_setting(key, value):
    execute("""
        INSERT INTO settings(key,value)
        VALUES(?,?)
        ON CONFLICT(key)
        DO UPDATE SET value=excluded.value
    """, (key, str(value)))


def add_transaction(user_id, amount, tx_type, description):
    execute("""
        INSERT INTO transactions
        (user_id, amount, type, description, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        amount,
        tx_type,
        description,
        now()
    ))


def change_balance(user_id, amount, description):
    execute("""
        UPDATE users
        SET balance = balance + ?
        WHERE telegram_id=?
    """, (
        amount,
        user_id
    ))

    add_transaction(
        user_id,
        amount,
        "wallet",
        description
    )


def get_plan(plan_id):
    return execute(
        "SELECT * FROM plans WHERE id=?",
        (plan_id,),
        fetchone=True
    )


def get_active_plans():
    return execute("""
        SELECT *
        FROM plans
        WHERE active=1
        ORDER BY sort_order,id
    """, fetchall=True)


# ============================================================
# PASARGUARD ADAPTER
# ============================================================

class PasarGuardClient:
    """
    این بخش عمداً API جعلی ندارد.

    برای ساخت واقعی سرویس باید API واقعی PasarGuard
    نصب‌شده روی سرور شما مشخص باشد.

    وقتی endpoint واقعی را داشته باشیم فقط همین کلاس
    به API واقعی وصل می‌شود و بقیه bot.py دست نمی‌خورد.
    """

    def __init__(self, url="", username="", password=""):
        self.url = (url or "").rstrip("/")
        self.username = username
        self.password = password

    def create_service(
        self,
        telegram_id,
        volume_gb,
        duration_days,
        devices,
        panel_id=0
    ):
        raise RuntimeError(
            "PasarGuard API is not configured."
        )

    def get_service(self, service_id):
        raise RuntimeError(
            "PasarGuard API is not configured."
        )

    def renew_service(self, service_id, days):
        raise RuntimeError(
            "PasarGuard API is not configured."
        )


PASARGUARD = PasarGuardClient(
    os.getenv("PASARGUARD_URL", ""),
    os.getenv("PASARGUARD_USERNAME", ""),
    os.getenv("PASARGUARD_PASSWORD", "")
)


# ============================================================
# KEYBOARDS
# ============================================================

def user_menu():
    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2
    )

    kb.add(
        types.KeyboardButton("🛒 خرید VPN"),
        types.KeyboardButton("🛡 سرویس‌های من")
    )

    kb.add(
        types.KeyboardButton("🎁 تست رایگان"),
        types.KeyboardButton("💰 کیف پول")
    )

    kb.add(
        types.KeyboardButton("📜 تراکنش‌های من"),
        types.KeyboardButton("🤝 پنل نمایندگی")
    )

    kb.add(
        types.KeyboardButton("🎫 خرید لایسنس ربات"),
        types.KeyboardButton("🆘 پشتیبانی")
    )

    kb.add(
        types.KeyboardButton("📚 راهنما"),
        types.KeyboardButton("⚙️ حساب کاربری")
    )

    return kb


def back_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="user_home"
        )
    )
    return kb


def admin_menu():
    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2
    )

    kb.add(
        types.KeyboardButton("📊 داشبورد"),
        types.KeyboardButton("👥 کاربران")
    )

    kb.add(
        types.KeyboardButton("🖥 پنل‌ها"),
        types.KeyboardButton("💎 پلن‌های VPN")
    )

    kb.add(
        types.KeyboardButton("📦 سرویس‌ها"),
        types.KeyboardButton("🤝 نمایندگان")
    )

    kb.add(
        types.KeyboardButton("💰 پرداخت‌ها"),
        types.KeyboardButton("💳 تنظیمات پرداخت")
    )

    kb.add(
        types.KeyboardButton("🎁 تنظیمات تست"),
        types.KeyboardButton("📢 عضویت اجباری")
    )

    kb.add(
        types.KeyboardButton("📢 ارسال همگانی"),
        types.KeyboardButton("🎫 تیکت‌ها")
    )

    kb.add(
        types.KeyboardButton("👑 مدیران"),
        types.KeyboardButton("💾 Backup")
    )

    kb.add(
        types.KeyboardButton("📈 گزارش‌ها"),
        types.KeyboardButton("🛡 امنیت")
    )

    kb.add(
        types.KeyboardButton("⚙️ تنظیمات"),
        types.KeyboardButton("🔧 وضعیت سیستم")
    )

    kb.add(
        types.KeyboardButton("🏠 منوی کاربر")
    )

    return kb


def plans_keyboard():
    kb = types.InlineKeyboardMarkup()

    for plan in get_active_plans():
        kb.add(
            types.InlineKeyboardButton(
                f"💎 {plan['name']} | {money(plan['price'])}",
                callback_data=f"buyplan:{plan['id']}"
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="user_home"
        )
    )

    return kb


# ============================================================
# FORCE JOIN
# ============================================================

def check_membership(user_id):
    if not FORCE_JOIN_ENABLED:
        return True

    if not FORCE_JOIN_CHANNEL:
        return True

    try:
        member = bot.get_chat_member(
            FORCE_JOIN_CHANNEL,
            user_id
        )

        return member.status in (
            "member",
            "administrator",
            "creator"
        )

    except Exception:
        return False


def force_join_message(chat_id):
    kb = types.InlineKeyboardMarkup()

    if FORCE_JOIN_CHANNEL_URL:
        kb.add(
            types.InlineKeyboardButton(
                "📢 عضویت در کانال",
                url=FORCE_JOIN_CHANNEL_URL
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            "✅ بررسی عضویت",
            callback_data="check_join"
        )
    )

    bot.send_message(
        chat_id,
        "🔒 برای استفاده از ربات ابتدا باید در کانال ما عضو شوید.",
        reply_markup=kb
    )


# ============================================================
# START
# ============================================================

@bot.message_handler(commands=["start"])
def start(message):
    ensure_user(message.from_user)

    if is_blocked(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "🚫 حساب شما مسدود شده است."
        )
        return

    if not check_membership(message.from_user.id):
        force_join_message(message.chat.id)
        return

    bot.send_message(
        message.chat.id,
        "🔥 <b>به VirangarVPN خوش آمدید</b>\n\n"
        "🚀 سرویس موردنظرتان را انتخاب کنید.",
        reply_markup=user_menu()
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "check_join"
)
def check_join(call):
    if check_membership(call.from_user.id):
        bot.answer_callback_query(
            call.id,
            "✅ عضویت شما تأیید شد."
        )

        bot.send_message(
            call.message.chat.id,
            "🔥 خوش آمدید!",
            reply_markup=user_menu()
        )

    else:
        bot.answer_callback_query(
            call.id,
            "❌ هنوز عضو کانال نشده‌اید.",
            show_alert=True
        )


# ============================================================
# USER HOME
# ============================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "user_home"
)
def user_home(call):
    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "🏠 <b>منوی اصلی</b>",
        reply_markup=user_menu()
    )


@bot.message_handler(
    func=lambda m: m.text == "🏠 منوی کاربر"
)
def user_home_text(message):
    bot.send_message(
        message.chat.id,
        "🏠 <b>منوی اصلی کاربر</b>",
        reply_markup=user_menu()
    )


# ============================================================
# BUY VPN
# ============================================================

@bot.message_handler(
    func=lambda m: m.text == "🛒 خرید VPN"
)
def buy_vpn(message):
    plans = get_active_plans()

    if not plans:
        bot.send_message(
            message.chat.id,
            "❌ فعلاً پلنی برای فروش وجود ندارد."
        )
        return

    bot.send_message(
        message.chat.id,
        "🛒 <b>انتخاب پلن VPN</b>\n\n"
        "پلن موردنظر را انتخاب کنید:",
        reply_markup=plans_keyboard()
    )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("buyplan:")
)
def buy_plan(call):
    plan_id = int(call.data.split(":")[1])
    plan = get_plan(plan_id)

    if not plan or not plan["active"]:
        bot.answer_callback_query(
            call.id,
            "❌ این پلن موجود نیست.",
            show_alert=True
        )
        return

    text = (
        f"💎 <b>{plan['name']}</b>\n\n"
        f"📦 حجم: {plan['volume_gb']}GB\n"
        f"⏳ مدت: {plan['duration_days']} روز\n"
        f"📱 دستگاه: {plan['devices']}\n"
        f"🌍 لوکیشن: {plan['location'] or 'پیش‌فرض'}\n"
        f"💰 قیمت: {money(plan['price'])}\n"
    )

    kb = types.InlineKeyboardMarkup()

    if PAYMENT_MODE in ("manual", "both"):
        kb.add(
            types.InlineKeyboardButton(
                "💳 کارت به کارت",
                callback_data=f"paymanual:{plan_id}"
            )
        )

    if PAYMENT_MODE in ("online", "both"):
        kb.add(
            types.InlineKeyboardButton(
                "🌐 پرداخت آنلاین",
                callback_data=f"payonline:{plan_id}"
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="user_home"
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

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("paymanual:")
)
def manual_payment(call):
    plan_id = int(call.data.split(":")[1])
    plan = get_plan(plan_id)

    if not plan:
        return

    payment = execute("""
        INSERT INTO payments
        (user_id, plan_id, amount, method, status, created_at)
        VALUES (?, ?, ?, 'manual', 'waiting_receipt', ?)
    """, (
        call.from_user.id,
        plan_id,
        plan["price"],
        now()
    ))

    payment_id = payment.lastrowid if payment else None

    text = (
        "💳 <b>پرداخت کارت به کارت</b>\n\n"
        f"💰 مبلغ: <b>{money(plan['price'])}</b>\n\n"
        f"🏦 شماره کارت:\n"
        f"<code>{CARD_NUMBER or 'تنظیم نشده'}</code>\n\n"
        f"👤 به نام:\n"
        f"<b>{CARD_HOLDER or 'تنظیم نشده'}</b>\n\n"
        "بعد از انتقال وجه، "
        "عکس رسید پرداخت را همینجا ارسال کنید."
    )

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=back_keyboard()
    )

    bot.answer_callback_query(call.id)


# ============================================================
# ONLINE PAYMENT
# ============================================================

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("payonline:")
)
def online_payment(call):
    plan_id = int(call.data.split(":")[1])
    plan = get_plan(plan_id)

    if not plan:
        return

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "🌐 <b>پرداخت آنلاین</b>\n\n"
        "درگاه آنلاین هنوز به API واقعی متصل نشده است.\n\n"
        "برای فعال‌سازی پرداخت آنلاین باید مشخصات API "
        "درگاه موردنظر وارد شود."
    )


# ============================================================
# RECEIPT
# ============================================================

@bot.message_handler(
    content_types=["photo"]
)
def receipt_photo(message):
    user = get_user(message.from_user.id)

    if not user:
        ensure_user(message.from_user)

    payment = execute("""
        SELECT *
        FROM payments
        WHERE user_id=?
        AND method='manual'
        AND status='waiting_receipt'
        ORDER BY id DESC
        LIMIT 1
    """, (
        message.from_user.id,
    ), fetchone=True)

    if not payment:
        bot.send_message(
            message.chat.id,
            "❌ پرداخت در انتظار رسیدی برای شما پیدا نشد."
        )
        return

    file_id = message.photo[-1].file_id

    execute("""
        UPDATE payments
        SET receipt_file_id=?,
            status='pending'
        WHERE id=?
    """, (
        file_id,
        payment["id"]
    ))

    bot.send_message(
        message.chat.id,
        "✅ رسید شما دریافت شد.\n\n"
        "⏳ پس از بررسی ادمین، نتیجه برای شما ارسال می‌شود."
    )

    if SUPER_ADMIN_ID:
        kb = types.InlineKeyboardMarkup()

        kb.add(
            types.InlineKeyboardButton(
                "✅ تأیید",
                callback_data=f"approve:{payment['id']}"
            ),
            types.InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject:{payment['id']}"
            )
        )

        bot.send_photo(
            SUPER_ADMIN_ID,
            file_id,
            caption=(
                "💳 <b>رسید پرداخت جدید</b>\n\n"
                f"🆔 پرداخت: <code>{payment['id']}</code>\n"
                f"👤 کاربر: <code>{message.from_user.id}</code>\n"
                f"💰 مبلغ: {money(payment['amount'])}\n"
                f"📦 Plan ID: {payment['plan_id']}"
            ),
            reply_markup=kb
        )


# ============================================================
# PAYMENT APPROVE / REJECT
# ============================================================

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("approve:")
)
def approve_payment(call):
    if not is_admin(call.from_user.id):
        return

    payment_id = int(call.data.split(":")[1])

    payment = execute(
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

    execute("""
        UPDATE payments
        SET status='approved',
            processed_at=?
        WHERE id=?
    """, (
        now(),
        payment_id
    ))

    plan = get_plan(payment["plan_id"])

    if not plan:
        bot.send_message(
            SUPER_ADMIN_ID,
            "⚠️ پرداخت تأیید شد ولی پلن پیدا نشد."
        )
        return

    # Try PasarGuard
    try:
        service = PASARGUARD.create_service(
            payment["user_id"],
            plan["volume_gb"],
            plan["duration_days"],
            plan["devices"],
            plan["panel_id"]
        )

        config = service.get("config", "")

    except Exception as e:
        # Payment remains approved but service isn't silently fabricated.
        logging.error("PasarGuard error: %s", e)

        expires = (
            datetime.utcnow()
            + timedelta(days=plan["duration_days"])
        ).strftime("%Y-%m-%d")

        execute("""
            INSERT INTO services
            (user_id, plan_id, volume_gb, duration_days,
             devices, expires_at, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending_creation', ?)
        """, (
            payment["user_id"],
            plan["id"],
            plan["volume_gb"],
            plan["duration_days"],
            plan["devices"],
            expires,
            now()
        ))

        bot.send_message(
            SUPER_ADMIN_ID,
            "✅ پرداخت تأیید شد.\n"
            "⚠️ اما ساخت سرویس انجام نشد چون API واقعی PasarGuard "
            "هنوز تنظیم نشده است."
        )

        bot.send_message(
            payment["user_id"],
            "✅ پرداخت شما تأیید شد.\n\n"
            "⚠️ سرویس در صف ساخت قرار گرفت و پس از اتصال "
            "PasarGuard ساخته می‌شود."
        )

        bot.answer_callback_query(call.id)
        return

    expires = (
        datetime.utcnow()
        + timedelta(days=plan["duration_days"])
    ).strftime("%Y-%m-%d")

    execute("""
        INSERT INTO services
        (user_id, plan_id, panel_id, config,
         volume_gb, duration_days, devices,
         expires_at, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
    """, (
        payment["user_id"],
        plan["id"],
        plan["panel_id"],
        config,
        plan["volume_gb"],
        plan["duration_days"],
        plan["devices"],
        expires,
        now()
    ))

    add_transaction(
        payment["user_id"],
        -payment["amount"],
        "purchase",
        f"خرید {plan['name']}"
    )

    bot.send_message(
        payment["user_id"],
        "🎉 <b>پرداخت تأیید شد!</b>\n\n"
        f"💎 پلن: {plan['name']}\n"
        f"📦 حجم: {plan['volume_gb']}GB\n"
        f"⏳ مدت: {plan['duration_days']} روز\n\n"
        f"🔐 کانفیگ:\n<code>{config}</code>"
    )

    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=None
    )

    bot.answer_callback_query(
        call.id,
        "✅ پرداخت تأیید شد."
    )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("reject:")
)
def reject_payment(call):
    if not is_admin(call.from_user.id):
        return

    payment_id = int(call.data.split(":")[1])

    payment = execute(
        "SELECT * FROM payments WHERE id=?",
        (payment_id,),
        fetchone=True
    )

    if not payment:
        return

    execute("""
        UPDATE payments
        SET status='rejected',
            processed_at=?
        WHERE id=?
    """, (
        now(),
        payment_id
    ))

    bot.send_message(
        payment["user_id"],
        "❌ <b>پرداخت شما رد شد.</b>\n\n"
        "در صورت اشتباه، با پشتیبانی تماس بگیرید."
    )

    bot.answer_callback_query(
        call.id,
        "❌ پرداخت رد شد."
    )


# ============================================================
# MY SERVICES
# ============================================================

@bot.message_handler(
    func=lambda m: m.text == "🛡 سرویس‌های من"
)
def my_services(message):
    services = execute("""
        SELECT *
        FROM services
        WHERE user_id=?
        ORDER BY id DESC
    """, (
        message.from_user.id,
    ), fetchall=True)

    if not services:
        bot.send_message(
            message.chat.id,
            "🛡 <b>سرویس‌های من</b>\n\n"
            "هنوز سرویسی ندارید."
        )
        return

    for service in services:
        text = (
            f"🛡 <b>سرویس #{service['id']}</b>\n\n"
            f"📦 حجم: {service['volume_gb']}GB\n"
            f"📊 مصرف: {service['used_gb']}GB\n"
            f"📱 دستگاه: {service['devices']}\n"
            f"⏳ انقضا: {service['expires_at']}\n"
            f"📌 وضعیت: {service['status']}"
        )

        kb = types.InlineKeyboardMarkup()

        kb.add(
            types.InlineKeyboardButton(
                "🔐 کانفیگ",
                callback_data=f"config:{service['id']}"
            ),
            types.InlineKeyboardButton(
                "🔄 تمدید",
                callback_data=f"renew:{service['id']}"
            )
        )

        kb.add(
            types.InlineKeyboardButton(
                "➕ افزایش حجم",
                callback_data=f"volume:{service['id']}"
            )
        )

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=kb
        )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("config:")
)
def service_config(call):
    service_id = int(call.data.split(":")[1])

    service = execute("""
        SELECT *
        FROM services
        WHERE id=? AND user_id=?
    """, (
        service_id,
        call.from_user.id
    ), fetchone=True)

    if not service:
        bot.answer_callback_query(
            call.id,
            "❌ سرویس پیدا نشد.",
            show_alert=True
        )
        return

    config = service["config"]

    if not config:
        bot.answer_callback_query(
            call.id,
            "⚠️ کانفیگ هنوز آماده نیست.",
            show_alert=True
        )
        return

    bot.send_message(
        call.message.chat.id,
        f"🔐 <b>کانفیگ سرویس #{service_id}</b>\n\n"
        f"<code>{config}</code>"
    )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("renew:")
)
def renew_service(call):
    service_id = int(call.data.split(":")[1])

    service = execute("""
        SELECT *
        FROM services
        WHERE id=? AND user_id=?
    """, (
        service_id,
        call.from_user.id
    ), fetchone=True)

    if not service:
        return

    bot.send_message(
        call.message.chat.id,
        "🔄 برای تمدید، ابتدا یکی از پلن‌های خرید را انتخاب کنید."
    )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("volume:")
)
def increase_volume(call):
    bot.answer_callback_query(
        call.id,
        "➕ انتخاب افزایش حجم به‌زودی از همین بخش انجام می‌شود.",
        show_alert=True
    )


# ============================================================
# FREE TRIAL
# ============================================================

@bot.message_handler(
    func=lambda m: m.text == "🎁 تست رایگان"
)
def free_trial(message):
    user = get_user(message.from_user.id)

    if user["trial_used"]:
        bot.send_message(
            message.chat.id,
            "❌ شما قبلاً تست رایگان خود را دریافت کرده‌اید."
        )
        return

    volume = int(get_setting("trial_volume", "5"))
    days = int(get_setting("trial_days", "2"))
    devices = int(get_setting("trial_devices", "1"))

    expires = (
        datetime.utcnow()
        + timedelta(days=days)
    ).strftime("%Y-%m-%d")

    try:
        service = PASARGUARD.create_service(
            message.from_user.id,
            volume,
            days,
            devices
        )

        config = service.get("config", "")

        execute("""
            INSERT INTO services
            (user_id, volume_gb, duration_days, devices,
             config, expires_at, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
        """, (
            message.from_user.id,
            volume,
            days,
            devices,
            config,
            expires,
            now()
        ))

        execute("""
            UPDATE users
            SET trial_used=1
            WHERE telegram_id=?
        """, (
            message.from_user.id,
        ))

        bot.send_message(
            message.chat.id,
            "🎁 <b>تست رایگان شما فعال شد!</b>\n\n"
            f"📦 حجم: {volume}GB\n"
            f"⏳ مدت: {days} روز\n"
            f"📱 دستگاه: {devices}\n\n"
            f"🔐 <code>{config}</code>"
        )

    except Exception as e:
        logging.error("Trial error: %s", e)

        bot.send_message(
            message.chat.id,
            "⚠️ تست رایگان تعریف شده، اما اتصال PasarGuard "
            "هنوز آماده نیست."
        )


# ============================================================
# WALLET
# ============================================================

@bot.message_handler(
    func=lambda m: m.text == "💰 کیف پول"
)
def wallet(message):
    user = get_user(message.from_user.id)

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "💳 شارژ حساب",
            callback_data="wallet_charge"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📜 تاریخچه کیف پول",
            callback_data="wallet_history"
        )
    )

    bot.send_message(
        message.chat.id,
        f"💰 <b>کیف پول</b>\n\n"
        f"موجودی فعلی:\n"
        f"💵 <b>{money(user['balance'])}</b>",
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "wallet_charge"
)
def wallet_charge(call):
    bot.send_message(
        call.message.chat.id,
        "💳 مبلغ موردنظر برای شارژ را به صورت عددی ارسال کنید.\n\n"
        "مثال:\n"
        "<code>200000</code>"
    )

    bot.register_next_step_handler(
        call.message,
        process_wallet_amount
    )

    bot.answer_callback_query(call.id)


def process_wallet_amount(message):
    try:
        amount = int(message.text.replace(",", "").strip())

        if amount < 10000:
            raise ValueError

    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ مبلغ نامعتبر است."
        )
        return

    payment = execute("""
        INSERT INTO payments
        (user_id, amount, method, status, created_at)
        VALUES (?, ?, 'wallet_manual', 'waiting_receipt', ?)
    """, (
        message.from_user.id,
        amount,
        now()
    ))

    bot.send_message(
        message.chat.id,
        "💳 <b>شارژ کیف پول</b>\n\n"
        f"💰 مبلغ: {money(amount)}\n\n"
        f"🏦 شماره کارت:\n"
        f"<code>{CARD_NUMBER or 'تنظیم نشده'}</code>\n\n"
        f"👤 به نام:\n"
        f"<b>{CARD_HOLDER or 'تنظیم نشده'}</b>\n\n"
        "بعد از پرداخت، عکس رسید را ارسال کنید."
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "wallet_history"
)
def wallet_history(call):
    rows = execute("""
        SELECT *
        FROM transactions
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 20
    """, (
        call.from_user.id,
    ), fetchall=True)

    if not rows:
        text = "📜 هنوز تراکنشی ندارید."
    else:
        lines = ["📜 <b>تاریخچه کیف پول</b>\n"]

        for row in rows:
            sign = "+" if row["amount"] >= 0 else ""

            lines.append(
                f"{sign}{money(row['amount'])} | "
                f"{row['description']}\n"
                f"🕐 {row['created_at']}"
            )

        text = "\n\n".join(lines)

    bot.send_message(
        call.message.chat.id,
        text
    )

    bot.answer_callback_query(call.id)


# ============================================================
# TRANSACTIONS
# ============================================================

@bot.message_handler(
    func=lambda m: m.text == "📜 تراکنش‌های من"
)
def transactions(message):
    rows = execute("""
        SELECT *
        FROM transactions
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 30
    """, (
        message.from_user.id,
    ), fetchall=True)

    if not rows:
        bot.send_message(
            message.chat.id,
            "📜 هنوز تراکنشی ثبت نشده."
        )
        return

    lines = ["📜 <b>تراکنش‌های من</b>\n"]

    for row in rows:
        sign = "+" if row["amount"] >= 0 else ""

        lines.append(
            f"#{row['id']} | {sign}{money(row['amount'])}\n"
            f"📌 {row['description']}\n"
            f"🕐 {row['created_at']}"
        )

    bot.send_message(
        message.chat.id,
        "\n\n".join(lines)
    )


# ============================================================
# RESELLER
# ============================================================

@bot.message_handler(
    func=lambda m: m.text == "🤝 پنل نمایندگی"
)
def reseller_panel(message):
    user = get_user(message.from_user.id)

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🛒 خرید پنل نمایندگی",
            callback_data="reseller_buy"
        )
    )

    if user["is_reseller"]:
        kb.add(
            types.InlineKeyboardButton(
                "👥 کاربران من",
                callback_data="reseller_users"
            )
        )

        kb.add(
            types.InlineKeyboardButton(
                "📦 سرویس‌های من",
                callback_data="reseller_services"
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
        "مدیریت کاربران و فروش سرویس‌ها از این بخش انجام می‌شود.",
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "reseller_buy"
)
def reseller_buy(call):
    plans = execute("""
        SELECT *
        FROM reseller_plans
        WHERE active=1
        ORDER BY id
    """, fetchall=True)

    kb = types.InlineKeyboardMarkup()

    for plan in plans:
        kb.add(
            types.InlineKeyboardButton(
                f"🤝 {plan['name']} | {money(plan['price'])}",
                callback_data=f"resplan:{plan['id']}"
            )
        )

    bot.send_message(
        call.message.chat.id,
        "🤝 <b>پلن نمایندگی</b>",
        reply_markup=kb
    )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("resplan:")
)
def reseller_plan(call):
    plan_id = int(call.data.split(":")[1])

    plan = execute(
        "SELECT * FROM reseller_plans WHERE id=?",
        (plan_id,),
        fetchone=True
    )

    if not plan:
        return

    bot.send_message(
        call.message.chat.id,
        f"🤝 <b>{plan['name']}</b>\n\n"
        f"📦 ظرفیت: {plan['capacity_gb']}GB\n"
        f"⏳ مدت: {plan['duration_days']} روز\n"
        f"💰 قیمت: {money(plan['price'])}\n\n"
        "برای خرید، پرداخت دستی فعلاً فعال است."
    )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(
    func=lambda c: c.data == "reseller_users"
)
def reseller_users(call):
    users = execute("""
        SELECT *
        FROM users
        WHERE id IN (
            SELECT DISTINCT user_id
            FROM services
            WHERE user_id != ?
        )
        LIMIT 50
    """, (
        call.from_user.id,
    ), fetchall=True)

    bot.send_message(
        call.message.chat.id,
        f"👥 تعداد کاربران: {len(users)}"
    )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(
    func=lambda c: c.data == "reseller_services"
)
def reseller_services(call):
    rows = execute("""
        SELECT *
        FROM services
        WHERE user_id=?
        ORDER BY id DESC
    """, (
        call.from_user.id,
    ), fetchall=True)

    bot.send_message(
        call.message.chat.id,
        f"📦 تعداد سرویس‌های شما: {len(rows)}"
    )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(
    func=lambda c: c.data == "reseller_stats"
)
def reseller_stats(call):
    count = execute("""
        SELECT COUNT(*) AS c
        FROM services
        WHERE user_id=?
    """, (
        call.from_user.id,
    ), fetchone=True)["c"]

    bot.send_message(
        call.message.chat.id,
        f"📈 <b>آمار فروش</b>\n\n"
        f"📦 تعداد سرویس‌ها: {count}"
    )

    bot.answer_callback_query(call.id)


# ============================================================
# LICENSE
# ============================================================

@bot.message_handler(
    func=lambda m: m.text == "🎫 خرید لایسنس ربات"
)
def licenses(message):
    price = int(
        get_setting(
            "license_price",
            "500000"
        )
    )

    days = int(
        get_setting(
            "license_days",
            "30"
        )
    )

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            f"🎫 خرید | {money(price)}",
            callback_data="license_buy"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🔑 لایسنس‌های من",
            callback_data="my_licenses"
        )
    )

    bot.send_message(
        message.chat.id,
        f"🎫 <b>لایسنس ربات</b>\n\n"
        f"⏳ مدت: {days} روز\n"
        f"💰 قیمت: {money(price)}",
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "license_buy"
)
def license_buy(call):
    price = int(get_setting("license_price", "500000"))
    days = int(get_setting("license_days", "30"))

    key = (
        "VIR-"
        + uuid.uuid4().hex[:8].upper()
        + "-"
        + uuid.uuid4().hex[:8].upper()
    )

    expires = (
        datetime.utcnow()
        + timedelta(days=days)
    ).strftime("%Y-%m-%d")

    execute("""
        INSERT INTO licenses
        (user_id, name, price, license_key,
         expires_at, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (
        call.from_user.id,
        "VirangarVPN License",
        price,
        key,
        expires,
        now()
    ))

    bot.send_message(
        call.message.chat.id,
        "🎫 درخواست خرید لایسنس ثبت شد.\n\n"
        "⏳ پس از تأیید پرداخت، لایسنس فعال می‌شود."
    )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(
    func=lambda c: c.data == "my_licenses"
)
def my_licenses(call):
    rows = execute("""
        SELECT *
        FROM licenses
        WHERE user_id=?
        ORDER BY id DESC
    """, (
        call.from_user.id,
    ), fetchall=True)

    if not rows:
        bot.send_message(
            call.message.chat.id,
            "🔑 لایسنسی ندارید."
        )
        return

    lines = ["🔑 <b>لایسنس‌های من</b>\n"]

    for row in rows:
        lines.append(
            f"🎫 {row['name']}\n"
            f"🔑 <code>{row['license_key']}</code>\n"
            f"⏳ {row['expires_at']}\n"
            f"📌 {row['status']}"
        )

    bot.send_message(
        call.message.chat.id,
        "\n\n".join(lines)
    )

    bot.answer_callback_query(call.id)


# ============================================================
# SUPPORT
# ============================================================

@bot.message_handler(
    func=lambda m: m.text == "🆘 پشتیبانی"
)
def support(message):
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🎫 ایجاد تیکت",
            callback_data="ticket_new"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📂 تیکت‌های من",
            callback_data="ticket_list"
        )
    )

    if SUPPORT_USERNAME:
        username = SUPPORT_USERNAME.replace("@", "")

        kb.add(
            types.InlineKeyboardButton(
                "💬 ارتباط مستقیم",
                url=f"https://t.me/{username}"
            )
        )

    bot.send_message(
        message.chat.id,
        "🆘 <b>مرکز پشتیبانی</b>",
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "ticket_new"
)
def ticket_new(call):
    bot.send_message(
        call.message.chat.id,
        "🎫 موضوع یا متن مشکل خود را ارسال کنید:"
    )

    bot.register_next_step_handler(
        call.message,
        create_ticket
    )

    bot.answer_callback_query(call.id)


def create_ticket(message):
    execute("""
        INSERT INTO tickets
        (user_id, subject, status, created_at)
        VALUES (?, ?, 'open', ?)
    """, (
        message.from_user.id,
        message.text or "پشتیبانی",
        now()
    ))

    ticket = execute(
        "SELECT last_insert_rowid() AS id",
        fetchone=True
    )

    ticket_id = ticket["id"]

    execute("""
        INSERT INTO ticket_messages
        (ticket_id, sender_id, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        ticket_id,
        message.from_user.id,
        message.text or "",
        now()
    ))

    bot.send_message(
        message.chat.id,
        f"✅ تیکت شما با شماره <b>#{ticket_id}</b> ثبت شد.\n\n"
        "پشتیبانی پس از بررسی پاسخ خواهد داد."
    )

    if SUPER_ADMIN_ID:
        bot.send_message(
            SUPER_ADMIN_ID,
            f"🎫 <b>تیکت جدید #{ticket_id}</b>\n\n"
            f"👤 کاربر: <code>{message.from_user.id}</code>\n\n"
            f"{message.text or ''}"
        )


@bot.callback_query_handler(
    func=lambda c: c.data == "ticket_list"
)
def ticket_list(call):
    rows = execute("""
        SELECT *
        FROM tickets
        WHERE user_id=?
        ORDER BY id DESC
    """, (
        call.from_user.id,
    ), fetchall=True)

    if not rows:
        bot.send_message(
            call.message.chat.id,
            "🎫 تیکتی ندارید."
        )
        return

    lines = ["🎫 <b>تیکت‌های من</b>\n"]

    for row in rows:
        lines.append(
            f"#{row['id']} | {row['subject']}\n"
            f"📌 وضعیت: {row['status']}"
        )

    bot.send_message(
        call.message.chat.id,
        "\n\n".join(lines)
    )

    bot.answer_callback_query(call.id)


# ============================================================
# GUIDE
# ============================================================

@bot.message_handler(
    func=lambda m: m.text == "📚 راهنما"
)
def guide(message):
    bot.send_message(
        message.chat.id,
        "📚 <b>راهنمای VirangarVPN</b>\n\n"
        "🛒 از بخش خرید VPN پلن خود را انتخاب کنید.\n"
        "💳 پرداخت را انجام دهید.\n"
        "🛡 کانفیگ از بخش سرویس‌های من قابل دریافت است.\n"
        "🎁 هر کاربر طبق تنظیمات فقط یک تست رایگان دریافت می‌کند.\n"
        "🆘 در صورت مشکل از پشتیبانی استفاده کنید."
    )


# ============================================================
# ACCOUNT
# ============================================================

@bot.message_handler(
    func=lambda m: m.text == "⚙️ حساب کاربری"
)
def account(message):
    user = get_user(message.from_user.id)

    services = execute("""
        SELECT COUNT(*) AS c
        FROM services
        WHERE user_id=?
    """, (
        message.from_user.id,
    ), fetchone=True)["c"]

    bot.send_message(
        message.chat.id,
        "⚙️ <b>حساب کاربری</b>\n\n"
        f"🆔 Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"👤 نام: {user['first_name']}\n"
        f"🔹 Username: @{user['username'] or '-'}\n"
        f"💰 موجودی: {money(user['balance'])}\n"
        f"📦 سرویس‌ها: {services}\n"
        f"📅 عضویت: {user['created_at']}"
    )


# ============================================================
# ADMIN
# ============================================================

@bot.message_handler(
    commands=["admin"]
)
def admin_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(
            message,
            "⛔ دسترسی ندارید."
        )
        return

    bot.send_message(
        message.chat.id,
        "👑 <b>پنل سوپر ادمین</b>",
        reply_markup=admin_menu()
    )


@bot.message_handler(
    func=lambda m:
        m.text in [
            "📊 داشبورد",
            "👥 کاربران",
            "🖥 پنل‌ها",
            "💎 پلن‌های VPN",
            "📦 سرویس‌ها",
            "🤝 نمایندگان",
            "💰 پرداخت‌ها",
            "💳 تنظیمات پرداخت",
            "🎁 تنظیمات تست",
            "📢 عضویت اجباری",
            "📢 ارسال همگانی",
            "🎫 تیکت‌ها",
            "👑 مدیران",
            "💾 Backup",
            "📈 گزارش‌ها",
            "🛡 امنیت",
            "⚙️ تنظیمات",
            "🔧 وضعیت سیستم"
        ]
)
def admin_text_router(message):
    if not is_admin(message.from_user.id):
        return

    text = message.text

    if text == "📊 داشبورد":
        admin_dashboard(message)

    elif text == "👥 کاربران":
        admin_users(message)

    elif text == "🖥 پنل‌ها":
        admin_panels(message)

    elif text == "💎 پلن‌های VPN":
        admin_plans(message)

    elif text == "📦 سرویس‌ها":
        admin_services(message)

    elif text == "🤝 نمایندگان":
        admin_resellers(message)

    elif text == "💰 پرداخت‌ها":
        admin_payments(message)

    elif text == "💳 تنظیمات پرداخت":
        admin_payment_settings(message)

    elif text == "🎁 تنظیمات تست":
        admin_trial(message)

    elif text == "📢 عضویت اجباری":
        admin_force_join(message)

    elif text == "📢 ارسال همگانی":
        admin_broadcast(message)

    elif text == "🎫 تیکت‌ها":
        admin_tickets(message)

    elif text == "👑 مدیران":
        admin_admins(message)

    elif text == "💾 Backup":
        admin_backup(message)

    elif text == "📈 گزارش‌ها":
        admin_reports(message)

    elif text == "🛡 امنیت":
        admin_security(message)

    elif text == "⚙️ تنظیمات":
        admin_settings(message)

    elif text == "🔧 وضعیت سیستم":
        admin_system(message)


# ============================================================
# ADMIN DASHBOARD
# ============================================================

def admin_dashboard(message):
    users = execute(
        "SELECT COUNT(*) AS c FROM users",
        fetchone=True
    )["c"]

    active_users = execute("""
        SELECT COUNT(DISTINCT user_id) AS c
        FROM services
        WHERE status='active'
    """, fetchone=True)["c"]

    services = execute(
        "SELECT COUNT(*) AS c FROM services",
        fetchone=True
    )["c"]

    payments = execute("""
        SELECT COALESCE(SUM(amount),0) AS s
        FROM payments
        WHERE status='approved'
    """, fetchone=True)["s"]

    panels = execute(
        "SELECT COUNT(*) AS c FROM panels WHERE active=1",
        fetchone=True
    )["c"]

    bot.send_message(
        message.chat.id,
        "📊 <b>داشبورد</b>\n\n"
        f"👥 کاربران: {users}\n"
        f"🟢 کاربران دارای سرویس: {active_users}\n"
        f"📦 سرویس‌ها: {services}\n"
        f"💰 درآمد ثبت‌شده: {money(payments)}\n"
        f"🖥 پنل‌های فعال: {panels}"
    )


# ============================================================
# ADMIN USERS
# ============================================================

def admin_users(message):
    rows = execute("""
        SELECT *
        FROM users
        ORDER BY id DESC
        LIMIT 30
    """, fetchall=True)

    if not rows:
        bot.send_message(
            message.chat.id,
            "👥 کاربری وجود ندارد."
        )
        return

    lines = ["👥 <b>آخرین کاربران</b>\n"]

    for row in rows:
        status = "🚫" if row["is_blocked"] else "🟢"

        lines.append(
            f"{status} #{row['id']} | "
            f"<code>{row['telegram_id']}</code>\n"
            f"👤 {row['first_name'] or '-'} "
            f"@{row['username'] or '-'}\n"
            f"💰 {money(row['balance'])}"
        )

    bot.send_message(
        message.chat.id,
        "\n\n".join(lines)
    )

    bot.send_message(
        message.chat.id,
        "برای مدیریت یک کاربر، Telegram ID او را ارسال کنید:"
    )

    bot.register_next_step_handler(
        message,
        admin_user_manage
    )


def admin_user_manage(message):
    try:
        tg_id = int(message.text.strip())
    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ ID نامعتبر."
        )
        return

    user = get_user(tg_id)

    if not user:
        bot.send_message(
            message.chat.id,
            "❌ کاربر پیدا نشد."
        )
        return

    kb = types.InlineKeyboardMarkup()

    if user["is_blocked"]:
        kb.add(
            types.InlineKeyboardButton(
                "🟢 رفع مسدودی",
                callback_data=f"unblock:{tg_id}"
            )
        )
    else:
        kb.add(
            types.InlineKeyboardButton(
                "🚫 مسدود",
                callback_data=f"block:{tg_id}"
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            "💰 تغییر موجودی",
            callback_data=f"balance:{tg_id}"
        )
    )

    bot.send_message(
        message.chat.id,
        f"👤 <b>کاربر</b>\n\n"
        f"🆔 {tg_id}\n"
        f"👤 {user['first_name']}\n"
        f"💰 {money(user['balance'])}\n"
        f"📌 {'مسدود' if user['is_blocked'] else 'فعال'}",
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("block:")
)
def block_user(call):
    if not is_admin(call.from_user.id):
        return

    tg_id = int(call.data.split(":")[1])

    execute(
        "UPDATE users SET is_blocked=1 WHERE telegram_id=?",
        (tg_id,)
    )

    bot.answer_callback_query(
        call.id,
        "🚫 کاربر مسدود شد."
    )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("unblock:")
)
def unblock_user(call):
    if not is_admin(call.from_user.id):
        return

    tg_id = int(call.data.split(":")[1])

    execute(
        "UPDATE users SET is_blocked=0 WHERE telegram_id=?",
        (tg_id,)
    )

    bot.answer_callback_query(
        call.id,
        "🟢 کاربر آزاد شد."
    )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("balance:")
)
def admin_balance(call):
    if not is_admin(call.from_user.id):
        return

    tg_id = int(call.data.split(":")[1])

    bot.send_message(
        call.message.chat.id,
        "💰 مبلغ تغییر موجودی را ارسال کنید.\n\n"
        "مثال افزایش:\n"
        "<code>200000</code>\n\n"
        "مثال کاهش:\n"
        "<code>-100000</code>"
    )

    bot.register_next_step_handler(
        call.message,
        lambda m: process_admin_balance(m, tg_id)
    )

    bot.answer_callback_query(call.id)


def process_admin_balance(message, tg_id):
    try:
        amount = int(message.text.replace(",", "").strip())
    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ مبلغ نامعتبر."
        )
        return

    change_balance(
        tg_id,
        amount,
        "تغییر موجودی توسط ادمین"
    )

    bot.send_message(
        message.chat.id,
        "✅ موجودی تغییر کرد."
    )


# ============================================================
# ADMIN PLANS
# ============================================================

def admin_plans(message):
    plans = execute("""
        SELECT *
        FROM plans
        ORDER BY sort_order,id
    """, fetchall=True)

    lines = ["💎 <b>پلن‌های VPN</b>\n"]

    for plan in plans:
        lines.append(
            f"#{plan['id']} | {plan['name']}\n"
            f"💰 {money(plan['price'])}\n"
            f"📦 {plan['volume_gb']}GB | "
            f"⏳ {plan['duration_days']} روز | "
            f"📱 {plan['devices']}\n"
            f"📌 {'فعال' if plan['active'] else 'غیرفعال'}"
        )

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "➕ افزودن پلن",
            callback_data="admin_add_plan"
        )
    )

    bot.send_message(
        message.chat.id,
        "\n\n".join(lines),
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "admin_add_plan"
)
def admin_add_plan(call):
    bot.send_message(
        call.message.chat.id,
        "فرمت را دقیقاً این‌طور ارسال کنید:\n\n"
        "<code>نام | قیمت | حجم | روز | دستگاه | لوکیشن</code>\n\n"
        "مثال:\n"
        "<code>VIP 100GB | 250000 | 100 | 30 | 2 | Germany</code>"
    )

    bot.register_next_step_handler(
        call.message,
        save_plan
    )

    bot.answer_callback_query(call.id)


def save_plan(message):
    try:
        parts = [
            x.strip()
            for x in message.text.split("|")
        ]

        name = parts[0]
        price = int(parts[1])
        volume = int(parts[2])
        days = int(parts[3])
        devices = int(parts[4])
        location = parts[5]

        execute("""
            INSERT INTO plans
            (name, price, volume_gb, duration_days,
             devices, location, active, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, 1, 99)
        """, (
            name,
            price,
            volume,
            days,
            devices,
            location
        ))

        bot.send_message(
            message.chat.id,
            "✅ پلن با موفقیت اضافه شد."
        )

    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ فرمت اشتباه است."
        )


# ============================================================
# ADMIN PANELS
# ============================================================

def admin_panels(message):
    panels = execute("""
        SELECT *
        FROM panels
        ORDER BY id DESC
    """, fetchall=True)

    lines = ["🖥 <b>پنل‌های PasarGuard</b>\n"]

    if not panels:
        lines.append("هنوز پنلی ثبت نشده.")
    else:
        for panel in panels:
            lines.append(
                f"#{panel['id']} | {panel['name']}\n"
                f"🌐 {panel['url']}\n"
                f"📌 {'فعال' if panel['active'] else 'غیرفعال'}"
            )

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "➕ افزودن پنل",
            callback_data="admin_add_panel"
        )
    )

    bot.send_message(
        message.chat.id,
        "\n\n".join(lines),
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "admin_add_panel"
)
def admin_add_panel(call):
    bot.send_message(
        call.message.chat.id,
        "فرمت:\n\n"
        "<code>نام | URL | username | password</code>"
    )

    bot.register_next_step_handler(
        call.message,
        save_panel
    )

    bot.answer_callback_query(call.id)


def save_panel(message):
    try:
        parts = [
            x.strip()
            for x in message.text.split("|")
        ]

        execute("""
            INSERT INTO panels
            (name, url, username, password, active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
        """, (
            parts[0],
            parts[1],
            parts[2],
            parts[3],
            now()
        ))

        bot.send_message(
            message.chat.id,
            "✅ پنل اضافه شد."
        )

    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ فرمت اشتباه است."
        )


# ============================================================
# ADMIN SERVICES
# ============================================================

def admin_services(message):
    rows = execute("""
        SELECT *
        FROM services
        ORDER BY id DESC
        LIMIT 50
    """, fetchall=True)

    if not rows:
        bot.send_message(
            message.chat.id,
            "📦 سرویسی وجود ندارد."
        )
        return

    lines = ["📦 <b>آخرین سرویس‌ها</b>\n"]

    for row in rows:
        lines.append(
            f"#{row['id']} | user={row['user_id']}\n"
            f"📦 {row['volume_gb']}GB\n"
            f"⏳ {row['expires_at']}\n"
            f"📌 {row['status']}"
        )

    bot.send_message(
        message.chat.id,
        "\n\n".join(lines)
    )


# ============================================================
# ADMIN RESELLERS
# ============================================================

def admin_resellers(message):
    users = execute("""
        SELECT *
        FROM users
        WHERE is_reseller=1
        ORDER BY id DESC
    """, fetchall=True)

    if not users:
        bot.send_message(
            message.chat.id,
            "🤝 هنوز نماینده‌ای وجود ندارد."
        )
        return

    lines = ["🤝 <b>نمایندگان</b>\n"]

    for user in users:
        lines.append(
            f"👤 {user['telegram_id']}\n"
            f"💰 {money(user['balance'])}"
        )

    bot.send_message(
        message.chat.id,
        "\n\n".join(lines)
    )


# ============================================================
# ADMIN PAYMENTS
# ============================================================

def admin_payments(message):
    rows = execute("""
        SELECT *
        FROM payments
        ORDER BY id DESC
        LIMIT 50
    """, fetchall=True)

    if not rows:
        bot.send_message(
            message.chat.id,
            "💰 پرداختی وجود ندارد."
        )
        return

    lines = ["💰 <b>پرداخت‌ها</b>\n"]

    for row in rows:
        lines.append(
            f"#{row['id']} | "
            f"user={row['user_id']}\n"
            f"💰 {money(row['amount'])}\n"
            f"💳 {row['method']}\n"
            f"📌 {row['status']}"
        )

    bot.send_message(
        message.chat.id,
        "\n\n".join(lines)
    )


# ============================================================
# ADMIN PAYMENT SETTINGS
# ============================================================

def admin_payment_settings(message):
    mode = PAYMENT_MODE

    bot.send_message(
        message.chat.id,
        "💳 <b>تنظیمات پرداخت</b>\n\n"
        f"حالت فعلی: <code>{mode}</code>\n\n"
        f"💳 شماره کارت:\n"
        f"<code>{CARD_NUMBER or 'تنظیم نشده'}</code>\n\n"
        f"👤 صاحب کارت:\n"
        f"{CARD_HOLDER or 'تنظیم نشده'}\n\n"
        "برای تغییر تنظیمات باید مقدارهای .env تغییر کنند."
    )


# ============================================================
# ADMIN TRIAL
# ============================================================

def admin_trial(message):
    volume = get_setting("trial_volume", "5")
    days = get_setting("trial_days", "2")
    devices = get_setting("trial_devices", "1")

    bot.send_message(
        message.chat.id,
        "🎁 <b>تنظیمات تست رایگان</b>\n\n"
        f"📦 حجم: {volume}GB\n"
        f"⏳ مدت: {days} روز\n"
        f"📱 دستگاه: {devices}\n\n"
        "برای تغییر:\n"
        "<code>حجم | روز | دستگاه</code>\n\n"
        "مثال:\n"
        "<code>10 | 3 | 2</code>"
    )

    bot.register_next_step_handler(
        message,
        save_trial_settings
    )


def save_trial_settings(message):
    try:
        parts = [
            x.strip()
            for x in message.text.split("|")
        ]

        set_setting("trial_volume", parts[0])
        set_setting("trial_days", parts[1])
        set_setting("trial_devices", parts[2])

        bot.send_message(
            message.chat.id,
            "✅ تنظیمات تست ذخیره شد."
        )

    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ فرمت اشتباه."
        )


# ============================================================
# ADMIN FORCE JOIN
# ============================================================

def admin_force_join(message):
    bot.send_message(
        message.chat.id,
        "📢 <b>عضویت اجباری</b>\n\n"
        f"فعال: {FORCE_JOIN_ENABLED}\n"
        f"کانال: {FORCE_JOIN_CHANNEL or '-'}\n"
        f"لینک: {FORCE_JOIN_CHANNEL_URL or '-'}\n\n"
        "تغییر این موارد از .env انجام می‌شود."
    )


# ============================================================
# ADMIN BROADCAST
# ============================================================

def admin_broadcast(message):
    bot.send_message(
        message.chat.id,
        "📢 متن پیام همگانی را ارسال کنید:"
    )

    bot.register_next_step_handler(
        message,
        perform_broadcast
    )


def perform_broadcast(message):
    users = execute(
        "SELECT telegram_id FROM users WHERE is_blocked=0",
        fetchall=True
    )

    success = 0
    failed = 0

    for user in users:
        try:
            bot.send_message(
                user["telegram_id"],
                message.text
            )
            success += 1
        except Exception:
            failed += 1

    bot.send_message(
        message.chat.id,
        f"📢 ارسال تمام شد.\n\n"
        f"✅ موفق: {success}\n"
        f"❌ ناموفق: {failed}"
    )


# ============================================================
# ADMIN TICKETS
# ============================================================

def admin_tickets(message):
    rows = execute("""
        SELECT *
        FROM tickets
        ORDER BY id DESC
        LIMIT 50
    """, fetchall=True)

    if not rows:
        bot.send_message(
            message.chat.id,
            "🎫 تیکتی وجود ندارد."
        )
        return

    lines = ["🎫 <b>تیکت‌ها</b>\n"]

    for row in rows:
        lines.append(
            f"#{row['id']} | user={row['user_id']}\n"
            f"موضوع: {row['subject']}\n"
            f"وضعیت: {row['status']}"
        )

    bot.send_message(
        message.chat.id,
        "\n\n".join(lines)
    )


# ============================================================
# ADMIN MANAGEMENT
# ============================================================

def admin_admins(message):
    bot.send_message(
        message.chat.id,
        "👑 <b>مدیریت مدیران</b>\n\n"
        f"سوپر ادمین اصلی:\n"
        f"<code>{SUPER_ADMIN_ID}</code>\n\n"
        "مدیریت چندادمینی را می‌توان در مرحله بعد "
        "با جدول roles پیاده‌سازی کرد."
    )


# ============================================================
# BACKUP
# ============================================================

def admin_backup(message):
    try:
        backup_name = (
            "virangarvpn_backup_"
            + datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            + ".db"
        )

        source = sqlite3.connect(DB_FILE)
        backup = sqlite3.connect(backup_name)

        with backup:
            source.backup(backup)

        backup.close()
        source.close()

        with open(backup_name, "rb") as file:
            bot.send_document(
                message.chat.id,
                file,
                caption="💾 بکاپ دیتابیس"
            )

        os.remove(backup_name)

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ خطا در Backup:\n<code>{e}</code>"
        )


# ============================================================
# REPORTS
# ============================================================

def admin_reports(message):
    total_sales = execute("""
        SELECT COUNT(*) AS c
        FROM payments
        WHERE status='approved'
    """, fetchone=True)["c"]

    revenue = execute("""
        SELECT COALESCE(SUM(amount),0) AS s
        FROM payments
        WHERE status='approved'
    """, fetchone=True)["s"]

    users = execute(
        "SELECT COUNT(*) AS c FROM users",
        fetchone=True
    )["c"]

    services = execute(
        "SELECT COUNT(*) AS c FROM services",
        fetchone=True
    )["c"]

    bot.send_message(
        message.chat.id,
        "📈 <b>گزارش کلی</b>\n\n"
        f"👥 کاربران: {users}\n"
        f"📦 سرویس‌ها: {services}\n"
        f"💳 پرداخت موفق: {total_sales}\n"
        f"💰 درآمد: {money(revenue)}"
    )


# ============================================================
# SECURITY
# ============================================================

def admin_security(message):
    bot.send_message(
        message.chat.id,
        "🛡 <b>امنیت</b>\n\n"
        "• دسترسی پنل فقط برای SUPER_ADMIN_ID\n"
        "• کاربران مسدود امکان استفاده ندارند\n"
        "• پرداخت‌ها با وضعیت pending/approved/rejected ذخیره می‌شوند\n"
        "• رمز PasarGuard در .env قرار می‌گیرد."
    )


# ============================================================
# SETTINGS
# ============================================================

def admin_settings(message):
    bot.send_message(
        message.chat.id,
        "⚙️ <b>تنظیمات سیستم</b>\n\n"
        f"نام ربات: {get_setting('bot_name')}\n"
        f"Trial: {get_setting('trial_volume')}GB / "
        f"{get_setting('trial_days')} روز\n"
        f"License: {money(int(get_setting('license_price', '0')))}"
    )


# ============================================================
# SYSTEM STATUS
# ============================================================

def admin_system(message):
    try:
        db_status = "🟢 OK"

        if not os.path.exists(DB_FILE):
            db_status = "🔴 ERROR"

    except Exception:
        db_status = "🔴 ERROR"

    pg_status = (
        "🟢 تنظیم شده"
        if PASARGUARD.url
        else "🔴 تنظیم نشده"
    )

    bot.send_message(
        message.chat.id,
        "🔧 <b>وضعیت سیستم</b>\n\n"
        f"🤖 Bot: 🟢 Running\n"
        f"🗄 Database: {db_status}\n"
        f"🖥 PasarGuard: {pg_status}\n"
        f"💳 Payment: {PAYMENT_MODE}"
    )


# ============================================================
# UNKNOWN TEXT
# ============================================================

@bot.message_handler(
    func=lambda m: True
)
def fallback(message):
    ensure_user(message.from_user)

    if is_blocked(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "🚫 حساب شما مسدود است."
        )
        return

    if not check_membership(message.from_user.id):
        force_join_message(message.chat.id)
        return

    bot.send_message(
        message.chat.id,
        "از منوی زیر انتخاب کنید:",
        reply_markup=user_menu()
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    init_db()

    print("=" * 50)
    print("🔥 VirangarVPN Bot")
    print("🚀 Bot is running...")
    print("=" * 50)

    bot.infinity_polling(
        skip_pending=True,
        allowed_updates=[
            "message",
            "callback_query"
        ]
    )
