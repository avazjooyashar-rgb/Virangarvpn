cat > bot.py <<'PY'
import os
import sqlite3
import logging
from datetime import datetime

import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SUPERADMIN_ID = int(os.getenv("SUPERADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "virangarvpn.db")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN داخل .env تنظیم نشده")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# =========================
# DATABASE
# =========================

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()

    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance INTEGER DEFAULT 0,
        blocked INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        volume_gb INTEGER NOT NULL,
        duration_days INTEGER NOT NULL,
        devices INTEGER NOT NULL,
        price INTEGER NOT NULL,
        active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_id INTEGER,
        amount INTEGER NOT NULL,
        method TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        receipt_file_id TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_id INTEGER,
        status TEXT DEFAULT 'active',
        config TEXT,
        expires_at TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        kind TEXT NOT NULL,
        description TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    if con.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 0:
        con.executemany(
            """
            INSERT INTO plans
            (name, volume_gb, duration_days, devices, price)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("اقتصادی", 30, 30, 1, 120000),
                ("حرفه‌ای", 70, 60, 2, 220000),
                ("پریمیوم", 150, 90, 4, 350000),
            ]
        )

    defaults = {
        "manual_payment": "1",
        "online_payment": "0",
        "card_number": "شماره کارت تنظیم نشده",
        "card_name": "نام صاحب کارت تنظیم نشده",
    }

    for key, value in defaults.items():
        con.execute(
            """
            INSERT OR IGNORE INTO settings(key, value)
            VALUES (?, ?)
            """,
            (key, value)
        )

    con.commit()
    con.close()


# =========================
# SETTINGS
# =========================

def get_setting(key, default=""):
    con = db()

    row = con.execute(
        "SELECT value FROM settings WHERE key=?",
        (key,)
    ).fetchone()

    con.close()

    if row:
        return row["value"]

    return default


def set_setting(key, value):
    con = db()

    con.execute(
        """
        INSERT INTO settings(key, value)
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET value=excluded.value
        """,
        (key, value)
    )

    con.commit()
    con.close()


# =========================
# USER
# =========================

def save_user(user):
    con = db()

    con.execute(
        """
        INSERT INTO users
        (id, username, first_name, created_at)
        VALUES (?, ?, ?, ?)

        ON CONFLICT(id)
        DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name
        """,
        (
            user.id,
            user.username or "",
            user.first_name or "",
            datetime.utcnow().isoformat()
        )
    )

    con.commit()

    row = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user.id,)
    ).fetchone()

    con.close()

    return row


def is_blocked(user_id):
    con = db()

    row = con.execute(
        "SELECT blocked FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    con.close()

    return bool(row and row["blocked"])


# =========================
# KEYBOARDS
# =========================

def menu():
    markup = types.InlineKeyboardMarkup()

    markup.row(
        types.InlineKeyboardButton(
            "🛒 خرید VPN",
            callback_data="buy"
        ),
        types.InlineKeyboardButton(
            "🛡 سرویس‌های من",
            callback_data="services"
        )
    )

    markup.row(
        types.InlineKeyboardButton(
            "🎁 تست رایگان",
            callback_data="trial"
        ),
        types.InlineKeyboardButton(
            "💰 کیف پول",
            callback_data="wallet"
        )
    )

    markup.row(
        types.InlineKeyboardButton(
            "📜 تراکنش‌های من",
            callback_data="transactions"
        )
    )

    markup.row(
        types.InlineKeyboardButton(
            "🤝 پنل نمایندگی",
            callback_data="reseller"
        ),
        types.InlineKeyboardButton(
            "🎫 لایسنس ربات",
            callback_data="license"
        )
    )

    markup.row(
        types.InlineKeyboardButton(
            "🆘 پشتیبانی",
            callback_data="support"
        ),
        types.InlineKeyboardButton(
            "📚 راهنما",
            callback_data="guide"
        )
    )

    markup.row(
        types.InlineKeyboardButton(
            "⚙️ حساب کاربری",
            callback_data="account"
        )
    )

    return markup


def back_button():
    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "🏠 منوی اصلی",
            callback_data="home"
        )
    )

    return markup


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start(message):

    user = save_user(message.from_user)

    if user["blocked"]:
        bot.send_message(
            message.chat.id,
            "⛔ حساب شما مسدود است."
        )
        return

    bot.send_message(
        message.chat.id,
        """
🔥 <b>به VirangarVPN خوش آمدید</b>

⚡ سرویس سریع و پایدار خودت رو انتخاب کن.

👇 از منوی زیر شروع کن:
""",
        reply_markup=menu()
    )


# =========================
# CALLBACKS
# =========================

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):

    user_id = call.from_user.id
    data = call.data

    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    # HOME
    if data == "home":

        bot.edit_message_text(
            "🏠 <b>منوی اصلی</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=menu()
        )

        return

    # BUY
    if data == "buy":

        con = db()

        plans = con.execute(
            """
            SELECT *
            FROM plans
            WHERE active=1
            ORDER BY id
            """
        ).fetchall()

        con.close()

        markup = types.InlineKeyboardMarkup()

        for plan in plans:

            markup.add(
                types.InlineKeyboardButton(
                    f"💎 {plan['name']} | {plan['volume_gb']}GB | {plan['duration_days']} روز | {plan['price']:,}",
                    callback_data=f"plan:{plan['id']}"
                )
            )

        markup.add(
            types.InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="home"
            )
        )

        bot.edit_message_text(
            "🛒 <b>انتخاب پلن VPN</b>\n\nیکی از پلن‌ها را انتخاب کن:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

        return

    # PLAN
    if data.startswith("plan:"):

        plan_id = int(data.split(":")[1])

        con = db()

        plan = con.execute(
            "SELECT * FROM plans WHERE id=? AND active=1",
            (plan_id,)
        ).fetchone()

        con.close()

        if not plan:

            bot.answer_callback_query(
                call.id,
                "پلن پیدا نشد",
                show_alert=True
            )

            return

        text = f"""
💎 <b>{plan['name']}</b>

📦 حجم: {plan['volume_gb']} گیگ
⏳ مدت: {plan['duration_days']} روز
📱 دستگاه: {plan['devices']}
💰 قیمت: <b>{plan['price']:,} تومان</b>

روش پرداخت را انتخاب کن:
"""

        markup = types.InlineKeyboardMarkup()

        if get_setting("manual_payment") == "1":

            markup.add(
                types.InlineKeyboardButton(
                    "💳 کارت‌به‌کارت",
                    callback_data=f"manual:{plan_id}"
                )
            )

        if get_setting("online_payment") == "1":

            markup.add(
                types.InlineKeyboardButton(
                    "🌐 پرداخت آنلاین",
                    callback_data=f"online:{plan_id}"
                )
            )

        markup.add(
            types.InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="buy"
            )
        )

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

        return

    # MANUAL PAYMENT
    if data.startswith("manual:"):

        plan_id = int(data.split(":")[1])

        con = db()

        plan = con.execute(
            "SELECT * FROM plans WHERE id=?",
            (plan_id,)
        ).fetchone()

        con.close()

        if not plan:
            return

        text = f"""
💳 <b>پرداخت کارت‌به‌کارت</b>

💰 مبلغ:
<b>{plan['price']:,} تومان</b>

💳 شماره کارت:
<code>{get_setting('card_number')}</code>

👤 به نام:
<b>{get_setting('card_name')}</b>

بعد از انتقال وجه، <b>عکس رسید</b> را همینجا ارسال کن.
"""

        bot.send_message(
            call.message.chat.id,
            text
        )

        bot.register_next_step_handler_by_chat_id(
            call.message.chat.id,
            lambda message: receive_receipt(message, plan_id)
        )

        return

    # ONLINE
    if data.startswith("online:"):

        bot.send_message(
            call.message.chat.id,
            "🌐 درگاه آنلاین هنوز به API درگاه متصل نشده است."
        )

        return

    # SERVICES
    if data == "services":

        con = db()

        services = con.execute(
            """
            SELECT *
            FROM services
            WHERE user_id=?
            AND status='active'
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

        con.close()

        if not services:

            bot.edit_message_text(
                """
🛡 <b>سرویس‌های من</b>

❌ سرویس فعالی نداری.
""",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton(
                        "🛒 خرید VPN",
                        callback_data="buy"
                    ),
                    types.InlineKeyboardButton(
                        "🏠 خانه",
                        callback_data="home"
                    )
                )
            )

            return

        text = "🛡 <b>سرویس‌های من</b>\n\n"

        for service in services:

            text += f"""
🔹 <b>سرویس #{service['id']}</b>
📅 انقضا: {service['expires_at'] or '-'}
📡 وضعیت: فعال

"""

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # WALLET
    if data == "wallet":

        con = db()

        user = con.execute(
            "SELECT balance FROM users WHERE id=?",
            (user_id,)
        ).fetchone()

        con.close()

        balance = user["balance"] if user else 0

        bot.edit_message_text(
            f"""
💰 <b>کیف پول</b>

موجودی فعلی:

💵 <b>{balance:,} تومان</b>
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # TRANSACTIONS
    if data == "transactions":

        con = db()

        transactions = con.execute(
            """
            SELECT *
            FROM transactions
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT 20
            """,
            (user_id,)
        ).fetchall()

        con.close()

        text = "📜 <b>تراکنش‌های من</b>\n\n"

        if not transactions:

            text += "❌ تراکنشی ثبت نشده."

        else:

            for tx in transactions:

                text += f"""
#{tx['id']}
💰 {tx['amount']:,} تومان
📌 {tx['kind']}
📝 {tx['description'] or '-'}
━━━━━━━━━━━━
"""

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # TRIAL
    if data == "trial":

        bot.edit_message_text(
            """
🎁 <b>تست رایگان</b>

فعلاً سرویس تست رایگان فعال نشده است.
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # RESELLER
    if data == "reseller":

        bot.edit_message_text(
            """
🤝 <b>پنل نمایندگی</b>

پنل نمایندگی از همین بخش مدیریت می‌شود.
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # LICENSE
    if data == "license":

        bot.edit_message_text(
            """
🎫 <b>لایسنس ربات</b>

پلن‌های لایسنس در این بخش قرار می‌گیرند.
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # SUPPORT
    if data == "support":

        bot.edit_message_text(
            """
🆘 <b>پشتیبانی</b>

پیام خودت را برای پشتیبانی ارسال کن.
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # GUIDE
    if data == "guide":

        bot.edit_message_text(
            """
📚 <b>راهنما</b>

1️⃣ پلن VPN را انتخاب کن.

2️⃣ پرداخت را انجام بده.

3️⃣ بعد از تأیید، سرویس برایت ساخته می‌شود.

4️⃣ کانفیگ سرویس را دریافت می‌کنی.
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # ACCOUNT
    if data == "account":

        user = save_user(call.from_user)

        bot.edit_message_text(
            f"""
⚙️ <b>حساب کاربری</b>

🆔 شناسه:
<code>{user_id}</code>

👤 username:
@{user['username'] or '-'}

💰 موجودی:
{user['balance']:,} تومان
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # =========================
    # ADMIN
    # =========================

    if user_id != SUPERADMIN_ID:
        return

    if data == "admin":

        admin_menu(call.message)

        return

    if data == "adm_stats":

        con = db()

        users = con.execute(
            "SELECT COUNT(*) AS c FROM users"
        ).fetchone()["c"]

        services = con.execute(
            "SELECT COUNT(*) AS c FROM services WHERE status='active'"
        ).fetchone()["c"]

        payments = con.execute(
            "SELECT COUNT(*) AS c FROM payments"
        ).fetchone()["c"]

        con.close()

        bot.edit_message_text(
            f"""
📊 <b>آمار ربات</b>

👥 کاربران: {users}
🛡 سرویس فعال: {services}
💳 پرداخت‌ها: {payments}
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_back()
        )

        return

    if data == "adm_payment":

        text = f"""
💳 <b>تنظیمات پرداخت</b>

کارت‌به‌کارت:
{'✅ فعال' if get_setting('manual_payment') == '1' else '❌ خاموش'}

پرداخت آنلاین:
{'✅ فعال' if get_setting('online_payment') == '1' else '❌ خاموش'}

💳 کارت:
<code>{get_setting('card_number')}</code>

👤 نام:
{get_setting('card_name')}
"""

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "💳 تغییر شماره کارت",
                callback_data="set_card"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "👤 تغییر نام کارت",
                callback_data="set_card_name"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="admin"
            )
        )

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

        return

    if data == "set_card":

        bot.send_message(
            user_id,
            "💳 شماره کارت جدید را ارسال کن:"
        )

        bot.register_next_step_handler_by_chat_id(
            user_id,
            save_card_number
        )

        return

    if data == "set_card_name":

        bot.send_message(
            user_id,
            "👤 نام صاحب کارت را ارسال کن:"
        )

        bot.register_next_step_handler_by_chat_id(
            user_id,
            save_card_name
        )

        return

    if data == "adm_users":

        con = db()

        count = con.execute(
            "SELECT COUNT(*) AS c FROM users"
        ).fetchone()["c"]

        con.close()

        bot.edit_message_text(
            f"""
👥 <b>کاربران</b>

تعداد کاربران:
<b>{count}</b>
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_back()
        )

        return

    if data == "adm_plans":

        con = db()

        plans = con.execute(
            "SELECT * FROM plans ORDER BY id"
        ).fetchall()

        con.close()

        text = "💎 <b>پلن‌ها</b>\n\n"

        for plan in plans:

            text += f"""
#{plan['id']} - {plan['name']}
📦 {plan['volume_gb']}GB
⏳ {plan['duration_days']} روز
📱 {plan['devices']} دستگاه
💰 {plan['price']:,} تومان

"""

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_back()
        )

        return

    if data == "adm_test":

        bot.send_message(
            user_id,
            "✅ ربات، دیتابیس و Callback Handler فعال هستند."
        )

        return

    # APPROVE PAYMENT
    if data.startswith("approve:"):

        payment_id = int(data.split(":")[1])

        approve_payment(payment_id)

        bot.send_message(
            user_id,
            f"✅ پرداخت #{payment_id} تأیید شد."
        )

        return

    # REJECT PAYMENT
    if data.startswith("reject:"):

        payment_id = int(data.split(":")[1])

        reject_payment(payment_id)

        bot.send_message(
            user_id,
            f"❌ پرداخت #{payment_id} رد شد."
        )

        return


# =========================
# ADMIN MENU
# =========================

def admin_menu(message):

    markup = types.InlineKeyboardMarkup()

    markup.row(
        types.InlineKeyboardButton(
            "📊 آمار",
            callback_data="adm_stats"
        ),
        types.InlineKeyboardButton(
            "👥 کاربران",
            callback_data="adm_users"
        )
    )

    markup.row(
        types.InlineKeyboardButton(
            "💎 پلن‌ها",
            callback_data="adm_plans"
        ),
        types.InlineKeyboardButton(
            "💳 پرداخت",
            callback_data="adm_payment"
        )
    )

    markup.row(
        types.InlineKeyboardButton(
            "🧪 تست سیستم",
            callback_data="adm_test"
        )
    )

    bot.send_message(
        message.chat.id,
        "👑 <b>پنل مدیریت VirangarVPN</b>",
        reply_markup=markup
    )


def admin_back():

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "👑 پنل مدیریت",
            callback_data="admin"
        )
    )

    return markup


@bot.message_handler(commands=["admin"])
def admin_command(message):

    if message.from_user.id != SUPERADMIN_ID:
        return

    admin_menu(message)


# =========================
# PAYMENT
# =========================

def receive_receipt(message, plan_id):

    if not message.photo:

        bot.send_message(
            message.chat.id,
            "❌ لطفاً فقط عکس رسید را ارسال کن."
        )

        return

    con = db()

    plan = con.execute(
        "SELECT * FROM plans WHERE id=?",
        (plan_id,)
    ).fetchone()

    if not plan:
        con.close()
        return

    cursor = con.execute(
        """
        INSERT INTO payments
        (
            user_id,
            plan_id,
            amount,
            method,
            status,
            receipt_file_id,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            message.from_user.id,
            plan_id,
            plan["price"],
            "manual",
            "pending",
            message.photo[-1].file_id,
            datetime.utcnow().isoformat()
        )
    )

    payment_id = cursor.lastrowid

    con.commit()
    con.close()

    bot.send_message(
        message.chat.id,
        f"""
⏳ <b>رسید ثبت شد.</b>

شماره پرداخت:
<code>#{payment_id}</code>

بعد از بررسی مدیریت، نتیجه برایت ارسال می‌شود.
"""
    )

    if SUPERADMIN_ID:

        markup = types.InlineKeyboardMarkup()

        markup.row(
            types.InlineKeyboardButton(
                "✅ تأیید",
                callback_data=f"approve:{payment_id}"
            ),
            types.InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject:{payment_id}"
            )
        )

        bot.send_message(
            SUPERADMIN_ID,
            f"""
💳 <b>رسید پرداخت جدید</b>

🧾 شماره:
#{payment_id}

👤 کاربر:
<code>{message.from_user.id}</code>

💰 مبلغ:
<b>{plan['price']:,} تومان</b>
""",
            reply_markup=markup
        )

        bot.send_photo(
            SUPERADMIN_ID,
            message.photo[-1].file_id
        )


def approve_payment(payment_id):

    con = db()

    payment = con.execute(
        """
        SELECT *
        FROM payments
        WHERE id=?
        """,
        (payment_id,)
    ).fetchone()

    if not payment:
        con.close()
        return

    if payment["status"] != "pending":
        con.close()
        return

    plan = con.execute(
        """
        SELECT *
        FROM plans
        WHERE id=?
        """,
        (payment["plan_id"],)
    ).fetchone()

    expires = datetime.utcnow() + __import__("datetime").timedelta(
        days=plan["duration_days"]
    )

    con.execute(
        """
        UPDATE payments
        SET status='approved'
        WHERE id=?
        """,
        (payment_id,)
    )

    con.execute(
        """
        INSERT INTO services
        (
            user_id,
            plan_id,
            status,
            config,
            expires_at,
            created_at
        )
        VALUES (?, ?, 'active', ?, ?, ?)
        """,
        (
            payment["user_id"],
            payment["plan_id"],
            "PASARGUARD_PENDING",
            expires.isoformat(),
            datetime.utcnow().isoformat()
        )
    )

    con.execute(
        """
        INSERT INTO transactions
        (
            user_id,
            amount,
            kind,
            description,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            payment["user_id"],
            -payment["amount"],
            "purchase",
            f"خرید پلن #{payment['plan_id']}",
            datetime.utcnow().isoformat()
        )
    )

    con.commit()
    con.close()

    bot.send_message(
        payment["user_id"],
        """
✅ <b>پرداخت تأیید شد.</b>

سرویس شما ثبت شد.

⚠️ اتصال نهایی به PasarGuard در مرحله اتصال API انجام می‌شود.
"""
    )


def reject_payment(payment_id):

    con = db()

    payment = con.execute(
        """
        SELECT *
        FROM payments
        WHERE id=?
        """,
        (payment_id,)
    ).fetchone()

    if payment and payment["status"] == "pending":

        con.execute(
            """
            UPDATE payments
            SET status='rejected'
            WHERE id=?
            """,
            (payment_id,)
        )

        con.commit()

    con.close()

    if payment:

        bot.send_message(
            payment["user_id"],
            f"""
❌ <b>پرداخت #{payment_id} رد شد.</b>

اگر فکر می‌کنی اشتباهی رخ داده، با پشتیبانی تماس بگیر.
"""
        )


def save_card_number(message):

    set_setting(
        "card_number",
        message.text.strip()
    )

    bot.send_message(
        message.chat.id,
        "✅ شماره کارت ذخیره شد."
    )

    admin_menu(message)


def save_card_name(message):

    set_setting(
        "card_name",
        message.text.strip()
    )

    bot.send_message(
        message.chat.id,
        "✅ نام صاحب کارت ذخیره شد."
    )

    admin_menu(message)


# =========================
# RUN
# =========================

if __name__ == "__main__":

    init_db()

    print("🔥 VirangarVPN is running...")

    bot.infinity_polling(
        skip_pending=True,
        allowed_updates=[
            "message",
            "callback_query"
        ]
    )
PY
