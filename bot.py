import os
import sqlite3
import telebot

from dotenv import load_dotenv
from telebot import types

# =========================
# CONFIG
# =========================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0") or 0)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN در فایل .env تنظیم نشده است.")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DB_FILE = "virangarvpn.db"


# =========================
# DATABASE
# =========================

def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 0,
            is_blocked INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            volume_gb INTEGER NOT NULL,
            duration_days INTEGER NOT NULL,
            devices INTEGER DEFAULT 1,
            price INTEGER NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            method TEXT NOT NULL,
            receipt_file_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER,
            status TEXT DEFAULT 'active',
            volume_gb INTEGER,
            duration_days INTEGER,
            devices INTEGER,
            expires_at TEXT,
            config TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # پلن‌های اولیه
    cur.execute("SELECT COUNT(*) FROM plans")
    count = cur.fetchone()[0]

    if count == 0:
        cur.execute("""
            INSERT INTO plans
            (name, volume_gb, duration_days, devices, price)
            VALUES (?, ?, ?, ?, ?)
        """, ("اقتصادی", 30, 30, 1, 100000))

        cur.execute("""
            INSERT INTO plans
            (name, volume_gb, duration_days, devices, price)
            VALUES (?, ?, ?, ?, ?)
        """, ("حرفه‌ای", 100, 60, 2, 200000))

        cur.execute("""
            INSERT INTO plans
            (name, volume_gb, duration_days, devices, price)
            VALUES (?, ?, ?, ?, ?)
        """, ("ویژه", 200, 90, 3, 350000))

    conn.commit()
    conn.close()


# =========================
# USERS
# =========================

def save_user(message):
    user = message.from_user

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO users
        (telegram_id, username, first_name)
        VALUES (?, ?, ?)
    """, (
        user.id,
        user.username or "",
        user.first_name or ""
    ))

    cur.execute("""
        UPDATE users
        SET username = ?, first_name = ?
        WHERE telegram_id = ?
    """, (
        user.username or "",
        user.first_name or "",
        user.id
    ))

    conn.commit()
    conn.close()


def get_user(telegram_id):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM users
        WHERE telegram_id = ?
    """, (telegram_id,))

    user = cur.fetchone()
    conn.close()

    return user


def is_blocked(telegram_id):
    user = get_user(telegram_id)
    return user and user["is_blocked"] == 1


# =========================
# USER MENU
# =========================

def user_menu():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2
    )

    keyboard.add(
        types.KeyboardButton("🛒 خرید VPN"),
        types.KeyboardButton("🛡 سرویس‌های من")
    )

    keyboard.add(
        types.KeyboardButton("🎁 تست رایگان"),
        types.KeyboardButton("💰 کیف پول")
    )

    keyboard.add(
        types.KeyboardButton("📜 تراکنش‌های من"),
        types.KeyboardButton("🤝 پنل نمایندگی")
    )

    keyboard.add(
        types.KeyboardButton("🎫 خرید لایسنس ربات"),
        types.KeyboardButton("🆘 پشتیبانی")
    )

    keyboard.add(
        types.KeyboardButton("📚 راهنما"),
        types.KeyboardButton("⚙️ حساب کاربری")
    )

    return keyboard


# =========================
# ADMIN MENU
# =========================

def admin_menu():
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    keyboard.add(
        types.InlineKeyboardButton(
            "📊 داشبورد",
            callback_data="admin_dashboard"
        ),
        types.InlineKeyboardButton(
            "👥 کاربران",
            callback_data="admin_users"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "💎 پلن‌های VPN",
            callback_data="admin_plans"
        ),
        types.InlineKeyboardButton(
            "📦 سرویس‌ها",
            callback_data="admin_services"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "💰 پرداخت‌ها",
            callback_data="admin_payments"
        ),
        types.InlineKeyboardButton(
            "🖥 پنل‌ها",
            callback_data="admin_panels"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🎁 تست رایگان",
            callback_data="admin_trial"
        ),
        types.InlineKeyboardButton(
            "🤝 نمایندگان",
            callback_data="admin_resellers"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "📢 ارسال همگانی",
            callback_data="admin_broadcast"
        ),
        types.InlineKeyboardButton(
            "⚙️ تنظیمات",
            callback_data="admin_settings"
        )
    )

    return keyboard


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start(message):
    save_user(message)

    if is_blocked(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "🚫 حساب شما مسدود شده است."
        )
        return

    text = (
        "🔥 <b>به VirangarVPN خوش آمدید</b>\n\n"
        "🚀 خرید و مدیریت سرویس VPN\n"
        "⚡️ سریع، ساده و حرفه‌ای\n\n"
        "👇 از منوی زیر انتخاب کنید."
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=user_menu()
    )


