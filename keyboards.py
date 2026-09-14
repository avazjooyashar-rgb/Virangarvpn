from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# =========================================================
# GENERAL
# =========================================================

def kb(*rows):
    return InlineKeyboardMarkup(list(rows))


def back_button(callback_data, text="🔙 بازگشت"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text,
                callback_data=callback_data
            )
        ]
    ])


def back_user(target="back_home"):
    return back_button(target)


def back_admin(target="admin_home"):
    return back_button(target)


# =========================================================
# USER MENU
# =========================================================

def user_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛒 خرید VPN",
                callback_data="buy_vpn"
            ),
            InlineKeyboardButton(
                "🎁 تست رایگان",
                callback_data="free_trial"
            ),
        ],
        [
            InlineKeyboardButton(
                "🛡️ سرویس‌های من",
                callback_data="my_services"
            ),
            InlineKeyboardButton(
                "💰 کیف پول",
                callback_data="wallet"
            ),
        ],
        [
            InlineKeyboardButton(
                "📦 نمایندگی پنل‌ها",
                callback_data="reseller_panels"
            ),
            InlineKeyboardButton(
                "🔑 خرید لایسنس ربات",
                callback_data="bot_license"
            ),
        ],
        [
            InlineKeyboardButton(
                "🆘 پشتیبانی",
                callback_data="support"
            ),
            InlineKeyboardButton(
                "📚 راهنما",
                callback_data="help"
            ),
        ],
    ])


# =========================================================
# ADMIN MENU
# =========================================================

def admin_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📦 پنل‌های نمایندگی",
                callback_data="a_reseller"
            ),
            InlineKeyboardButton(
                "🔌 مدیریت API",
                callback_data="a_api"
            ),
        ],
        [
            InlineKeyboardButton(
                "🎁 تست رایگان",
                callback_data="a_trial"
            ),
            InlineKeyboardButton(
                "💳 پرداختی‌ها",
                callback_data="a_payments"
            ),
        ],
        [
            InlineKeyboardButton(
                "🎫 تیکت‌ها",
                callback_data="a_tickets"
            ),
            InlineKeyboardButton(
                "⚙️ تنظیمات",
                callback_data="a_settings"
            ),
        ],
        [
            InlineKeyboardButton(
                "📢 کانال‌های اجباری",
                callback_data="a_channels"
            ),
            InlineKeyboardButton(
                "👥 کاربران",
                callback_data="a_users"
            ),
        ],
        [
            InlineKeyboardButton(
                "👑 مدیریت ادمین‌ها",
                callback_data="a_admins"
            ),
            InlineKeyboardButton(
                "🔑 لایسنس ربات",
                callback_data="a_licenses"
            ),
        ],
        [
            InlineKeyboardButton(
                "🛡️ مدیریت پلن‌های VPN",
                callback_data="a_vpn"
            ),
        ],
        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="a_stats"
            ),
            InlineKeyboardButton(
                "📢 ارسال همگانی",
                callback_data="a_broadcast"
            ),
        ],
        [
            InlineKeyboardButton(
                "🏠 منوی کاربر",
                callback_data="back_home"
            ),
        ],
    ])


# =========================================================
# FORCE JOIN
# =========================================================

def force_join_menu(channels):
    rows = []

    for channel in channels:
        title = channel.get("title") or "عضویت در کانال"

        link = (
            channel.get("invite_link")
            or channel.get("username")
            or ""
        )

        if link and not link.startswith("http"):
            if link.startswith("@"):
                link = f"https://t.me/{link[1:]}"
            else:
                link = f"https://t.me/{link}"

        if link:
            rows.append([
                InlineKeyboardButton(
                    f"📢 {title}",
                    url=link
                )
            ])

    rows.append([
        InlineKeyboardButton(
            "✅ بررسی عضویت",
            callback_data="check_membership"
        )
    ])

    return InlineKeyboardMarkup(rows)


# =========================================================
# PANEL LIST
# =========================================================

def panel_list(panels, back_callback="back_home"):
    rows = []

    for panel in panels:
        status = "🟢" if panel["is_active"] else "🔴"

        rows.append([
            InlineKeyboardButton(
                f"{status} {panel['name']}",
                callback_data=f"panel_{panel['id']}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data=back_callback
        )
    ])

    return InlineKeyboardMarkup(rows)


