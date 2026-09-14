# user.py

import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database import one, all, execute
from keyboards import (
    user_menu,
    back_user,
    payment_methods,
    wallet_menu,
    services_list,
    support_menu,
)
from pasarguard import (
    create_user,
    get_links,
    delete_user,
)

logger = logging.getLogger(__name__)


# =========================================================
# HELPERS
# =========================================================

def money(value):
    try:
        return f"{int(value):,} تومان"
    except Exception:
        return f"{value} تومان"


def clear_buy_state(context):
    for key in (
        "buy_panel_id",
        "buy_plan_id",
        "buy_config_name",
        "state",
    ):
        context.user_data.pop(key, None)


def get_user(user_id):
    row = one(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    )
    return dict(row) if row else None


def get_balance(user_id):
    row = one(
        "SELECT balance FROM wallets WHERE user_id = ?",
        (user_id,),
    )

    return int(row["balance"]) if row else 0


def get_plan(plan_id):
    row = one(
        "SELECT * FROM vpn_plans WHERE id = ?",
        (plan_id,),
    )

    return dict(row) if row else None


def get_panel(panel_id):
    row = one(
        "SELECT * FROM panels WHERE id = ?",
        (panel_id,),
    )

    return dict(row) if row else None


def get_active_panels():
    rows = all(
        """
        SELECT *
        FROM panels
        WHERE is_active = 1
        ORDER BY id ASC
        """
    )

    return [dict(row) for row in rows]


def get_panel_plans(panel_id):
    rows = all(
        """
        SELECT *
        FROM vpn_plans
        WHERE panel_id = ?
          AND active = 1
        ORDER BY sort_order ASC, id ASC
        """,
        (panel_id,),
    )

    return [dict(row) for row in rows]


