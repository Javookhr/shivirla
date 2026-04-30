import asyncio
import logging
from aiogram import Bot
from database import add_coins, get_all_queue_users, get_user
from utils import active_sessions, in_search_queue
from config import COIN_PER_10MIN, COIN_INTERVAL, REMINDER_INTERVAL

logger = logging.getLogger(__name__)

REMINDER_MESSAGES = [
    "🔍 Hali dost topilmadi... Lekin kimdir seni qidirmoqda! Kut!",
    "💫 Botda {count}+ foydalanuvchi bor. Juftingiz topiladi!",
    "⏳ Qidirish davom etmoqda... 🎯 Mos keladigan odam kelishi mumkun!",
    "🌟 Sabr qilgan maqsadiga yetadi! Qidirishda davom et.",
    "💪 Hali tayyor! Biroz kut, yangi dost topiladi.",
]

_reminder_counter: dict[int, int] = {}


async def coin_task(bot: Bot):
    """Har 10 daqiqada aktiv foydalanuvchilarga 5 kumush beradi."""
    while True:
        await asyncio.sleep(COIN_INTERVAL)
        try:
            # Aktiv chatlardagi foydalanuvchilar
            for user_id in list(active_sessions.keys()):
                await add_coins(user_id, COIN_PER_10MIN)
                logger.debug(f"Coin: +{COIN_PER_10MIN} to {user_id}")

            # Navbatda kutayotganlar ham oladi (yarim miqdorda)
            for user_id in list(in_search_queue.keys()):
                if user_id not in active_sessions:
                    await add_coins(user_id, COIN_PER_10MIN // 2)
        except Exception as e:
            logger.error(f"Coin task error: {e}")


async def reminder_task(bot: Bot):
    """Har 20 daqiqada navbatda kutayotgan foydalanuvchilarga eslatma yuboradi."""
    while True:
        await asyncio.sleep(REMINDER_INTERVAL)
        try:
            queue_users = await get_all_queue_users()
            total = len(queue_users)

            for entry in queue_users:
                user_id = entry['user_id']
                counter = _reminder_counter.get(user_id, 0)
                msg_index = counter % len(REMINDER_MESSAGES)
                msg = REMINDER_MESSAGES[msg_index].replace("{count}", str(max(total, 10)))

                try:
                    await bot.send_message(user_id, msg)
                    _reminder_counter[user_id] = counter + 1
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Reminder task error: {e}")


def cleanup_reminder(user_id: int):
    """Foydalanuvchi navbatdan chiqqanda counterini tozalaydi."""
    _reminder_counter.pop(user_id, None)


async def start_tasks(bot: Bot):
    asyncio.create_task(coin_task(bot))
    asyncio.create_task(reminder_task(bot))
    logger.info("Background tasks started.")
