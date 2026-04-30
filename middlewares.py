from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database import get_user
from utils import check_subscriptions
from config import ADMIN_IDS

BYPASS_COMMANDS = {'/start', '/admin'}


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            user_id = event.from_user.id
            text = event.text or ''
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            text = ''
        else:
            return await handler(event, data)

        if user_id in ADMIN_IDS:
            return await handler(event, data)
        if text in BYPASS_COMMANDS:
            return await handler(event, data)

        user = await get_user(user_id)
        if not user:
            return await handler(event, data)

        bot = data['bot']
        unsubscribed = await check_subscriptions(bot, user_id)
        if unsubscribed:
            lines = ["Botdan foydalanish uchun quyidagi kanallarga obuna boling:\n"]
            for ch in unsubscribed:
                lines.append(f"@{ch['username']} — {ch['name']}")
            lines.append("\nObuna bolgach /start bosing.")
            msg = "\n".join(lines)
            if isinstance(event, Message):
                await event.answer(msg)
            else:
                await event.message.answer(msg)
            return

        return await handler(event, data)