def get_user_services(user_id):
    rows = all(
        """
        SELECT *
        FROM services
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,),
    )

    return [dict(row) for row in rows]


# =========================================================
# PLAN TEXT
# =========================================================

def plan_text(plan):
    return (
        f"📦 {plan.get('name') or '-'}\n\n"
        f"💰 قیمت: {money(plan.get('price', 0))}\n"
        f"📦 حجم: {plan.get('volume') or '-'}\n"
        f"⏱ مدت: {plan.get('duration') or '-'}\n"
        f"👥 حداکثر کاربر: {plan.get('max_users') or 1}\n\n"
        f"📝 {plan.get('description') or '-'}"
    )


# =========================================================
# BUY VPN - PANELS
# =========================================================

async def show_buy_vpn(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    panels = get_active_panels()

    if not panels:
        await query.edit_message_text(
            "🛒 خرید VPN\n\n"
            "❌ در حال حاضر هیچ پنل فعالی برای فروش وجود ندارد.",
            reply_markup=back_user(),
        )
        return

    buttons = []

    for panel in panels:
        plans = get_panel_plans(panel["id"])

        if not plans:
            continue

        buttons.append([
            InlineKeyboardButton(
                f"🌐 {panel['name']}",
                callback_data=f"buy_panel_{panel['id']}",
            )
        ])

    if not buttons:
        await query.edit_message_text(
            "🛒 خرید VPN\n\n"
            "❌ هیچ پنلی دارای پلن فعال نیست.",
            reply_markup=back_user(),
        )
        return

    buttons.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="back_home",
        )
    ])

    await query.edit_message_text(
        "🛒 خرید VPN\n\n"
        "🌐 پنل / تانل موردنظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================================================
# SELECT PANEL
# =========================================================

async def select_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    panel_id: int,
):
    query = update.callback_query

    panel = get_panel(panel_id)

    if not panel or not panel.get("is_active"):
        await query.edit_message_text(
            "❌ این پنل دیگر فعال نیست.",
            reply_markup=back_user("buy_vpn"),
        )
        return

    plans = get_panel_plans(panel_id)

    if not plans:
        await query.edit_message_text(
            f"🌐 {panel['name']}\n\n"
            "❌ برای این پنل هیچ پلن فعالی وجود ندارد.",
            reply_markup=back_user("buy_vpn"),
        )
        return

    context.user_data["buy_panel_id"] = panel_id

    buttons = []

    for plan in plans:
        buttons.append([
            InlineKeyboardButton(
                f"📦 {plan['name']} — {money(plan['price'])}",
                callback_data=f"buy_plan_{plan['id']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 انتخاب پنل",
            callback_data="buy_vpn",
        )
    ])

    await query.edit_message_text(
        f"🌐 پنل: {panel['name']}\n\n"
        "💎 پلن موردنظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================================================
# SELECT PLAN
# =========================================================

async def select_plan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    plan_id: int,
):
    query = update.callback_query

    plan = get_plan(plan_id)

    if not plan or not plan.get("active"):
        await query.edit_message_text(
            "❌ این پلن دیگر فعال نیست.",
            reply_markup=back_user("buy_vpn"),
        )
        return

    panel_id = plan.get("panel_id")

    panel = get_panel(panel_id)

    if not panel or not panel.get("is_active"):
        await query.edit_message_text(
            "❌ پنل مربوط به این پلن فعال نیست.",
            reply_markup=back_user("buy_vpn"),
        )
        return

    context.user_data["buy_panel_id"] = panel_id
    context.user_data["buy_plan_id"] = plan_id
    context.user_data["state"] = "buy_config_name"

    await query.edit_message_text(
        plan_text(plan)
        + "\n\n"
        "✏️ نام سرویس را ارسال کنید.\n\n"
        "این نام داخل PasarGuard برای سرویس شما استفاده می‌شود.",
        reply_markup=back_user(
            f"buy_panel_{panel_id}"
        ),
    )


# =========================================================
# PAYMENT METHODS
# =========================================================

async def show_payment_methods(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    plan_id = context.user_data.get("buy_plan_id")
    name = context.user_data.get("buy_config_name")

    plan = get_plan(plan_id) if plan_id else None

    if not plan or not name:
        clear_buy_state(context)

        await query.edit_message_text(
            "❌ سفارش پیدا نشد یا منقضی شده است.",
            reply_markup=user_menu(),
        )
        return

    balance = get_balance(
        update.effective_user.id
    )

    buttons = [
        [
            InlineKeyboardButton(
                "💰 پرداخت از کیف پول",
                callback_data="buy_wallet",
            )
        ],
        [
            InlineKeyboardButton(
                "💳 کارت‌به‌کارت",
                callback_data="buy_card",
            )
        ],
        [
            InlineKeyboardButton(
                "🌐 پرداخت آنلاین",
                callback_data="buy_online",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 تغییر نام سرویس",
                callback_data=f"buy_plan_{plan_id}",
            )
        ],
    ]

    await query.edit_message_text(
        "💳 انتخاب روش پرداخت\n\n"
        f"📦 پلن: {plan['name']}\n"
        f"✏️ نام سرویس: {name}\n"
        f"💰 مبلغ: {money(plan['price'])}\n"
        f"💳 موجودی کیف پول: {money(balance)}\n\n"
        "روش پرداخت را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================================================
# CREATE LOCAL SERVICE RECORD
# =========================================================

def save_service(
    user_id,
    plan,
    config_name,
    payment_method,
    pg_result,
):
    panel = get_panel(plan["panel_id"])

    subscription = (
        pg_result.get("subscription_url")
        or ""
    )

    expire = pg_result.get("expire")

    execute(
        """
        INSERT INTO services
        (
            user_id,
            panel_id,
            panel_name,
            price,
            duration,
            volume,
            status,
            config,
            created_at,
            expires_at,
            config_name,
            plan_id,
            payment_method,
            order_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            plan["panel_id"],
            panel["name"] if panel else "",
            int(plan["price"]),
            plan.get("duration") or "",
            plan.get("volume") or "",
            "active",
            subscription,
            datetime.utcnow().isoformat(),
            expire,
            config_name,
            plan["id"],
            payment_method,
            "completed",
        ),
    )

    row = one(
        """
        SELECT id
        FROM services
        WHERE user_id = ?
          AND plan_id = ?
          AND config_name = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            user_id,
            plan["id"],
            config_name,
        ),
    )

    return int(row["id"]) if row else None


# =========================================================
# WALLET PAYMENT
# =========================================================

async def pay_with_wallet(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    user_id = update.effective_user.id

    plan_id = context.user_data.get("buy_plan_id")
    name = context.user_data.get("buy_config_name")

    plan = get_plan(plan_id) if plan_id else None

    if not plan or not name:
        clear_buy_state(context)

        await query.edit_message_text(
            "❌ سفارش پیدا نشد.",
            reply_markup=user_menu(),
        )
        return

    price = int(plan["price"])

    balance = get_balance(user_id)

    if balance < price:
        await query.edit_message_text(
            "❌ موجودی کیف پول کافی نیست.\n\n"
            f"💰 قیمت: {money(price)}\n"
            f"💳 موجودی: {money(balance)}\n"
            f"📉 کمبود: {money(price - balance)}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💰 شارژ کیف پول",
                        callback_data="wallet_deposit",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 روش‌های پرداخت",
                        callback_data="buy_payment",
                    )
                ],
            ]),
        )
        return

    await query.edit_message_text(
        "⏳ در حال ساخت سرویس...\n\n"
        "🔐 اتصال به PasarGuard و ساخت کانفیگ در حال انجام است."
    )

    # =====================================================
    # IMPORTANT:
    # اول PasarGuard ساخته می‌شود.
    # اگر ساخت ناموفق باشد، پول کم نمی‌شود.
    # =====================================================

    try:
        result = create_user(
            plan["panel_id"],
            name,
            plan["volume"],
            plan["duration"],
            plan.get("max_users", 1),
        )

    except Exception as exc:
        logger.exception(
            "PasarGuard wallet purchase failed"
        )

        await query.edit_message_text(
            "❌ ساخت سرویس در PasarGuard ناموفق بود.\n\n"
            f"جزئیات:\n{str(exc)[:500]}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔁 تلاش مجدد",
                        callback_data="buy_wallet",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 روش‌های پرداخت",
                        callback_data="buy_payment",
                    )
                ],
            ]),
        )
        return

    service_id = None

    try:
        # =================================================
        # برداشت اتمیک موجودی
        # =================================================

        current = get_balance(user_id)

        if current < price:
            raise RuntimeError(
                "موجودی شما در لحظه پرداخت کافی نبود."
            )

        execute(
            """
            UPDATE wallets
            SET balance = balance - ?
            WHERE user_id = ?
              AND balance >= ?
            """,
            (
                price,
                user_id,
                price,
            ),
        )

        # =================================================
        # تراکنش
        # =================================================

        execute(
            """
            INSERT INTO transactions
            (
                user_id,
                amount,
                type,
                status,
                description,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                -price,
                "purchase",
                "approved",
                f"خرید پلن {plan['name']} | {name}",
                datetime.utcnow().isoformat(),
            ),
        )

        # =================================================
        # ثبت سرویس
        # =================================================

        service_id = save_service(
            user_id,
            plan,
            name,
            "wallet",
            result,
        )

        if not service_id:
            raise RuntimeError(
                "ثبت سرویس در دیتابیس انجام نشد."
            )

    except Exception as exc:
        logger.exception(
            "Wallet database transaction failed"
        )

        # =================================================
        # اگر DB شکست خورد، تلاش برای حذف کاربر PG
        # =================================================

        try:
            delete_user(
                plan["panel_id"],
                result["username"],
            )
        except Exception:
            logger.exception(
                "Could not rollback PasarGuard user"
            )

        await query.edit_message_text(
            "❌ ثبت نهایی خرید انجام نشد.\n\n"
            "💰 مبلغ از کیف پول شما کسر نشده است.",
            reply_markup=back_user(
                "buy_payment"
            ),
        )
        return

    # =====================================================
    # GET LINKS
    # =====================================================

    subscription = (
        result.get("subscription_url")
        or "-"
    )

    links = get_links(subscription)

    new_balance = get_balance(user_id)

    text = (
        "🎉 خرید با موفقیت انجام شد!\n\n"
        f"📦 پلن: {plan['name']}\n"
        f"✏️ نام سرویس: {name}\n"
        f"💰 مبلغ: {money(price)}\n"
        f"💳 موجودی جدید: {money(new_balance)}\n"
        f"🆔 سرویس: #{service_id}\n\n"
        "🔐 Subscription:\n"
        f"{subscription}"
    )

    if links:
        text += (
            "\n\n🔗 لینک‌های کانفیگ:\n"
            + "\n".join(links[:10])
        )

    clear_buy_state(context)

    await query.edit_message_text(
        text,
        reply_markup=back_user("back_home"),
    )


