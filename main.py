import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from middlewares import SubscriptionMiddleware
from tasks import start_tasks

from handlers.registration import router as reg_router
from handlers.friends     import router as friends_router
from handlers.couple      import router as couple_router
from handlers.profile     import router as profile_router
from handlers.time_stats  import router as time_router
from handlers.admin       import router as admin_router
from handlers.voice_intro import router as voice_router
from handlers.interests   import router as interests_router
from handlers.gifts       import router as gifts_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    await init_db()
    logger.info("Database initialized.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    # Router tartibiga e'tibor bering — voice_router birinchi (edit:cancel uchun)
    dp.include_router(reg_router)
    dp.include_router(voice_router)
    dp.include_router(interests_router)
    dp.include_router(friends_router)
    dp.include_router(couple_router)
    dp.include_router(profile_router)
    dp.include_router(time_router)
    dp.include_router(admin_router)
    dp.include_router(gifts_router)

    logger.info("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await start_tasks(bot)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
