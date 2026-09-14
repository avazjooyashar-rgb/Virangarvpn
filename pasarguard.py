# pasarguard.py

import base64
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from database import one


# =========================================================
# PANEL
# =========================================================

def get_panel(panel_id: int):
    row = one(
        "SELECT * FROM panels WHERE id = ? AND is_active = 1",
        (int(panel_id),),
    )

    if not row:
        return None

    return dict(row)


# =========================================================
# HTTP HEADERS
# =========================================================

def make_headers(
    token: Optional[str] = None,
    api_key: str = "",
):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if api_key:
        headers["X-Api-Key"] = api_key

    elif token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


# =========================================================
# LOGIN
# =========================================================

def login(panel_data: dict):
    """
    اگر API Key داشته باشیم، لاگین JWT لازم نیست.
    در غیر این صورت با username/password وارد PasarGuard می‌شویم.
    """

    api_key = (panel_data.get("api_key") or "").strip()

    if api_key:
        return None

    username = (panel_data.get("username") or "").strip()
    password = (panel_data.get("password") or "").strip()

    if not username or not password:
        raise RuntimeError(
            "اطلاعات ورود PasarGuard برای این پنل تنظیم نشده است."
        )

    base_url = (panel_data.get("base_url") or "").strip().rstrip("/")

    if not base_url:
        raise RuntimeError(
            "آدرس پنل PasarGuard تنظیم نشده است."
        )

    response = requests.post(
        f"{base_url}/api/admin/token",
        data={
            "username": username,
            "password": password,
            "grant_type": "password",
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        timeout=20,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"ورود به PasarGuard ناموفق بود. "
            f"HTTP {response.status_code}"
        )

    try:
        data = response.json()
    except Exception:
        raise RuntimeError(
            "پاسخ ورود PasarGuard قابل خواندن نیست."
        )

    token = data.get("access_token")

    if not token:
        raise RuntimeError(
            "توکن PasarGuard دریافت نشد."
        )

    return token


# =========================================================
# VOLUME
# =========================================================

def volume_to_bytes(value) -> int:
    """
    مثال‌ها:
        100
        100GB
        1TB
        500MB
    """

    text = str(value).strip().upper()

    match = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*"
        r"(B|KB|MB|GB|TB|KIB|MIB|GIB|TIB)?",
        text,
    )

    if not match:
        raise ValueError(
            "حجم پلن نامعتبر است. مثال صحیح: 100GB"
        )

    number = float(match.group(1))
    unit = match.group(2) or "B"

    multipliers = {
        "B": 1,
        "KB": 1024,
        "KIB": 1024,
        "MB": 1024 ** 2,
        "MIB": 1024 ** 2,
        "GB": 1024 ** 3,
        "GIB": 1024 ** 3,
        "TB": 1024 ** 4,
        "TIB": 1024 ** 4,
    }

    return int(number * multipliers[unit])


# =========================================================
# DURATION
# =========================================================

def duration_to_seconds(value) -> int:
    """
    مثال‌ها:
        30
        30d
        1month
        12h
        7d
    """

    text = str(value).strip().lower()

    match = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*"
        r"(m|min|h|hour|hours|d|day|days|"
        r"w|week|weeks|mo|month|months)?",
        text,
    )

    if not match:
        raise ValueError(
            "مدت پلن نامعتبر است. مثال صحیح: 30d"
        )

    number = float(match.group(1))
    unit = match.group(2) or "d"

    if unit in ("m", "min"):
        multiplier = 60

    elif unit in ("h", "hour", "hours"):
        multiplier = 60 * 60

    elif unit in ("w", "week", "weeks"):
        multiplier = 7 * 24 * 60 * 60

    elif unit in ("mo", "month", "months"):
        multiplier = 30 * 24 * 60 * 60

    else:
        multiplier = 24 * 60 * 60

    return int(number * multiplier)


# =========================================================
# EXPIRATION
# =========================================================

def calculate_expire(duration) -> str:
    seconds = duration_to_seconds(duration)

    expire = datetime.now(timezone.utc) + timedelta(
        seconds=seconds
    )

    return expire.replace(
        microsecond=0
    ).isoformat()


# =========================================================
# CREATE USER
# =========================================================

def create_user(
    panel_id: int,
    username: str,
    volume,
    duration,
    max_users: int = 1,
):
    """
    ساخت کاربر واقعی داخل PasarGuard.
    """

    panel_data = get_panel(panel_id)

    if not panel_data:
        raise RuntimeError(
            "پنل PasarGuard فعال پیدا نشد."
        )

    base_url = (
        panel_data.get("base_url") or ""
    ).strip().rstrip("/")

    if not base_url:
        raise RuntimeError(
            "آدرس پنل PasarGuard خالی است."
        )

    api_key = (
        panel_data.get("api_key") or ""
    ).strip()

    token = login(panel_data)

    expire = calculate_expire(duration)

    data_limit = volume_to_bytes(volume)

    username = str(username).strip()

    if not username:
        raise RuntimeError(
            "نام سرویس خالی است."
        )

    max_users = max(
        1,
        int(max_users or 1),
    )

    payload = {
        "username": username,
        "data_limit": data_limit,
        "expire": expire,
        "data_limit_reset_strategy": "no_reset",
        "status": "active",
        "proxy_settings": {},
        "note": (
            f"VirangarVPN | "
            f"max_users={max_users}"
        ),
    }

    response = requests.post(
        f"{base_url}/api/user",
        json=payload,
        headers=make_headers(
            token=token,
            api_key=api_key,
        ),
        timeout=30,
    )

    # اگر API Key منقضی/نامعتبر بود،
    # در صورت داشتن username/password با JWT دوباره تست می‌کنیم.
    if response.status_code in (401, 403):

        if (
            api_key
            and panel_data.get("username")
            and panel_data.get("password")
        ):
            fallback_panel = dict(panel_data)
            fallback_panel["api_key"] = ""

            token = login(fallback_panel)

            response = requests.post(
                f"{base_url}/api/user",
                json=payload,
                headers=make_headers(
                    token=token,
                    api_key="",
                ),
                timeout=30,
            )

    if response.status_code not in (200, 201):

        error_text = response.text[:500]

        raise RuntimeError(
            f"ساخت سرویس در PasarGuard ناموفق بود "
            f"(HTTP {response.status_code})\n"
            f"{error_text}"
        )

    try:
        result = response.json()
    except Exception:
        raise RuntimeError(
            "PasarGuard کاربر را ساخت اما پاسخ JSON قابل خواندن نیست."
        )

    subscription_url = (
        result.get("subscription_url")
        or result.get("subscription_token")
        or result.get("subscription")
        or ""
    )

    return {
        "username": (
            result.get("username")
            or username
        ),
        "id": result.get("id"),
        "subscription_url": subscription_url,
        "expire": (
            result.get("expire")
            or expire
        ),
        "data_limit": (
            result.get("data_limit")
            or data_limit
        ),
        "raw": result,
    }