# =========================================================
# CARD TO CARD
# =========================================================

async def card_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    plan_id = context.user_data.get("buy_plan_id")
    name = context.user_data.get("buy_config_name")

    plan = get_plan(plan_id) if plan_id else None

    if not plan or not name:
        clear_buy_state(context)

        await query.edit_message_text(
            "❌ سفارش پیدا نشد.",
            reply_markup=user_menu(),
        )
        return

    settings = one(
        """
        SELECT *
        FROM payment_settings
        WHERE id = 1
        """
    )

    settings = dict(settings) if settings else {}

    card_number = (
        settings.get("card_number")
        or "-"
    )

    card_holder = (
        settings.get("card_holder")
        or "-"
    )

    context.user_data["state"] = (
        "buy_card_receipt"
    )

    await query.edit_message_text(
        "💳 کارت‌به‌کارت\n\n"
        f"📦 پلن: {plan['name']}\n"
        f"✏️ نام سرویس: {name}\n"
        f"💰 مبلغ: {money(plan['price'])}\n\n"
        f"💳 شماره کارت:\n{card_number}\n\n"
        f"👤 صاحب کارت:\n{card_holder}\n\n"
        "📸 پس از واریز، تصویر رسید را همینجا ارسال کنید.\n\n"
        "⚠️ پس از بررسی و تأیید ادمین، سرویس شما "
        "به‌صورت خودکار در PasarGuard ساخته خواهد شد.",
        reply_markup=back_user(
            "buy_payment"
        ),
    )


