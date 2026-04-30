import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8596548736:AAHi3V80RDQeTxUzB2xko8r2NwNMAbEOVRk")
ADMIN_IDS: list[int] = list(map(int, os.getenv("ADMIN_IDS", "8534111622").split(",")))

DB_NAME: str = "bot.db"
MIN_AGE: int = 10
MAX_AGE: int = 50
MIN_PASSWORD_LENGTH: int = 8
MAX_GROUP_SIZE: int = 6

COUPLE_REQUEST_TIMEOUT: int = 300    # 5 daqiqa
FIND_REQUEST_TIMEOUT: int = 43200    # 12 soat

COIN_PER_10MIN: int = 5              # har 10 daqiqada beriladigan kumush
COIN_INTERVAL: int = 600             # 10 daqiqa (soniyalarda)
REMINDER_INTERVAL: int = 1200        # 20 daqiqa (soniyalarda)

# Sovgalar narxi (kumushda)
GIFTS = {
    "premium_1": {"name": "Telegram Premium 1 oy",  "emoji": "⭐",  "price": 10000},
    "premium_3": {"name": "Telegram Premium 3 oy",  "emoji": "🌟",  "price": 30000},
    "premium_6": {"name": "Telegram Premium 6 oy",  "emoji": "💫",  "price": 59000},
    "premium_12":{"name": "Telegram Premium 12 oy", "emoji": "🏆",  "price": 120000},
}
