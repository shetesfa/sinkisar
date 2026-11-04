"""
Synksar Auto Publisher - Configuration Module
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Telegram Bot & Channel
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_RAW.split(",") if i.strip().isdigit()]

# Scheduling & Timezone
TIMEZONE = os.getenv("TIMEZONE", "Africa/Addis_Ababa")
PUBLISH_HOUR = int(os.getenv("PUBLISH_HOUR", "0"))      # 0 = 12:00 AM Midnight
PUBLISH_MINUTE = int(os.getenv("PUBLISH_MINUTE", "0"))  # 00

# Paths
SYNKSAR_DATA_DIR = Path(os.getenv("SYNKSAR_DATA_DIR", str(BASE_DIR / "SYNKSAR_DATA")))
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "synksar.db")))
DEFAULT_YEAR = int(os.getenv("DEFAULT_YEAR", "2018"))

# Web Dashboard
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))
DASHBOARD_SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "synksar-secret-key-2026-tewahedo")

# Default Links and Footer Text (Note: NO BOT LINK as requested by user)
CHANNEL_LINK_NAME = os.getenv("CHANNEL_LINK_NAME", "telegram channel")
CHANNEL_LINK_URL = os.getenv("CHANNEL_LINK_URL", "https://t.me/atsedeteguhan")

GROUP_LINK_NAME = os.getenv("GROUP_LINK_NAME", "Telegram group")
GROUP_LINK_URL = os.getenv("GROUP_LINK_URL", "https://t.me/atsede2009")

SUNDAY_SCHOOL_AMHARIC = os.getenv("SUNDAY_SCHOOL_AMHARIC", "አጸደ ትጉሃን ሰንበት ትምህርት ቤት")
SUNDAY_SCHOOL_ENGLISH = os.getenv("SUNDAY_SCHOOL_ENGLISH", "Atsede tguhan sunday school")

OPENING_PRAYER = os.getenv(
    "OPENING_PRAYER",
    "ለእግዚአብሔር ምስጋና ይሁን እኛንም በቅዱሳኑ ጸሎት ይማረን በረከታቸው ከእኛ ጋር ትሁን ለዘላለሙ አሜን"
)