# =========================================================
# ONLINE PAYMENT
# =========================================================

async def online_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.edit_message_text(
        "🌐 پرداخت آنلاین\n\n"
        "⚠️ درگاه آنلاین هنوز در تنظیمات ربات "
        "فعال نشده است.\n\n"
        "فعلاً می‌توانید از کیف پول یا کارت‌به‌کارت استفاده کنید.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "💳 روش‌های پرداخت",
                    callback_data="buy_payment",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="buy_payment",
                )
            ],
        ]),
    )


# =========================================================
# MY SERVICES
# =========================================================

async def my_services(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    user_id = update.effective_user.id

    services = get_user_services(user_id)

    if not services:
        await query.edit_message_text(
            "🛡️ سرویس‌های من\n\n"
            "❌ هنوز هیچ سرویسی ندارید.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🛒 خرید VPN",
                        callback_data="buy_vpn",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="back_home",
                    )
                ],
            ]),
        )
        return

    buttons = []

    for service in services[:30]:
        status = service.get("status")

        icon = (
            "🟢"
            if status == "active"
            else "🔴"
        )

        buttons.append([
            InlineKeyboardButton(
                f"{icon} {service.get('config_name') or 'سرویس'} "
                f"#{service['id']}",
                callback_data=f"service_{service['id']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="back_home",
        )
    ])

    await query.edit_message_text(
        "🛡️ سرویس‌های من\n\n"
        "سرویس موردنظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================================================
# SERVICE DETAILS
# =========================================================

async def service_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    service_id: int,
):
    query = update.callback_query

    user_id = update.effective_user.id

    service = one(
        """
        SELECT *
        FROM services
        WHERE id = ?
          AND user_id = ?
        """,
        (
            service_id,
            user_id,
        ),
    )

    if not service:
        await query.edit_message_text(
            "❌ سرویس پیدا نشد.",
            reply_markup=back_user(
                "my_services"
            ),
        )
        return

    service = dict(service)

    text = (
        "🛡️ اطلاعات سرویس\n\n"
        f"🆔 شماره: #{service['id']}\n"
        f"✏️ نام: {service.get('config_name') or '-'}\n"
        f"📦 پلن: #{service.get('plan_id') or '-'}\n"
        f"📦 حجم: {service.get('volume') or '-'}\n"
        f"⏱ مدت: {service.get('duration') or '-'}\n"
        f"📅 انقضا: {service.get('expires_at') or '-'}\n"
        f"📊 وضعیت: {service.get('status') or '-'}\n\n"
        f"🔐 Subscription:\n"
        f"{service.get('config') or '-'}"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 سرویس‌های من",
                    callback_data="my_services",
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 منوی اصلی",
                    callback_data="back_home",
                )
            ],
        ]),
    )


