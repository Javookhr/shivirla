from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import VoiceIntro
from database import get_user, update_user_field
from buttons import main_menu_kb, cancel_edit_kb
from utils import safe_edit

router = Router()

MIN_DURATION = 3
MAX_DURATION = 30


@router.callback_query(F.data == "edit:voice")
async def voice_intro_start(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    has = bool(user.get('voice_intro_id'))
    await state.set_state(VoiceIntro.recording)
    prefix = "Sizda ovozli tanishuv mavjud. Yangilash uchun:\n\n" if has else ""
    await safe_edit(
        callback.message,
        f"Ovozli tanishuv\n\n"
        f"{prefix}"
        f"{MIN_DURATION}-{MAX_DURATION} soniyalik ovoz yuboring.\n\n"
        "Maslahat: ozingiz haqingizda qisqacha aytib bering — ism, yosh, qiziqishlar.",
        reply_markup=cancel_edit_kb()
    )
    await callback.answer()


@router.message(VoiceIntro.recording, F.voice)
async def voice_intro_save(message: Message, state: FSMContext):
    duration = message.voice.duration
    if duration < MIN_DURATION:
        return await message.answer(f"Juda qisqa! Kamida {MIN_DURATION} soniya yuboring.")
    if duration > MAX_DURATION:
        return await message.answer(f"Juda uzun! Maksimal {MAX_DURATION} soniya bolishi kerak.")
    await update_user_field(message.from_user.id, 'voice_intro_id', message.voice.file_id)
    await state.clear()
    secs = duration % 60
    mins = duration // 60
    dur = f"{mins}:{secs:02d}" if mins else f"{secs} soniya"
    await message.answer(
        f"Ovozli tanishuv saqlandi! ({dur})\n\n"
        "Endi dost/juft topilganda partner sizning ovozingizni eshitadi.",
        reply_markup=main_menu_kb()
    )


@router.message(VoiceIntro.recording)
async def voice_intro_wrong(message: Message):
    await message.answer("Iltimos, ovozli xabar yuboring. (Mikrofon tugmasini bosing)")


@router.callback_query(F.data == "edit:cancel")
async def edit_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
    await callback.answer()