# =========================
# BUY VPN
# =========================

@bot.message_handler(func=lambda m: m.text == "🛒 خرید VPN")
def buy_vpn(message):
    save_user(message)

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM plans
        WHERE active = 1
        ORDER BY id
    """)

    plans = cur.fetchall()
    conn.close()

    if not plans:
        bot.send_message(
            message.chat.id,
            "❌ در حال حاضر پلنی برای فروش وجود ندارد."
        )
        return

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    for plan in plans:
        keyboard.add(
            types.InlineKeyboardButton(
                f"💎 {plan['name']} | {plan['price']:,} تومان",
                callback_data=f"plan_{plan['id']}"
            )
        )

    keyboard.add(
        types.InlineKeyboardButton(
            "❌ بستن",
            callback_data="close"
        )
    )

    bot.send_message(
        message.chat.id,
        "💎 <b>انتخاب پلن VPN</b>\n\n"
        "پلن موردنظر خودت رو انتخاب کن:",
        reply_markup=keyboard
    )


# =========================
# PLAN CALLBACK
# =========================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("plan_")
)
def plan_selected(call):
    plan_id = int(call.data.split("_")[1])

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM plans WHERE id = ? AND active = 1",
        (plan_id,)
    )

    plan = cur.fetchone()
    conn.close()

    if not plan:
        bot.answer_callback_query(
            call.id,
            "پلن پیدا نشد."
        )
        return

    text = (
        f"💎 <b>{plan['name']}</b>\n\n"
        f"📦 حجم: {plan['volume_gb']} GB\n"
        f"⏳ مدت: {plan['duration_days']} روز\n"
        f"📱 دستگاه: {plan['devices']}\n"
        f"💰 قیمت: {plan['price']:,} تومان\n\n"
        "روش پرداخت را انتخاب کنید:"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        types.InlineKeyboardButton(
            "💳 کارت به کارت",
            callback_data=f"cardpay_{plan_id}"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🌐 پرداخت آنلاین",
            callback_data=f"onlinepay_{plan_id}"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="back_buy"
        )
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

    bot.answer_callback_query(call.id)


# =========================
# CARD PAYMENT
# =========================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("cardpay_")
)
def card_payment(call):
    plan_id = int(call.data.split("_")[1])

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM plans WHERE id = ?",
        (plan_id,)
    )

    plan = cur.fetchone()
    conn.close()

    card_number = os.getenv("CARD_NUMBER", "").strip()
    card_holder = os.getenv("CARD_HOLDER", "").strip()

    if not card_number:
        bot.answer_callback_query(
            call.id,
            "پرداخت کارت به کارت فعال نیست."
        )
        return

    text = (
        "💳 <b>پرداخت کارت به کارت</b>\n\n"
        f"💰 مبلغ: <b>{plan['price']:,} تومان</b>\n\n"
        f"💳 شماره کارت:\n"
        f"<code>{card_number}</code>\n\n"
        f"👤 به نام:\n"
        f"<b>{card_holder}</b>\n\n"
        "بعد از انتقال وجه، تصویر رسید را همینجا ارسال کنید."
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        f"🧾 برای ثبت رسید، همینجا عکس پرداخت را ارسال کنید.\n\n"
        f"شناسه پلن: <code>{plan_id}</code>"
    )


# =========================
# ONLINE PAYMENT
# =========================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("onlinepay_")
)
def online_payment(call):
    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "🌐 <b>پرداخت آنلاین</b>\n\n"
        "⏳ درگاه پرداخت هنوز به ربات متصل نشده است.\n\n"
        "بعد از اتصال درگاه، پرداخت و تأیید به‌صورت خودکار انجام می‌شود."
    )


# =========================
# MY SERVICES
# =========================

@bot.message_handler(func=lambda m: m.text == "🛡 سرویس‌های من")
def my_services(message):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM services
        WHERE user_id = ?
        ORDER BY id DESC
    """, (message.from_user.id,))

    services = cur.fetchall()
    conn.close()

    if not services:
        bot.send_message(
            message.chat.id,
            "🛡 <b>سرویس‌های من</b>\n\n"
            "هنوز سرویس فعالی نداری."
        )
        return

    lines = ["🛡 <b>سرویس‌های من</b>\n"]

    for service in services:
        lines.append(
            f"🔹 سرویس #{service['id']}\n"
            f"📦 حجم: {service['volume_gb']} GB\n"
            f"⏳ مدت: {service['duration_days']} روز\n"
            f"📱 دستگاه: {service['devices']}\n"
            f"📌 وضعیت: {service['status']}\n"
        )

    bot.send_message(
        message.chat.id,
        "\n".join(lines)
    )