# =========================================================
# WALLET
# =========================================================

async def wallet(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    user_id = update.effective_user.id

    balance = get_balance(user_id)

    await query.edit_message_text(
        "💰 کیف پول\n\n"
        f"💵 موجودی شما:\n"
        f"{money(balance)}\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=wallet_menu(),
    )


# =========================================================
# WALLET TRANSACTIONS
# =========================================================

async def wallet_transactions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    user_id = update.effective_user.id

    rows = all(
        """
        SELECT *
        FROM transactions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 30
        """,
        (user_id,),
    )

    if not rows:
        await query.edit_message_text(
            "📋 تراکنش‌های کیف پول\n\n"
            "هنوز تراکنشی ثبت نشده است.",
            reply_markup=back_user("wallet"),
        )
        return

    lines = [
        "📋 تراکنش‌های کیف پول\n"
    ]

    for row in rows:
        row = dict(row)

        amount = int(
            row.get("amount") or 0
        )

        icon = "🟢" if amount >= 0 else "🔴"

        lines.append(
            f"{icon} {money(amount)}\n"
            f"📝 {row.get('description') or '-'}\n"
            f"📅 {row.get('created_at') or '-'}\n"
        )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=back_user("wallet"),
    )


# =========================================================
# SUPPORT
# =========================================================