# =========================================================
# DELETE USER
# =========================================================

def delete_user(
    panel_id: int,
    username: str,
) -> bool:

    panel_data = get_panel(panel_id)

    if not panel_data:
        return False

    base_url = (
        panel_data.get("base_url") or ""
    ).strip().rstrip("/")

    if not base_url:
        return False

    api_key = (
        panel_data.get("api_key") or ""
    ).strip()

    token = login(panel_data)

    url = (
        f"{base_url}/api/user/"
        f"{requests.utils.quote(str(username), safe='')}"
    )

    response = requests.delete(
        url,
        headers=make_headers(
            token=token,
            api_key=api_key,
        ),
        timeout=20,
    )

    # API Key fallback
    if response.status_code in (401, 403):

        if (
            api_key
            and panel_data.get("username")
            and panel_data.get("password")
        ):
            fallback_panel = dict(panel_data)
            fallback_panel["api_key"] = ""

            token = login(fallback_panel)

            response = requests.delete(
                url,
                headers=make_headers(
                    token=token,
                    api_key="",
                ),
                timeout=20,
            )

    return response.status_code in (
        200,
        204,
    )


# =========================================================
# GET SUBSCRIPTION LINKS
# =========================================================

def get_links(subscription_url: str):
    """
    لینک‌های VLESS / VMess / Trojan و ...
    را از Subscription دریافت می‌کند.
    """

    if not subscription_url:
        return []

    url = str(subscription_url).strip()

    if not url:
        return []

    try:
        response = requests.get(
            url.rstrip("/") + "/links",
            timeout=20,
        )

        if response.status_code != 200:
            return []

        text = response.text.strip()

        if not text:
            return []

        decoded = ""

        try:
            padding = "=" * (
                -len(text) % 4
            )

            decoded = base64.b64decode(
                text + padding
            ).decode(
                "utf-8",
                errors="ignore",
            )

        except Exception:
            decoded = ""

        source = (
            decoded
            if "://" in decoded
            else text
        )

        links = []

        for line in source.splitlines():

            line = line.strip()

            if "://" not in line:
                continue

            links.append(line)

        return links[:20]

    except Exception:
        return []


# =========================================================
# GET SUBSCRIPTION
# =========================================================

def get_subscription_url(
    panel_id: int,
    username: str,
):
    """
    اطلاعات کاربر را از PasarGuard می‌گیرد
    و subscription URL را برمی‌گرداند.
    """

    panel_data = get_panel(panel_id)

    if not panel_data:
        raise RuntimeError(
            "پنل PasarGuard پیدا نشد."
        )

    base_url = (
        panel_data.get("base_url") or ""
    ).strip().rstrip("/")

    api_key = (
        panel_data.get("api_key") or ""
    ).strip()

    token = login(panel_data)

    url = (
        f"{base_url}/api/user/"
        f"{requests.utils.quote(str(username), safe='')}"
    )

    response = requests.get(
        url,
        headers=make_headers(
            token=token,
            api_key=api_key,
        ),
        timeout=20,
    )

    if response.status_code in (401, 403):

        if (
            api_key
            and panel_data.get("username")
            and panel_data.get("password")
        ):
            fallback_panel = dict(panel_data)
            fallback_panel["api_key"] = ""

            token = login(fallback_panel)

            response = requests.get(
                url,
                headers=make_headers(
                    token=token,
                    api_key="",
                ),
                timeout=20,
            )

    if response.status_code != 200:
        raise RuntimeError(
            f"دریافت سرویس از PasarGuard ناموفق بود "
            f"(HTTP {response.status_code})"
        )

    data = response.json()

    return (
        data.get("subscription_url")
        or data.get("subscription_token")
        or data.get("subscription")
        or ""
    )


# =========================================================
# TEST PANEL CONNECTION
# =========================================================

def test_connection(panel_id: int) -> bool:
    """
    تست اتصال پنل.
    """

    panel_data = get_panel(panel_id)

    if not panel_data:
        return False

    base_url = (
        panel_data.get("base_url") or ""
    ).strip().rstrip("/")

    if not base_url:
        return False

    api_key = (
        panel_data.get("api_key") or ""
    ).strip()

    try:
        token = login(panel_data)

        response = requests.get(
            f"{base_url}/api/user",
            headers=make_headers(
                token=token,
                api_key=api_key,
            ),
            timeout=15,
        )

        if response.status_code in (
            200,
            401,
            403,
        ):
            return response.status_code == 200

        return False

    except Exception:
        return False
