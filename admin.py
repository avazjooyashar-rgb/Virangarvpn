# admin.py

import logging
from datetime import datetime

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes

from database import one, all, execute
from keyboards import (
    admin_menu,
    back_admin,
    admin_panels_menu,
    admin_plans_menu,
    plan_admin_actions,
    panel_admin_actions,
    payment_admin_actions,
    ticket_admin_actions,
)

logger = logging.getLogger(__name__)


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(user_id: int) -> bool:
    row = one(
        """
        SELECT id
        FROM admins
        WHERE user_id = ?
          AND is_active = 1
        LIMIT 1
        """,
        (user_id,),
    )

    return bool(row)


# =========================================================
# SUPER ADMIN CHECK
# =========================================================

def is_super_admin(user_id: int) -> bool:
    row = one(
        """
        SELECT id
        FROM admins
        WHERE user_id = ?
          AND role = 'super_admin'
          AND is_active = 1
        LIMIT 1
        """,
        (user_id,),
    )

    return bool(row)


# =========================================================
# ADMIN HOME
# =========================================================

async def admin_home(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    user_id = update.effective_user.id

    if not is_admin(user_id):
        await query.edit_message_text(
            "❌ دسترسی ادمین ندارید."
        )
        return

    await query.edit_message_text(
        "👑 پنل مدیریت VirangarVPN\n\n"
        "از منوی زیر بخش موردنظر را انتخاب کنید:",
        reply_markup=admin_menu(),
    )


# =========================================================
# PANELS
# =========================================================

async def panels(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    rows = all(
        """
        SELECT *
        FROM panels
        ORDER BY id DESC
        """
    )

    if not rows:
        await query.edit_message_text(
            "📦 مدیریت پنل‌ها\n\n"
            "❌ هنوز هیچ پنلی ثبت نشده است.",
            reply_markup=admin_panels_menu(),
        )
        return

    buttons = []

    for row in rows:
        row = dict(row)

        status = (
            "🟢"
            if row.get("is_active")
            else "🔴"
        )

        buttons.append([
            InlineKeyboardButton(
                f"{status} {row.get('name') or 'پنل'}",
                callback_data=f"a_panel_{row['id']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "➕ افزودن پنل",
            callback_data="a_panel_add",
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="admin_home",
        )
    ])

    await query.edit_message_text(
        "📦 مدیریت پنل‌های PasarGuard\n\n"
        "پنل موردنظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================================================
# PANEL DETAILS
# =========================================================

async def panel_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    panel_id: int,
):
    query = update.callback_query

    row = one(
        "SELECT * FROM panels WHERE id = ?",
        (panel_id,),
    )

    if not row:
        await query.edit_message_text(
            "❌ پنل پیدا نشد.",
            reply_markup=back_admin("a_reseller"),
        )
        return

    panel = dict(row)

    status = (
        "🟢 فعال"
        if panel.get("is_active")
        else "🔴 غیرفعال"
    )

    plans_count = one(
        """
        SELECT COUNT(*) AS count
        FROM vpn_plans
        WHERE panel_id = ?
        """,
        (panel_id,),
    )

    count = (
        int(plans_count["count"])
        if plans_count
        else 0
    )

    await query.edit_message_text(
        "📦 اطلاعات پنل\n\n"
        f"🆔 ID: {panel['id']}\n"
        f"🏷 نام: {panel.get('name') or '-'}\n"
        f"🌐 آدرس: {panel.get('base_url') or '-'}\n"
        f"📊 وضعیت: {status}\n"
        f"💎 تعداد پلن‌ها: {count}\n\n"
        "عملیات موردنظر را انتخاب کنید:",
        reply_markup=panel_admin_actions(
            panel_id,
            bool(panel.get("is_active")),
        ),
    )


# =========================================================
# ADD PANEL START
# =========================================================

async def add_panel_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    context.user_data["state"] = "admin_panel_name"

    await query.edit_message_text(
        "➕ افزودن پنل جدید\n\n"
        "🏷 نام پنل را ارسال کنید:",
        reply_markup=back_admin("a_reseller"),
    )


# =========================================================
# ADD PANEL
# =========================================================

async def add_panel_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    state = context.user_data.get("state")

    if not state:
        return False

    # -----------------------------------------------------
    # PANEL NAME
    # -----------------------------------------------------

    if state == "admin_panel_name":

        name = (
            message.text or ""
        ).strip()

        if not name:
            await message.reply_text(
                "❌ نام پنل خالی است."
            )
            return True

        context.user_data[
            "admin_panel_name"
        ] = name

        context.user_data[
            "state"
        ] = "admin_panel_url"

        await message.reply_text(
            "🌐 آدرس کامل PasarGuard را ارسال کنید.\n\n"
            "مثال:\n"
            "https://panel.example.com",
            reply_markup=back_admin(
                "a_reseller"
            ),
        )

        return True

    # -----------------------------------------------------
    # PANEL URL
    # -----------------------------------------------------

    if state == "admin_panel_url":

        base_url = (
            message.text or ""
        ).strip().rstrip("/")

        if not (
            base_url.startswith("http://")
            or base_url.startswith("https://")
        ):
            await message.reply_text(
                "❌ آدرس نامعتبر است.\n\n"
                "آدرس باید با http:// یا https:// شروع شود."
            )
            return True

        context.user_data[
            "admin_panel_url"
        ] = base_url

        context.user_data[
            "state"
        ] = "admin_panel_username"

        await message.reply_text(
            "👤 نام کاربری ادمین PasarGuard را ارسال کنید.",
            reply_markup=back_admin(
                "a_reseller"
            ),
        )

        return True

    # -----------------------------------------------------
    # PANEL USERNAME
    # -----------------------------------------------------

    if state == "admin_panel_username":

        username = (
            message.text or ""
        ).strip()

        context.user_data[
            "admin_panel_username"
        ] = username

        context.user_data[
            "state"
        ] = "admin_panel_password"

        await message.reply_text(
            "🔐 رمز عبور ادمین PasarGuard را ارسال کنید.",
            reply_markup=back_admin(
                "a_reseller"
            ),
        )

        return True

    # -----------------------------------------------------
    # PANEL PASSWORD
    # -----------------------------------------------------

    if state == "admin_panel_password":

        password = (
            message.text or ""
        ).strip()

        name = context.user_data.get(
            "admin_panel_name"
        )

        base_url = context.user_data.get(
            "admin_panel_url"
        )

        username = context.user_data.get(
            "admin_panel_username"
        )

        execute(
            """
            INSERT INTO panels
            (
                name,
                base_url,
                username,
                password,
                api_key,
                is_active,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                base_url,
                username,
                password,
                "",
                1,
                datetime.utcnow().isoformat(),
            ),
        )

        context.user_data.pop(
            "admin_panel_name",
            None,
        )
        context.user_data.pop(
            "admin_panel_url",
            None,
        )
        context.user_data.pop(
            "admin_panel_username",
            None,
        )
        context.user_data.pop(
            "admin_panel_password",
            None,
        )
        context.user_data.pop(
            "state",
            None,
        )

        await message.reply_text(
            "✅ پنل با موفقیت اضافه شد.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "📦 مدیریت پنل‌ها",
                        callback_data="a_reseller",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "👑 پنل مدیریت",
                        callback_data="admin_home",
                    )
                ],
            ]),
        )

        return True

    return False


# =========================================================
# PLANS
# =========================================================

async def plans(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    rows = all(
        """
        SELECT *
        FROM vpn_plans
        ORDER BY panel_id ASC, sort_order ASC, id ASC
        """
    )

    if not rows:
        await query.edit_message_text(
            "🛡️ مدیریت پلن‌های VPN\n\n"
            "❌ هنوز هیچ پلنی ساخته نشده است.",
            reply_markup=admin_plans_menu(),
        )
        return

    buttons = []

    for row in rows:
        row = dict(row)

        status = (
            "🟢"
            if row.get("active")
            else "🔴"
        )

        buttons.append([
            InlineKeyboardButton(
                f"{status} {row.get('name') or 'پلن'}",
                callback_data=f"a_plan_{row['id']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "➕ افزودن پلن",
            callback_data="a_plan_add",
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="admin_home",
        )
    ])

    await query.edit_message_text(
        "🛡️ مدیریت پلن‌های VPN\n\n"
        "پلن موردنظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================================================
# PLAN DETAILS
# =========================================================

async def plan_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    plan_id: int,
):
    query = update.callback_query

    row = one(
        "SELECT * FROM vpn_plans WHERE id = ?",
        (plan_id,),
    )

    if not row:
        await query.edit_message_text(
            "❌ پلن پیدا نشد.",
            reply_markup=back_admin("a_vpn"),
        )
        return

    plan = dict(row)

    panel = one(
        "SELECT name FROM panels WHERE id = ?",
        (plan["panel_id"],),
    )

    panel_name = (
        panel["name"]
        if panel
        else "-"
    )

    status = (
        "🟢 فعال"
        if plan.get("active")
        else "🔴 غیرفعال"
    )

    await query.edit_message_text(
        "🛡️ اطلاعات پلن\n\n"
        f"🆔 ID: {plan['id']}\n"
        f"🏷 نام: {plan.get('name') or '-'}\n"
        f"🌐 پنل: {panel_name}\n"
        f"💰 قیمت: {int(plan.get('price') or 0):,} تومان\n"
        f"📦 حجم: {plan.get('volume') or '-'}\n"
        f"⏱ مدت: {plan.get('duration') or '-'}\n"
        f"👥 حداکثر کاربر: {plan.get('max_users') or 1}\n"
        f"📊 وضعیت: {status}\n\n"
        f"📝 توضیحات:\n"
        f"{plan.get('description') or '-'}",
        reply_markup=plan_admin_actions(
            plan_id,
            bool(plan.get("active")),
        ),
    )


# =========================================================
# ADD PLAN START
# =========================================================

async def add_plan_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    panels_rows = all(
        """
        SELECT *
        FROM panels
        WHERE is_active = 1
        ORDER BY id ASC
        """
    )

    if not panels_rows:
        await query.edit_message_text(
            "❌ ابتدا حداقل یک پنل فعال اضافه کنید.",
            reply_markup=back_admin("a_reseller"),
        )
        return

    buttons = []

    for panel in panels_rows:
        panel = dict(panel)

        buttons.append([
            InlineKeyboardButton(
                f"🌐 {panel['name']}",
                callback_data=f"a_plan_panel_{panel['id']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="a_vpn",
        )
    ])

    await query.edit_message_text(
        "➕ افزودن پلن\n\n"
        "🌐 ابتدا پنلی که این پلن متعلق به آن است انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================================================
# ADD PLAN PANEL
# =========================================================

async def add_plan_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    panel_id: int,
):
    query = update.callback_query

    panel = one(
        "SELECT * FROM panels WHERE id = ?",
        (panel_id,),
    )

    if not panel:
        await query.edit_message_text(
            "❌ پنل پیدا نشد.",
            reply_markup=back_admin("a_vpn"),
        )
        return

    context.user_data[
        "admin_plan_panel_id"
    ] = panel_id

    context.user_data[
        "state"
    ] = "admin_plan_name"

    await query.edit_message_text(
        f"🌐 پنل: {panel['name']}\n\n"
        "🏷 نام پلن را ارسال کنید:",
        reply_markup=back_admin(
            "a_vpn"
        ),
    )


# =========================================================
# ADD PLAN MESSAGE
# =========================================================

async def add_plan_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    state = context.user_data.get("state")

    if state == "admin_plan_name":

        name = (
            message.text or ""
        ).strip()

        if not name:
            await message.reply_text(
                "❌ نام پلن خالی است."
            )
            return True

        context.user_data[
            "admin_plan_name"
        ] = name

        context.user_data[
            "state"
        ] = "admin_plan_price"

        await message.reply_text(
            "💰 قیمت پلن را فقط به تومان ارسال کنید.\n\n"
            "مثال:\n"
            "150000"
        )

        return True

    if state == "admin_plan_price":

        try:
            price = int(
                (message.text or "")
                .replace(",", "")
                .replace("٬", "")
                .strip()
            )

            if price < 0:
                raise ValueError

        except Exception:
            await message.reply_text(
                "❌ قیمت نامعتبر است.\n"
                "مثال: 150000"
            )
            return True

        context.user_data[
            "admin_plan_price"
        ] = price

        context.user_data[
            "state"
        ] = "admin_plan_volume"

        await message.reply_text(
            "📦 حجم پلن را ارسال کنید.\n\n"
            "مثال:\n"
            "100GB"
        )

        return True

    if state == "admin_plan_volume":

        volume = (
            message.text or ""
        ).strip()

        if not volume:
            await message.reply_text(
                "❌ حجم نمی‌تواند خالی باشد."
            )
            return True

        context.user_data[
            "admin_plan_volume"
        ] = volume

        context.user_data[
            "state"
        ] = "admin_plan_duration"

        await message.reply_text(
            "⏱ مدت پلن را ارسال کنید.\n\n"
            "مثال:\n"
            "30d"
        )

        return True

    if state == "admin_plan_duration":

        duration = (
            message.text or ""
        ).strip()

        if not duration:
            await message.reply_text(
                "❌ مدت نمی‌تواند خالی باشد."
            )
            return True

        context.user_data[
            "admin_plan_duration"
        ] = duration

        context.user_data[
            "state"
        ] = "admin_plan_max_users"

        await message.reply_text(
            "👥 حداکثر تعداد کاربر را ارسال کنید.\n\n"
            "مثال:\n"
            "1"
        )

        return True

    if state == "admin_plan_max_users":

        try:
            max_users = int(
                (message.text or "").strip()
            )

            if max_users < 1:
                raise ValueError

        except Exception:
            await message.reply_text(
                "❌ تعداد کاربر نامعتبر است.\n"
                "مثال: 1"
            )
            return True

        context.user_data[
            "admin_plan_max_users"
        ] = max_users

        context.user_data[
            "state"
        ] = "admin_plan_description"

        await message.reply_text(
            "📝 توضیحات پلن را ارسال کنید.\n\n"
            "اگر توضیحی ندارید بنویسید:\n"
            "ندارد"
        )

        return True

    if state == "admin_plan_description":

        description = (
            message.text or ""
        ).strip()

        panel_id = context.user_data.get(
            "admin_plan_panel_id"
        )

        name = context.user_data.get(
            "admin_plan_name"
        )

        price = context.user_data.get(
            "admin_plan_price"
        )

        volume = context.user_data.get(
            "admin_plan_volume"
        )

        duration = context.user_data.get(
            "admin_plan_duration"
        )

        max_users = context.user_data.get(
            "admin_plan_max_users",
            1,
        )

        if description == "ندارد":
            description = ""

        execute(
            """
            INSERT INTO vpn_plans
            (
                panel_id,
                name,
                price,
                volume,
                duration,
                max_users,
                description,
                active,
                sort_order,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                panel_id,
                name,
                price,
                volume,
                duration,
                max_users,
                description,
                1,
                0,
                datetime.utcnow().isoformat(),
            ),
        )

        for key in (
            "admin_plan_panel_id",
            "admin_plan_name",
            "admin_plan_price",
            "admin_plan_volume",
            "admin_plan_duration",
            "admin_plan_max_users",
            "state",
        ):
            context.user_data.pop(
                key,
                None,
            )

        await message.reply_text(
            "✅ پلن با موفقیت ساخته شد.\n\n"
            "این پلن به همان پنلی که انتخاب کردید متصل شده "
            "و فقط برای همان پنل در خرید نمایش داده می‌شود.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🛡️ مدیریت پلن‌ها",
                        callback_data="a_vpn",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "👑 پنل مدیریت",
                        callback_data="admin_home",
                    )
                ],
            ]),
        )

        return True

    return False