async def support(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.edit_message_text(
        "🎫 پشتیبانی\n\n"
        "اگر مشکلی دارید می‌توانید برای پشتیبانی "
        "تیکت ایجاد کنید.",
        reply_markup=support_menu(),
    )


# =========================================================
# HELP
# =========================================================

async def help_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.edit_message_text(
        "📚 راهنمای VirangarVPN\n\n"
        "🛒 خرید VPN\n"
        "از بخش خرید، پنل و پلن را انتخاب کنید، "
        "سپس نام سرویس و روش پرداخت را مشخص کنید.\n\n"
        "🛡️ سرویس‌های من\n"
        "تمام سرویس‌های خریداری‌شده شما در این قسمت نمایش داده می‌شوند.\n\n"
        "💰 کیف پول\n"
        "می‌توانید کیف پول خود را شارژ کرده و برای خرید VPN استفاده کنید.\n\n"
        "🎫 پشتیبانی\n"
        "برای مشکلات و سوالات می‌توانید تیکت ارسال کنید.",
        reply_markup=back_user("back_home"),
    )


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def user_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    data = query.data or ""

    try:
        if data == "buy_vpn":
            await show_buy_vpn(
                update,
                context,
            )
            return True

        if data.startswith("buy_panel_"):
            panel_id = int(
                data.rsplit("_", 1)[1]
            )

            await select_panel(
                update,
                context,
                panel_id,
            )
            return True

        if data.startswith("buy_plan_"):
            plan_id = int(
                data.rsplit("_", 1)[1]
            )

            await select_plan(
                update,
                context,
                plan_id,
            )
            return True

        if data == "buy_payment":
            await show_payment_methods(
                update,
                context,
            )
            return True

        if data == "buy_wallet":
            await pay_with_wallet(
                update,
                context,
            )
            return True

        if data == "buy_card":
            await card_payment(
                update,
                context,
            )
            return True

        if data == "buy_online":
            await online_payment(
                update,
                context,
            )
            return True

        if data == "my_services":
            await my_services(
                update,
                context,
            )
            return True

        if data.startswith("service_"):
            service_id = int(
                data.rsplit("_", 1)[1]
            )

            await service_details(
                update,
                context,
                service_id,
            )
            return True

        if data == "wallet":
            await wallet(
                update,
                context,
            )
            return True

        if data == "wallet_transactions":
            await wallet_transactions(
                update,
                context,
            )
            return True

        if data == "support":
            await support(
                update,
                context,
            )
            return True

        if data == "help":
            await help_page(
                update,
                context,
            )
            return True

    except Exception:
        logger.exception(
            "User callback error: %s",
            data,
        )

        try:
            await query.edit_message_text(
                "❌ یک خطای غیرمنتظره رخ داد.\n\n"
                "لطفاً دوباره تلاش کنید.",
                reply_markup=back_user(),
            )
        except Exception:
            pass

        return True

    return False


# =========================================================
# USER MESSAGE ROUTER
# =========================================================

async def user_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if not message:
        return False

    state = context.user_data.get("state")

    # =====================================================
    # BUY CONFIG NAME
    # =====================================================

    if state == "buy_config_name":

        name = (
            message.text or ""
        ).strip()

        if not name:
            await message.reply_text(
                "❌ نام سرویس نمی‌تواند خالی باشد.",
                reply_markup=back_user(
                    "buy_vpn"
                ),
            )
            return True

        if len(name) < 2:
            await message.reply_text(
                "❌ نام سرویس خیلی کوتاه است.\n\n"
                "حداقل ۲ کاراکتر وارد کنید.",
                reply_markup=back_user(
                    "buy_vpn"
                ),
            )
            return True

        if len(name) > 64:
            await message.reply_text(
                "❌ نام سرویس نباید بیشتر از ۶۴ کاراکتر باشد.",
                reply_markup=back_user(
                    "buy_vpn"
                ),
            )
            return True

        plan_id = context.user_data.get(
            "buy_plan_id"
        )

        plan = get_plan(plan_id) if plan_id else None

        if not plan:
            clear_buy_state(context)

            await message.reply_text(
                "❌ پلن پیدا نشد.",
                reply_markup=user_menu(),
            )
            return True

        context.user_data[
            "buy_config_name"
        ] = name

        context.user_data[
            "state"
        ] = "buy_payment"

        await message.reply_text(
            plan_text(plan)
            + "\n\n"
            f"✏️ نام سرویس: {name}\n\n"
            "💳 روش پرداخت را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💰 پرداخت از کیف پول",
                        callback_data="buy_wallet",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "💳 کارت‌به‌کارت",
                        callback_data="buy_card",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🌐 پرداخت آنلاین",
                        callback_data="buy_online",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 تغییر نام",
                        callback_data=f"buy_plan_{plan['id']}",
                    )
                ],
            ]),
        )

        return True

    return False