# =========================
# FREE TRIAL
# =========================

@bot.message_handler(func=lambda m: m.text == "🎁 تست رایگان")
def free_trial(message):
    bot.send_message(
        message.chat.id,
        "🎁 <b>تست رایگان</b>\n\n"
        "تنظیمات تست رایگان از پنل مدیریت انجام می‌شود.\n\n"
        "⏳ این بخش در مرحله اتصال به PasarGuard فعال می‌شود."
    )


# =========================
# WALLET
# =========================

@bot.message_handler(func=lambda m: m.text == "💰 کیف پول")
def wallet(message):
    user = get_user(message.from_user.id)

    balance = user["balance"] if user else 0

    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "➕ شارژ حساب",
            callback_data="wallet_charge"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "📜 تراکنش‌ها",
            callback_data="wallet_transactions"
        )
    )

    bot.send_message(
        message.chat.id,
        f"💰 <b>کیف پول من</b>\n\n"
        f"💵 موجودی: <b>{balance:,} تومان</b>",
        reply_markup=keyboard
    )


# =========================
# TRANSACTIONS
# =========================

@bot.message_handler(func=lambda m: m.text == "📜 تراکنش‌های من")
def transactions(message):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM transactions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 20
    """, (message.from_user.id,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.send_message(
            message.chat.id,
            "📜 هنوز تراکنشی ثبت نشده است."
        )
        return

    lines = ["📜 <b>تراکنش‌های من</b>\n"]

    for row in rows:
        sign = "+" if row["amount"] >= 0 else ""

        lines.append(
            f"💰 {sign}{row['amount']:,} تومان\n"
            f"📝 {row['description'] or row['type']}\n"
            f"🕐 {row['created_at']}\n"
        )

    bot.send_message(
        message.chat.id,
        "\n".join(lines)
    )


# =========================
# RESELLER
# =========================

@bot.message_handler(func=lambda m: m.text == "🤝 پنل نمایندگی")
def reseller_panel(message):
    bot.send_message(
        message.chat.id,
        "🤝 <b>پنل نمایندگی</b>\n\n"
        "از این بخش می‌توانید پنل نمایندگی خریداری کرده و "
        "کاربران و سرویس‌های خودتان را مدیریت کنید.\n\n"
        "⏳ بخش نمایندگی در مرحله بعد تکمیل می‌شود."
    )


# =========================
# LICENSE
# =========================

@bot.message_handler(func=lambda m: m.text == "🎫 خرید لایسنس ربات")
def bot_license(message):
    bot.send_message(
        message.chat.id,
        "🎫 <b>لایسنس ربات</b>\n\n"
        "پلن‌های لایسنس در این بخش قرار می‌گیرند."
    )


# =========================
# SUPPORT
# =========================

@bot.message_handler(func=lambda m: m.text == "🆘 پشتیبانی")
def support(message):
    support_username = os.getenv(
        "SUPPORT_USERNAME",
        ""
    ).strip()

    if support_username:
        bot.send_message(
            message.chat.id,
            f"🆘 <b>پشتیبانی</b>\n\n"
            f"برای ارتباط با پشتیبانی:\n"
            f"@{support_username.lstrip('@')}"
        )
    else:
        bot.send_message(
            message.chat.id,
            "🆘 پشتیبانی\n\n"
            "آیدی پشتیبانی هنوز تنظیم نشده است."
        )


# =========================
# GUIDE
# =========================

@bot.message_handler(func=lambda m: m.text == "📚 راهنما")
def guide(message):
    bot.send_message(
        message.chat.id,
        "📚 <b>راهنمای VirangarVPN</b>\n\n"
        "🛒 برای خرید، گزینه خرید VPN را بزنید.\n"
        "🛡 برای مشاهده سرویس‌ها، سرویس‌های من را بزنید.\n"
        "💰 برای مشاهده موجودی، کیف پول را بزنید.\n"
        "🆘 برای ارتباط با پشتیبانی، پشتیبانی را انتخاب کنید."
    )


# =========================
# ACCOUNT
# =========================

@bot.message_handler(func=lambda m: m.text == "⚙️ حساب کاربری")
def account(message):
    user = get_user(message.from_user.id)

    if not user:
        save_user(message)
        user = get_user(message.from_user.id)

    username = (
        f"@{user['username']}"
        if user["username"]
        else "ندارد"
    )

    bot.send_message(
        message.chat.id,
        "⚙️ <b>حساب کاربری</b>\n\n"
        f"🆔 آیدی: <code>{user['telegram_id']}</code>\n"
        f"👤 نام کاربری: {username}\n"
        f"💰 موجودی: {user['balance']:,} تومان"
    )


# =========================
# ADMIN
# =========================

@bot.message_handler(commands=["admin"])
def admin_command(message):
    if message.from_user.id != SUPER_ADMIN_ID:
        bot.reply_to(
            message,
            "🚫 دسترسی ندارید."
        )
        return

    bot.send_message(
        message.chat.id,
        "👑 <b>پنل مدیریت VirangarVPN</b>\n\n"
        "بخش موردنظر را انتخاب کنید:",
        reply_markup=admin_menu()
    )


# =========================
# ADMIN CALLBACKS
# =========================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("admin_")
)
def admin_callbacks(call):

    if call.from_user.id != SUPER_ADMIN_ID:
        bot.answer_callback_query(
            call.id,
            "🚫 دسترسی ندارید.",
            show_alert=True
        )
        return

    data = call.data

    if data == "admin_dashboard":
        conn = db()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users")
        users = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM services
            WHERE status = 'active'
        """)
        services = cur.fetchone()[0]

        cur.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE amount > 0
        """)
        revenue = cur.fetchone()[0]

        conn.close()

        bot.edit_message_text(
            "📊 <b>داشبورد</b>\n\n"
            f"👥 کاربران: {users}\n"
            f"🛡 سرویس‌های فعال: {services}\n"
            f"💰 گردش مالی ثبت‌شده: {revenue:,} تومان",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_menu()
        )

    elif data == "admin_users":
        conn = db()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]

        conn.close()

        bot.answer_callback_query(call.id)

        bot.send_message(
            call.message.chat.id,
            f"👥 <b>کاربران</b>\n\n"
            f"تعداد کاربران ثبت‌شده: <b>{count}</b>"
        )

    elif data == "admin_plans":
        conn = db()
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM plans
            ORDER BY id
        """)

        plans = cur.fetchall()
        conn.close()

        lines = ["💎 <b>پلن‌های VPN</b>\n"]

        for plan in plans:
            status = "فعال" if plan["active"] else "غیرفعال"

            lines.append(
                f"#{plan['id']} — {plan['name']}\n"
                f"📦 {plan['volume_gb']}GB | "
                f"⏳ {plan['duration_days']} روز | "
                f"💰 {plan['price']:,}\n"
                f"📌 {status}\n"
            )

        bot.edit_message_text(
            "\n".join(lines),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_menu()
        )

    elif data == "admin_payments":
        conn = db()
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM payments
            WHERE status = 'pending'
        """)

        pending = cur.fetchone()[0]
        conn.close()

        bot.answer_callback_query(call.id)

        bot.send_message(
            call.message.chat.id,
            "💰 <b>پرداخت‌ها</b>\n\n"
            f"⏳ پرداخت‌های در انتظار بررسی: <b>{pending}</b>"
        )

    else:
        bot.answer_callback_query(call.id)

        bot.send_message(
            call.message.chat.id,
            f"🛠 بخش <b>{data}</b>\n\n"
            "این بخش در مرحله بعد به‌صورت کامل پیاده‌سازی می‌شود."
        )


# =========================
# OTHER CALLBACKS
# =========================

@bot.callback_query_handler(func=lambda call: True)
def general_callbacks(call):

    if call.data == "close":
        try:
            bot.delete_message(
                call.message.chat.id,
                call.message.message_id
            )
        except Exception:
            pass

        bot.answer_callback_query(call.id)

    elif call.data == "back_buy":
        bot.answer_callback_query(call.id)
        buy_vpn(call.message)

    elif call.data == "wallet_charge":
        bot.answer_callback_query(call.id)

        bot.send_message(
            call.message.chat.id,
            "➕ <b>شارژ حساب</b>\n\n"
            "روش پرداخت را انتخاب کنید."
        )

    elif call.data == "wallet_transactions":
        bot.answer_callback_query(call.id)
        transactions(call.message)

    else:
        bot.answer_callback_query(call.id)


# =========================
# UNKNOWN MESSAGE
# =========================

@bot.message_handler(
    func=lambda message: True,
    content_types=["text"]
)
def unknown_message(message):

    if message.text.startswith("/"):
        return

    save_user(message)

    bot.send_message(
        message.chat.id,
        "👇 از منوی زیر انتخاب کنید:",
        reply_markup=user_menu()
    )


# =========================
# RUN
# =========================

if __name__ == "__main__":
    create_database()

    print("🔥 VirangarVPN Bot is running...")

    bot.infinity_polling(
        skip_pending=True,
        allowed_updates=["message", "callback_query"]
    )
