import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from states import ChatState
from database import (
    get_user, get_couple, get_partner_id,
    create_couple_request, get_couple_request, update_request_status,
    create_chat, get_chat_participants,
    get_couple_photos, delete_couple_photo,
)
from buttons import (
    main_menu_kb, end_chat_kb, lover_section_kb,
    connect_request_kb, chat_with_lover_kb, photo_delete_kb
)
from utils import (
    start_session, get_session,
    start_section_timer, safe_edit, format_time
)
from config import COUPLE_REQUEST_TIMEOUT

router = Router()


def other_fsm(state: FSMContext, bot_id: int, uid: int) -> FSMContext:
    key = StorageKey(bot_id=bot_id, chat_id=uid, user_id=uid)
    return FSMContext(storage=state.storage, key=key)


# ─── SEVGILIM MENU ───────────────────────────────────────────────────────────

@router.message(F.text == "❤️ Sevgilim")
async def lover_menu(message: Message, state: FSMContext):
    await state.clear()
    couple = await get_couple(message.from_user.id)
    if not couple:
        await message.answer(
            "Sevgilim bolimi\n\n"
            "Hozircha sevgilim yoq.\n"
            "Yangi Dostlar → Juft topish orqali juft toping!",
            reply_markup=main_menu_kb())
        return
    await message.answer("Sevgilim bolimi\n\nNimani kormoqchisiz?",
                         reply_markup=lover_section_kb())


# ─── SEVGANIM ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "lover:my")
async def lover_my(callback: CallbackQuery):
    uid    = callback.from_user.id
    couple = await get_couple(uid)
    if not couple:
        return await callback.answer("Hozircha sevgilim yoq.", show_alert=True)
    pid     = await get_partner_id(uid)
    partner = await get_user(pid) if pid else None
    if not partner:
        return await callback.answer("Sevgilim topilmadi.", show_alert=True)

    g    = "Erkak" if partner.get('gender') == 'erkak' else "Ayol"
    text = (
        f"Sevganim\n\n"
        f"Ism: {partner['name']}\n"
        f"Username: @{partner['username']}\n"
        f"Yosh: {partner['age']}\n"
        f"Jins: {g}"
    )
    kb = chat_with_lover_kb(pid)
    if partner.get('photo_id'):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(partner['photo_id'], caption=text, reply_markup=kb)
    else:
        await safe_edit(callback.message, text, reply_markup=kb)
    await callback.answer()


# ─── CHAT SO'ROVI ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("lover:chat:"))
async def lover_chat_request(callback: CallbackQuery, state: FSMContext, bot: Bot):
    uid   = callback.from_user.id
    to_id = int(callback.data.split(':')[2])
    if await get_session(uid):
        return await callback.answer("Siz allaqachon chatdasiz!", show_alert=True)
    me = await get_user(uid)
    if not me:
        return await callback.answer("Xatolik.", show_alert=True)

    rid = await create_couple_request(uid, to_id)
    await safe_edit(callback.message, "Sevgilimga sorov yuborildi. 5 daqiqa javob kutiladi...")
    try:
        await bot.send_message(
            to_id,
            f"Sevgilimdan boglanish sorov!\n\n{me['name']} siz bilan suxbatlashmoqchi.",
            reply_markup=connect_request_kb(rid))
    except Exception:
        await callback.message.answer(
            "Sevgilim botni bloklagan yoki mavjud emas.",
            reply_markup=lover_section_kb())
        await callback.answer()
        return
    asyncio.create_task(_timeout_request(rid, uid, bot, callback.message.chat.id))
    await callback.answer()


async def _timeout_request(request_id: int, from_id: int, bot: Bot, chat_id: int):
    await asyncio.sleep(COUPLE_REQUEST_TIMEOUT)
    req = await get_couple_request(request_id)
    if req and req['status'] == 'pending':
        await update_request_status(request_id, 'expired')
        try:
            await bot.send_message(
                chat_id,
                "Sorov bekor qilindi — 5 daqiqa javob bolmadi.",
                reply_markup=main_menu_kb())
        except Exception:
            pass


# ─── QABUL / RAD ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("connect:accept:"))
async def connect_accept(callback: CallbackQuery, state: FSMContext, bot: Bot):
    rid = int(callback.data.split(':')[2])
    req = await get_couple_request(rid)
    if not req or req['status'] != 'pending':
        return await callback.answer("Sorov muddati otgan.", show_alert=True)
    await update_request_status(rid, 'accepted')
    fid, tid = req['from_id'], req['to_id']

    chat_id = await create_chat('lover', [fid, tid])
    await start_session(fid, chat_id, 'lover')
    await start_session(tid, chat_id, 'lover')
    start_section_timer(fid, 'lover')
    start_section_timer(tid, 'lover')

    me      = await get_user(tid)
    partner = await get_user(fid)
    me_n    = me['name']      if me      else "U"
    p_n     = partner['name'] if partner else "U"

    await other_fsm(state, bot.id, fid).set_state(ChatState.in_lover_chat)
    await state.set_state(ChatState.in_lover_chat)

    await safe_edit(callback.message, f"Chat boshlandi! {p_n} bilan gaplashishingiz mumkun.")
    await callback.message.answer("Yozishingiz mumkun.", reply_markup=end_chat_kb())
    try:
        await bot.send_message(fid, f"{me_n} sorovingizni qabul qildi! Chat boshlandi.",
                               reply_markup=end_chat_kb())
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("connect:reject:"))
async def connect_reject(callback: CallbackQuery, bot: Bot):
    rid = int(callback.data.split(':')[2])
    req = await get_couple_request(rid)
    if not req:
        return await callback.answer()
    await update_request_status(rid, 'rejected')
    try:
        await callback.message.edit_text("Sorov rad etildi.")
    except Exception:
        pass
    try:
        await bot.send_message(req['from_id'], "Sevgilim sorovingizni rad etdi.",
                               reply_markup=main_menu_kb())
    except Exception:
        pass
    await callback.answer()


# ─── SEVGANIM RASMLARI ───────────────────────────────────────────────────────

@router.callback_query(F.data == "lover:photos")
async def lover_photos(callback: CallbackQuery):
    uid    = callback.from_user.id
    couple = await get_couple(uid)
    if not couple:
        return await callback.answer("Sevgilim yoq.", show_alert=True)
    photos = await get_couple_photos(couple['id'])
    if not photos:
        await safe_edit(
            callback.message,
            "Hozircha rasmlar yoq.\nSevgilim bilan suxbat paytida rasm yuboring.",
            reply_markup=lover_section_kb())
        return
    await safe_edit(callback.message, f"Rasmlar ({len(photos)} ta):")
    for photo in photos:
        try:
            await callback.message.answer_photo(
                photo['file_id'],
                caption=f"Soat: {format_time(photo['sent_at'])}",
                reply_markup=photo_delete_kb(photo['id']))
        except Exception:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("dphoto:"))
async def delete_photo(callback: CallbackQuery):
    pid = int(callback.data.split(':')[1])
    await delete_couple_photo(pid)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer("Rasm ochirildi.")
