import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

SUPER_ADMIN_ID = int(
    os.getenv("SUPER_ADMIN_ID", "0") or 0
)

ADMIN_IDS = {
    int(x)
    for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",")
    if x.isdigit()
}

if SUPER_ADMIN_ID:
    ADMIN_IDS.add(SUPER_ADMIN_ID)

DB_PATH = os.getenv(
    "DB_PATH",
    "virangar.db"
).strip()

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN در فایل env تنظیم نشده است."
    )