# =========================================================
# PLAN LIST
# =========================================================

def plan_list(plans, back_callback="buy_vpn"):
    rows = []

    for plan in plans:
        status = "🟢" if plan["active"] else "🔴"

        rows.append([
            InlineKeyboardButton(
                f"{status} {plan['name']} | "
                f"{int(plan['price'] or 0):,} تومان",
                callback_data=f"plan_{plan['id']}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data=back_callback
        )
    ])

    return InlineKeyboardMarkup(rows)


# =========================================================
# PAYMENT METHODS
# =========================================================

def payment_methods():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💰 پرداخت از کیف پول",
                callback_data="pay_wallet"
            )
        ],
        [
            InlineKeyboardButton(
                "💳 کارت‌به‌کارت",
                callback_data="pay_card"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="buy_vpn"
            )
        ],
    ])


# =========================================================
# WALLET
# =========================================================

def wallet_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ افزایش موجودی",
                callback_data="wallet_deposit"
            )
        ],
        [
            InlineKeyboardButton(
                "📜 تراکنش‌های من",
                callback_data="wallet_transactions"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="back_home"
            )
        ],
    ])


# =========================================================
# SERVICES
# =========================================================

def services_list(services):
    rows = []

    for service in services:
        status = service.get("status") or "unknown"

        if status == "active":
            icon = "🟢"
        elif status == "expired":
            icon = "🔴"
        else:
            icon = "🟡"

        name = service.get("config_name") or "سرویس"

        rows.append([
            InlineKeyboardButton(
                f"{icon} {name}",
                callback_data=f"service_{service['id']}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="back_home"
        )
    ])

    return InlineKeyboardMarkup(rows)


# =========================================================
# SUPPORT
# =========================================================

def support_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎫 ایجاد تیکت",
                callback_data="ticket_create"
            )
        ],
        [
            InlineKeyboardButton(
                "📂 تیکت‌های من",
                callback_data="ticket_list"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="back_home"
            )
        ],
    ])


# =========================================================
# ADMIN PANEL MANAGEMENT
# =========================================================

def admin_panels_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ افزودن پنل",
                callback_data="panel_add"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 لیست پنل‌ها",
                callback_data="panel_list"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="admin_home"
            )
        ],
    ])


# =========================================================
# ADMIN PLAN MANAGEMENT
# =========================================================

def admin_plans_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ افزودن پلن",
                callback_data="plan_add"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 لیست پلن‌ها",
                callback_data="plan_list"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="admin_home"
            )
        ],
    ])


# =========================================================
# PLAN ADMIN ACTIONS
# =========================================================

def plan_admin_actions(plan_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✏️ ویرایش",
                callback_data=f"plan_edit_{plan_id}"
            ),
            InlineKeyboardButton(
                "🗑 حذف",
                callback_data=f"plan_delete_{plan_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 فعال/غیرفعال",
                callback_data=f"plan_toggle_{plan_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="a_vpn"
            )
        ],
    ])


# =========================================================
# PANEL ADMIN ACTIONS
# =========================================================

def panel_admin_actions(panel_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✏️ ویرایش",
                callback_data=f"panel_edit_{panel_id}"
            ),
            InlineKeyboardButton(
                "🗑 حذف",
                callback_data=f"panel_delete_{panel_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 فعال/غیرفعال",
                callback_data=f"panel_toggle_{panel_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "💎 مدیریت پلن‌ها",
                callback_data=f"panel_plans_{panel_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="a_api"
            )
        ],
    ])


# =========================================================
# PAYMENT ADMIN
# =========================================================

def payment_admin_actions(transaction_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تایید",
                callback_data=f"payment_approve_{transaction_id}"
            ),
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"payment_reject_{transaction_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="a_payments"
            )
        ],
    ])


# =========================================================
# TICKET ADMIN
# =========================================================

def ticket_admin_actions(ticket_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💬 پاسخ",
                callback_data=f"ticket_reply_{ticket_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ بستن تیکت",
                callback_data=f"ticket_close_{ticket_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="a_tickets"
            )
        ],
    ])


# =========================================================
# CONFIRMATION
# =========================================================

def confirm_keyboard(
    yes_callback,
    no_callback
):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ بله",
                callback_data=yes_callback
            ),
            InlineKeyboardButton(
                "❌ خیر",
                callback_data=no_callback
            ),
        ]
    ])
