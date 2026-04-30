from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import get_today_time, get_coins, get_leaderboard, get_user_rank
from buttons import main_menu_kb
from utils import format_minutes, SECTION_NAMES

router = Router()
MEDALS = ['1', '2', '3']
SEC_EMOJI = {'friend': '🔍', 'group': '👥', 'couple': '💑', 'lover': '❤️'}


def build_time_text(data: dict, coins: int, rank: int, leaders: list) -> str:
    lines = ["Bizning time\n"]
    sections = data['sections']
    if sections:
        for key, label in SECTION_NAMES.items():
            mins = sections.get(key, 0)
            if mins > 0:
                e = SEC_EMOJI.get(key, '•')
                lines.append(f"{e} {label}: {format_minutes(mins)}")
    else:
        lines.append("Bugun hali hech narsa qilmadingiz.")
    lines.append(f"\nJami bugun: {format_minutes(data['total'])}")
    lines.append(f"Kumush: {coins:,} ta")
    lines.append(f"Reyting: {rank}-orin")
    if leaders:
        lines.append("\nTop 10 — Kumush reytingi:")
        for i, u in enumerate(leaders):
            medal = f"{i+1}."
            lines.append(f"{medal} {u['name']} — {u['amount']:,} kumush")
    return "\n".join(lines)


@router.message(F.text == "⏱ Bizning time")
async def time_stats(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    data = await get_today_time(user_id)
    coins = await get_coins(user_id)
    rank = await get_user_rank(user_id)
    leaders = await get_leaderboard(10)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Yangilash", callback_data="time:refresh"))
    await message.answer(
        build_time_text(data, coins, rank, leaders),
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "time:refresh")
async def time_refresh(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = await get_today_time(user_id)
    coins = await get_coins(user_id)
    rank = await get_user_rank(user_id)
    leaders = await get_leaderboard(10)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Yangilash", callback_data="time:refresh"))
    try:
        await callback.message.edit_text(
            build_time_text(data, coins, rank, leaders),
            reply_markup=builder.as_markup()
        )
    except Exception:
        pass
    await callback.answer("Yangilandi!")
