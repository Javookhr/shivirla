import json
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from states import InterestsState
from database import get_user, update_user_field
from buttons import main_menu_kb, interests_kb
from utils import safe_edit
from constants import ALL_INTERESTS, INTEREST_EMOJIS

router = Router()


def interest_label(code: str) -> str:
    emoji = INTEREST_EMOJIS.get(code, "")
    name = ALL_INTERESTS.get(code, code)
    return f"{emoji} {name}"


def build_text(selected: list) -> str:
    count = len(selected)
    sel_text = "  ".join(selected) if selected else "Hech narsa"
    return (
        f"Qiziqishlaringizni tanlang\n\n"
        f"Tanlangan ({count}/8): {sel_text}\n\n"
        "Mos qiziqishli odamlar birinchi topiladi."
    )


@router.callback_query(F.data == "edit:interests")
async def interests_start(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Avval royxatdan oting.", show_alert=True)
        return
    try:
        selected = json.loads(user.get('interests') or '[]')
    except Exception:
        selected = []
    await state.set_state(InterestsState.selecting)
    await state.update_data(selected=selected)
    await safe_edit(
        callback.message,
        build_text(selected),
        reply_markup=interests_kb(selected)
    )
    await callback.answer()


@router.callback_query(InterestsState.selecting, F.data.startswith("int:"))
async def interests_toggle(callback: CallbackQuery, state: FSMContext):
    action = callback.data[4:]
    data = await state.get_data()
    selected: list = data.get('selected', [])

    if action == 'save':
        await update_user_field(callback.from_user.id, 'interests', json.dumps(selected))
        await state.clear()
        sel_text = "  ".join(selected) if selected else "Hech narsa"
        try:
            await callback.message.edit_text(f"Qiziqishlar saqlandi!\n\n{sel_text}")
        except Exception:
            pass
        await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_kb())
        await callback.answer("Saqlandi!")
        return

    if action == 'clear':
        selected = []
        await state.update_data(selected=selected)
        await callback.answer("Tozalandi")
    else:
        code = action
        if code not in ALL_INTERESTS:
            return await callback.answer()
        label = interest_label(code)
        if label in selected:
            selected.remove(label)
        else:
            if len(selected) >= 8:
                return await callback.answer(
                    "Maksimal 8 ta tanlashingiz mumkun!", show_alert=True
                )
            selected.append(label)
        await state.update_data(selected=selected)

    try:
        await callback.message.edit_text(
            build_text(selected),
            reply_markup=interests_kb(selected)
        )
    except Exception:
        pass
    await callback.answer()