# =========================================================
# TOGGLE PLAN
# =========================================================

async def toggle_plan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    plan_id: int,
):
    query = update.callback_query

    row = one(
        "SELECT active FROM vpn_plans WHERE id = ?",
        (plan_id,),
    )

    if not row:
        await query.answer(
            "پلن پیدا نشد.",
            show_alert=True,
        )
        return

    new_status = 0 if row["active"] else 1

    execute(
        """
        UPDATE vpn_plans
        SET active = ?
        WHERE id = ?
        """,
        (
            new_status,
            plan_id,
        ),
    )

    await query.answer(
        "وضعیت پلن تغییر کرد."
    )

    await plan_details(
        update,
        context,
        plan_id,
    )


# =========================================================
# DELETE PLAN
# =========================================================

async def delete_plan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    plan_id: int,
):
    query = update.callback_query

    await query.edit_message_text(
        "⚠️ حذف پلن\n\n"
        "آیا از حذف این پلن مطمئن هستید؟\n\n"
        "سرویس‌های قبلی کاربران حذف نمی‌شوند.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🗑 بله، حذف شود",
                    callback_data=f"a_plan_delete_yes_{plan_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 انصراف",
                    callback_data=f"a_plan_{plan_id}",
                )
            ],
        ]),
    )


async def delete_plan_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    plan_id: int,
):
    query = update.callback_query

    execute(
        """
        DELETE FROM vpn_plans
        WHERE id = ?
        """,
        (plan_id,),
    )

    await query.edit_message_text(
        "✅ پلن حذف شد.",
        reply_markup=back_admin("a_vpn"),
    )


