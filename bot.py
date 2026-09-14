import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, SUPER_ADMIN_ID
from database import init_db
from keyboards import user_menu, force_join_menu
from user import user_callback, user_message
from admin import admin_callback, admin_message, is_admin
from database import all as db_all


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("VirangarVPN")


# =========================================================
# FORCE JOIN
# =========================================================

async def check_membership(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> bool:
    try:
        channels = db_all(
            """
            SELECT *
            FROM channels
            WHERE is_active = 1
            ORDER BY id ASC
            """
        )
    except Exception:
        logger.exception("Failed to load channels")
        return True

    if not channels:
        return True

    for channel in channels:
        chat_id = channel["chat_id"]

        try:
            member = await context.bot.get_chat_member(
                chat_id=chat_id,
                user_id=user_id,
            )

            if member.status in ("left", "kicked"):
                return False

        except Exception:
            logger.exception(
                "Membership check failed for channel %s",
                chat_id,
            )

    return True


async def force_join_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = (
        "🔒 <b>عضویت در کانال‌های اجباری</b>\n\n"
        "برای استفاده از ربات ابتدا باید در کانال‌های زیر عضو شوید.\n\n"
        "بعد از عضویت روی «✅ بررسی عضویت» بزنید."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=force_join_menu(),
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=force_join_menu(),
        )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.effective_user:
        return

    user_id = update.effective_user.id

    # ساخت کاربر در صورت وجود helper
    try:
        from database import execute

        execute(
            """
            INSERT OR IGNORE INTO users
            (
                user_id,
                username,
                first_name,
                created_at
            )
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                user_id,
                update.effective_user.username or "",
                update.effective_user.first_name or "",
            ),
        )
    except Exception:
        logger.exception("Failed to create/update user")

    # Super Admin همیشه دسترسی دارد
    if user_id != SUPER_ADMIN_ID:
        if not await check_membership(context, user_id):
            await force_join_message(update, context)
            return

    text = (
        "🚀 <b>به VirangarVPN خوش آمدید</b>\n\n"
        "🛡️ خرید و مدیریت سرویس‌های VPN\n"
        "💰 کیف پول و پرداخت\n"
        "📦 نمایندگی پنل‌ها\n"
        "🎫 پشتیبانی و تیکت\n\n"
        "👇 از منوی زیر انتخاب کنید:"
    )

    await update.message.reply_text(
        text,
        reply_markup=user_menu(),
    )


# =========================================================
# FORCE JOIN CALLBACK
# =========================================================

async def check_join_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if await check_membership(context, user_id):
        await query.edit_message_text(
            "✅ عضویت شما تأیید شد.\n\n"
            "به منوی اصلی خوش آمدید 👇",
            reply_markup=user_menu(),
        )
        return

    await query.answer(
        "❌ هنوز در همه کانال‌های اجباری عضو نشده‌اید.",
        show_alert=True,
    )


# =========================================================
# GLOBAL CALLBACK ROUTER
# =========================================================

async def callback_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if not query:
        return

    data = query.data or ""

    # بررسی عضویت
    if data == "check_join":
        await check_join_callback(update, context)
        return

    # خانه کاربر
    if data == "back_home":
        user_id = query.from_user.id

        if user_id != SUPER_ADMIN_ID:
            if not await check_membership(context, user_id):
                await force_join_message(update, context)
                return

        await query.answer()

        await query.edit_message_text(
            "🏠 <b>منوی اصلی</b>\n\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=user_menu(),
        )
        return

    # خانه ادمین
    if data == "admin_home":
        if not is_admin(query.from_user.id):
            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True,
            )
            return

        await admin_callback(update, context)
        return

    # callback های ادمین
    if (
        data.startswith("a_")
        or data.startswith("admin_")
        or data.startswith("approve_")
        or data.startswith("reject_")
    ):
        if not is_admin(query.from_user.id):
            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True,
            )
            return

        await admin_callback(update, context)
        return

    # بقیه callback ها → کاربر
    await user_callback(update, context)


# =========================================================
# MESSAGE ROUTER
# =========================================================

async def message_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.effective_user:
        return

    user_id = update.effective_user.id

    # پیام‌های ادمین
    if is_admin(user_id):
        handled = await admin_message(update, context)

        if handled:
            return

    # بررسی عضویت کاربران
    if user_id != SUPER_ADMIN_ID:
        if not await check_membership(context, user_id):
            await force_join_message(update, context)
            return

    # پیام‌های کاربر
    await user_message(update, context)


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.exception(
        "Unhandled exception:",
        exc_info=context.error,
    )


# =========================================================
# MAIN
# =========================================================

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN در فایل env تنظیم نشده است."
        )

    # ساخت دیتابیس و جدول‌ها
    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # /start
    application.add_handler(
        CommandHandler("start", start)
    )

    # Callback ها
    application.add_handler(
        CallbackQueryHandler(callback_router)
    )

    # پیام‌های متنی
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_router,
        )
    )

    # عکس‌ها؛ برای رسید کارت‌به‌کارت
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            message_router,
        )
    )

    # خطاها
    application.add_error_handler(
        error_handler
    )

    logger.info("VirangarVPN bot started")

    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