# =========================================================
# USERS
# =========================================================

async def users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    total = one(
        "SELECT COUNT(*) AS count FROM users"
    )

    active = one(
        """
        SELECT COUNT(*) AS count
        FROM users
        WHERE is_active = 1
        """
    )

    total_count = (
        int(total["count"])
        if total
        else 0
    )

    active_count = (
        int(active["count"])
        if active
        else 0
    )

    rows = all(
        """
        SELECT *
        FROM users
        ORDER BY id DESC
        LIMIT 20
        """
    )

    lines = [
        "👥 کاربران",
        "",
        f"👤 کل کاربران: {total_count}",
        f"🟢 فعال: {active_count}",
        "",
    ]

    for row in rows:
        row = dict(row)

        lines.append(
            f"🆔 {row.get('id')} | "
            f"{row.get('first_name') or '-'} | "
            f"{row.get('username') or '-'}"
        )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=back_admin("admin_home"),
    )


# =========================================================
# PAYMENTS
# =========================================================

async def payments(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    rows = all(
        """
        SELECT *
        FROM payments
        ORDER BY id DESC
        LIMIT 30
        """
    )

    if not rows:
        await query.edit_message_text(
            "💳 پرداخت‌ها\n\n"
            "هیچ پرداختی ثبت نشده است.",
            reply_markup=back_admin("admin_home"),
        )
        return

    buttons = []

    for row in rows:
        row = dict(row)

        status = row.get("status")

        icon = {
            "pending": "🟡",
            "approved": "🟢",
            "rejected": "🔴",
        }.get(status, "⚪")

        buttons.append([
            InlineKeyboardButton(
                f"{icon} #{row['id']} — "
                f"{int(row.get('amount') or 0):,}",
                callback_data=f"a_payment_{row['id']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="admin_home",
        )
    ])

    await query.edit_message_text(
        "💳 مدیریت پرداخت‌ها\n\n"
        "پرداخت موردنظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================================================
# PAYMENT DETAILS
# =========================================================

async def payment_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    payment_id: int,
):
    query = update.callback_query

    row = one(
        """
        SELECT *
        FROM payments
        WHERE id = ?
        """,
        (payment_id,),
    )

    if not row:
        await query.edit_message_text(
            "❌ پرداخت پیدا نشد.",
            reply_markup=back_admin("a_payments"),
        )
        return

    payment = dict(row)

    await query.edit_message_text(
        "💳 اطلاعات پرداخت\n\n"
        f"🆔 پرداخت: #{payment['id']}\n"
        f"👤 کاربر: {payment.get('user_id')}\n"
        f"💰 مبلغ: {int(payment.get('amount') or 0):,} تومان\n"
        f"📌 نوع: {payment.get('method') or '-'}\n"
        f"📊 وضعیت: {payment.get('status') or '-'}\n"
        f"📅 تاریخ: {payment.get('created_at') or '-'}",
        reply_markup=payment_admin_actions(
            payment_id,
            payment.get("status"),
        ),
    )


# =========================================================
# STATS
# =========================================================

async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    users_count = one(
        "SELECT COUNT(*) AS count FROM users"
    )

    panels_count = one(
        "SELECT COUNT(*) AS count FROM panels"
    )

    plans_count = one(
        "SELECT COUNT(*) AS count FROM vpn_plans"
    )

    services_count = one(
        "SELECT COUNT(*) AS count FROM services"
    )

    tickets_count = one(
        "SELECT COUNT(*) AS count FROM tickets"
    )

    await query.edit_message_text(
        "📊 آمار ربات\n\n"
        f"👥 کاربران: {users_count['count'] if users_count else 0}\n"
        f"📦 پنل‌ها: {panels_count['count'] if panels_count else 0}\n"
        f"🛡️ پلن‌ها: {plans_count['count'] if plans_count else 0}\n"
        f"🔐 سرویس‌ها: {services_count['count'] if services_count else 0}\n"
        f"🎫 تیکت‌ها: {tickets_count['count'] if tickets_count else 0}",
        reply_markup=back_admin("admin_home"),
    )


# =========================================================
# ADMIN CALLBACK ROUTER
# =========================================================

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if not is_admin(
        update.effective_user.id
    ):
        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True,
        )
        return False

    data = query.data or ""

    try:

        if data == "admin_home":
            await admin_home(
                update,
                context,
            )
            return True

        if data == "a_reseller":
            await panels(
                update,
                context,
            )
            return True

        if data == "a_panel_add":
            await add_panel_start(
                update,
                context,
            )
            return True

        if data.startswith("a_panel_"):
            panel_id = int(
                data.rsplit("_", 1)[1]
            )

            await panel_details(
                update,
                context,
                panel_id,
            )
            return True

        if data == "a_vpn":
            await plans(
                update,
                context,
            )
            return True

        if data == "a_plan_add":
            await add_plan_start(
                update,
                context,
            )
            return True

        if data.startswith("a_plan_panel_"):
            panel_id = int(
                data.rsplit("_", 1)[1]
            )

            await add_plan_panel(
                update,
                context,
                panel_id,
            )
            return True

        if data.startswith("a_plan_delete_yes_"):
            plan_id = int(
                data.rsplit("_", 1)[1]
            )

            await delete_plan_confirm(
                update,
                context,
                plan_id,
            )
            return True

        if data.startswith("a_plan_delete_"):
            plan_id = int(
                data.rsplit("_", 1)[1]
            )

            await delete_plan(
                update,
                context,
                plan_id,
            )
            return True

        if data.startswith("a_plan_toggle_"):
            plan_id = int(
                data.rsplit("_", 1)[1]
            )

            await toggle_plan(
                update,
                context,
                plan_id,
            )
            return True

        if data.startswith("a_plan_"):
            plan_id = int(
                data.rsplit("_", 1)[1]
            )

            await plan_details(
                update,
                context,
                plan_id,
            )
            return True

        if data == "a_users":
            await users(
                update,
                context,
            )
            return True

        if data == "a_payments":
            await payments(
                update,
                context,
            )
            return True

        if data.startswith("a_payment_"):
            payment_id = int(
                data.rsplit("_", 1)[1]
            )

            await payment_details(
                update,
                context,
                payment_id,
            )
            return True

        if data == "a_stats":
            await stats(
                update,
                context,
            )
            return True

    except Exception:
        logger.exception(
            "Admin callback error: %s",
            data,
        )

        try:
            await query.edit_message_text(
                "❌ هنگام اجرای عملیات خطایی رخ داد.",
                reply_markup=back_admin(
                    "admin_home"
                ),
            )
        except Exception:
            pass

        return True

    return False


# =========================================================
# ADMIN MESSAGE ROUTER
# =========================================================

async def admin_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(
        update.effective_user.id
    ):
        return False

    if await add_panel_message(
        update,
        context,
    ):
        return True

    if await add_plan_message(
        update,
        context,
    ):
        return True

    return False
