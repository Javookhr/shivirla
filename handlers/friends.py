import asyncio
import json
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.filters import StateFilter

from states import ChatState, FindUser
from database import (
    get_user, get_user_by_username,
    join_queue, leave_queue,
    find_match_by_interests, find_group_members,
    create_chat, get_chat_participants, delete_chat,
    find_joinable_group, add_participant_to_chat,
    create_couple_request, get_couple_request, update_request_status,
    create_couple, get_couple,
    add_time, add_coins,
    add_couple_photo
)
from buttons import (
    new_friends_kb, end_chat_kb, couple_rating_kb,
    main_menu_kb, find_type_kb, find_couple_request_kb
)
from utils import (
    start_session, end_session, get_session,
    start_section_timer, stop_section_timer,
    in_search_queue
)
from tasks import cleanup_reminder
from config import MAX_GROUP_SIZE, FIND_REQUEST_TIMEOUT

router = Router()

pending_ratings: dict[int, int] = {}
mutual_yes:      dict[int, int] = {}


def other_fsm(state: FSMContext, bot_id: int, uid: int) -> FSMContext:
    key = StorageKey(bot_id=bot_id, chat_id=uid, user_id=uid)
    return FSMContext(storage=state.storage, key=key)


def get_interests(user: dict) -> list:
    try:
        return json.loads(user.get('interests') or '[]')
    except Exception:
        return []


def common_interests(a: dict, b: dict) -> list:
    return list(set(get_interests(a)) & set(get_interests(b)))


def match_text(user: dict, mtype: str, common: list) -> str:
    emoji = "🎉" if mtype == 'friend' else "💑"
    title = "Yangi dost topildi!" if mtype == 'friend' else "Juft topildi!"
    g     = "Erkak" if user.get('gender') == 'erkak' else "Ayol"
    inter = "  ".join(common) if common else "Yoq"
    return (
        f"{emoji} {title}\n\n"
        f"Ism:  {user.get('name','?')}\n"
        f"Yosh: {user.get('age','?')}\n"
        f"Jins: {g}\n"
        f"Umumiy qiziqishlar: {inter}\n\n"
        "Muloqot qilishingiz mumkun!\n"
        "Rasm, ovoz, video, sticker yubora olasiz."
    )


async def send_match(target, partner: dict, mtype: str,
                     common: list, to_id: int = 0, is_bot: bool = True):
    text = match_text(partner, mtype, common)
    kb   = end_chat_kb()
    if is_bot:
        await target.send_message(to_id, text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)
    if partner.get('voice_intro_id'):
        cap = f"Ovozli tanishuv: {partner.get('name','')}"
        try:
            if is_bot:
                await target.send_voice(to_id, partner['voice_intro_id'], caption=cap)
            else:
                await target.answer_voice(partner['voice_intro_id'], caption=cap)
        except Exception:
            pass


# ─── YANGI DOSTLAR ───────────────────────────────────────────────────────────

@router.message(F.text == "👥 Yangi Dostlar")
async def friends_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Yangi Dostlar\n\nQuyidan birini tanlang:",
                         reply_markup=new_friends_kb())


# ─── DOST QIDIRISH ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "friends:search")
async def cb_friend_search(callback: CallbackQuery, state: FSMContext, bot: Bot):
    uid = callback.from_user.id
    if await get_session(uid):
        return await callback.answer("Siz allaqachon chatdasiz!", show_alert=True)
    if uid in in_search_queue:
        return await callback.answer("Siz allaqachon qidirishdasiz!", show_alert=True)

    me = await get_user(uid)
    if not me:
        return await callback.answer("Avval /start bosing.", show_alert=True)

    mid = await find_match_by_interests('friend', uid, get_interests(me))
    if mid:
        partner = await get_user(mid)
        if not partner:
            await callback.answer()
            return
        await leave_queue(mid)
        in_search_queue.pop(mid, None)
        cleanup_reminder(mid)

        chat_id = await create_chat('friend', [uid, mid])
        common  = common_interests(me, partner)
        await start_session(uid, chat_id, 'friend')
        await start_session(mid, chat_id, 'friend')
        start_section_timer(uid, 'friend')
        start_section_timer(mid, 'friend')
        await state.set_state(ChatState.in_friend_chat)
        await other_fsm(state, bot.id, mid).set_state(ChatState.in_friend_chat)

        await send_match(callback.message, partner, 'friend', common, is_bot=False)
        await send_match(bot, me, 'friend', common, to_id=mid)
    else:
        await join_queue(uid, 'friend')
        in_search_queue[uid] = 'friend'
        start_section_timer(uid, 'friend')
        await callback.message.answer(
            "Dost qidirilmoqda...\n\nBoshqa foydalanuvchi ham qidirishni boshlaguncha kuting.\n"
            "Bekor qilish uchun tugmani bosing.",
            reply_markup=end_chat_kb())
    await callback.answer()


# ─── GURUH CHAT ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "friends:group")
async def cb_group_search(callback: CallbackQuery, state: FSMContext, bot: Bot):
    uid = callback.from_user.id
    if await get_session(uid):
        return await callback.answer("Siz allaqachon chatdasiz!", show_alert=True)
    if uid in in_search_queue:
        return await callback.answer("Siz allaqachon qidirishdasiz!", show_alert=True)

    me = await get_user(uid)
    if not me:
        return await callback.answer("Avval /start bosing.", show_alert=True)

    # 1. Mavjud to'lmagan guruhga qo'shilish
    joinable = await find_joinable_group(MAX_GROUP_SIZE)
    if joinable:
        await add_participant_to_chat(joinable, uid)
        await start_session(uid, joinable, 'group')
        start_section_timer(uid, 'group')
        await state.set_state(ChatState.in_group_chat)

        members = await get_chat_participants(joinable)
        names = []
        for m in members:
            u = await get_user(m)
            if u:
                names.append(f"• {u['name']} ({u['age']})")

        notify = (
            f"{me['name']} guruhga qoshildi!\n\n"
            f"Azolar ({len(members)}):\n" + "\n".join(names)
        )
        for m in members:
            if m != uid:
                try:
                    await bot.send_message(m, notify)
                except Exception:
                    pass

        await callback.message.answer(
            f"Mavjud guruhga qoshildingiz!\n\nAzolar ({len(members)}):\n"
            + "\n".join(names) + "\n\nYozing — hammaga boradi!",
            reply_markup=end_chat_kb())
        await callback.answer()
        return

    # 2. Navbatdan yangi guruh
    await join_queue(uid, 'group')
    in_search_queue[uid] = 'group'
    start_section_timer(uid, 'group')

    members = await find_group_members(uid, MAX_GROUP_SIZE)
    members.append(uid)

    if len(members) >= 2:
        for m in members:
            await leave_queue(m)
            in_search_queue.pop(m, None)
            cleanup_reminder(m)

        chat_id = await create_chat('group', members)
        names = []
        for m in members:
            u = await get_user(m)
            if u:
                names.append(f"• {u['name']} ({u['age']})")
            await start_session(m, chat_id, 'group')
            start_section_timer(m, 'group')
            await other_fsm(state, bot.id, m).set_state(ChatState.in_group_chat)

        intro = (
            f"Guruh chat boshlandi! ({len(members)} kishi)\n\n"
            "Azolar:\n" + "\n".join(names) +
            f"\n\nYozing — hammaga boradi!\nMaksimal {MAX_GROUP_SIZE} kishi."
        )
        for m in members:
            try:
                await bot.send_message(m, intro, reply_markup=end_chat_kb())
            except Exception:
                pass
    else:
        await callback.message.answer(
            f"Guruh chat qidirilmoqda...\n"
            f"Navbatda: {len(members)} kishi (max {MAX_GROUP_SIZE})\n\n"
            "Boshqalar qoshilguncha kuting.",
            reply_markup=end_chat_kb())
    await callback.answer()


# ─── JUFT TOPISH ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "friends:couple")
async def cb_couple_search(callback: CallbackQuery, state: FSMContext, bot: Bot):
    uid = callback.from_user.id
    if await get_session(uid):
        return await callback.answer("Siz allaqachon chatdasiz!", show_alert=True)
    if uid in in_search_queue:
        return await callback.answer("Siz allaqachon qidirishdasiz!", show_alert=True)

    me = await get_user(uid)
    if not me:
        return await callback.answer("Avval /start bosing.", show_alert=True)

    my_gender = me.get('gender', 'erkak')
    opposite  = 'ayol' if my_gender == 'erkak' else 'erkak'

    mid = await find_match_by_interests('couple', uid, get_interests(me),
                                        required_gender=opposite)
    if mid:
        partner = await get_user(mid)
        if not partner:
            await callback.answer()
            return
        await leave_queue(mid)
        in_search_queue.pop(mid, None)
        cleanup_reminder(mid)

        chat_id = await create_chat('couple', [uid, mid])
        common  = common_interests(me, partner)
        await start_session(uid, chat_id, 'couple')
        await start_session(mid, chat_id, 'couple')
        start_section_timer(uid, 'couple')
        start_section_timer(mid, 'couple')
        await state.set_state(ChatState.in_couple_chat)
        await other_fsm(state, bot.id, mid).set_state(ChatState.in_couple_chat)

        await send_match(callback.message, partner, 'couple', common, is_bot=False)
        await send_match(bot, me, 'couple', common, to_id=mid)
    else:
        await join_queue(uid, 'couple', gender=my_gender)
        in_search_queue[uid] = 'couple'
        start_section_timer(uid, 'couple')
        opp_txt = 'Ayol' if my_gender == 'erkak' else 'Erkak'
        await callback.message.answer(
            f"Juft qidirilmoqda... ({opp_txt} izlanmoqda)\n\nTopilguncha kuting.",
            reply_markup=end_chat_kb())
    await callback.answer()


# ─── UNIVERSAL TUGATISH (barcha chat turlari) ────────────────────────────────

@router.message(F.text == "🚪 Suxbatni tugatish")
async def universal_end(message: Message, state: FSMContext, bot: Bot):
    uid     = message.from_user.id
    cur_st  = await state.get_state()
    is_couple = cur_st == ChatState.in_couple_chat.state
    is_lover  = cur_st == ChatState.in_lover_chat.state

    # ── Navbatda kutayotgan ──
    if uid in in_search_queue:
        in_search_queue.pop(uid)
        await leave_queue(uid)
        cleanup_reminder(uid)
        stop_section_timer(uid)
        await state.clear()
        me   = await get_user(uid)
        name = me['name'] if me else "Foydalanuvchi"
        await message.answer(
            f"Qidirish bekor qilindi. Asosiy menyudasiz, {name}.",
            reply_markup=main_menu_kb())
        return

    # ── Aktiv chatda ──
    session = await end_session(uid)
    section, minutes = stop_section_timer(uid)
    if minutes > 0:
        await add_time(uid, section, minutes)
        await add_coins(uid, minutes)

    partner_ids: list[int] = []
    if session:
        try:
            participants = await get_chat_participants(session['chat_id'])
            await delete_chat(session['chat_id'])
        except Exception:
            participants = []
        for p in participants:
            if p == uid:
                continue
            partner_ids.append(p)
            await end_session(p)
            stop_section_timer(p)
            in_search_queue.pop(p, None)
            cleanup_reminder(p)
            try:
                await other_fsm(state, bot.id, p).clear()
            except Exception:
                pass

    await state.clear()
    me   = await get_user(uid)
    name = me['name'] if me else "Foydalanuvchi"

    # ── Sevgilim chati tugadi ──
    if is_lover:
        for p in partner_ids:
            try:
                await bot.send_message(p, "Sevgilim chatdan chiqdi.", reply_markup=main_menu_kb())
            except Exception:
                pass
        await message.answer(f"Chat tugatildi, {name}.", reply_markup=main_menu_kb())
        return

    # ── Juft chati tugadi — reyting so'rovi ──
    if is_couple and partner_ids:
        rating_q = (
            "Suxbat tugadi!\n\n"
            "Sizga bu juft yoqdimi?\n"
            "Ikkingiz ham yoqdi desa — sevgilim bolimiga qoshilasiz!"
        )
        pending_ratings[uid]           = partner_ids[0]
        pending_ratings[partner_ids[0]] = uid
        await message.answer(rating_q, reply_markup=couple_rating_kb())
        for p in partner_ids:
            try:
                await bot.send_message(p, rating_q, reply_markup=couple_rating_kb())
            except Exception:
                pass
        return

    # ── Oddiy dost / guruh chati tugadi ──
    for p in partner_ids:
        try:
            await bot.send_message(p, "Chat tugadi.", reply_markup=main_menu_kb())
        except Exception:
            pass
    await message.answer(
        f"Suxbat tugatildi. Asosiy menyudasiz, {name}.",
        reply_markup=main_menu_kb())


# ─── RATING ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "rating:yes")
async def rating_yes(callback: CallbackQuery, state: FSMContext, bot: Bot):
    uid        = callback.from_user.id
    partner_id = pending_ratings.pop(uid, None)
    try:
        await callback.message.edit_text("Yoqdi deb belgilandi!")
    except Exception:
        pass
    await state.clear()

    if not partner_id:
        await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_kb())
        await callback.answer()
        return

    mutual_yes[uid] = partner_id

    if mutual_yes.get(partner_id) == uid:
        mutual_yes.pop(uid, None)
        mutual_yes.pop(partner_id, None)
        pending_ratings.pop(partner_id, None)
        if not await get_couple(uid):
            await create_couple(uid, partner_id)
        msg = "Tabriklaymiz!\n\nIkkalangiz ham yoqdi! Sevgilim bolimiga qoshildingiz!"
        await callback.message.answer(msg, reply_markup=main_menu_kb())
        try:
            await bot.send_message(partner_id, msg, reply_markup=main_menu_kb())
        except Exception:
            pass
    else:
        await callback.message.answer(
            "Juftingizning javobi kutilmoqda...", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "rating:no")
async def rating_no(callback: CallbackQuery, state: FSMContext, bot: Bot):
    uid        = callback.from_user.id
    partner_id = pending_ratings.pop(uid, None)
    mutual_yes.pop(uid, None)

    if partner_id and mutual_yes.get(partner_id) == uid:
        mutual_yes.pop(partner_id, None)
        pending_ratings.pop(partner_id, None)
        try:
            await bot.send_message(partner_id, "Javob uchun rahmat!", reply_markup=main_menu_kb())
        except Exception:
            pass

    try:
        await callback.message.edit_text("Javobingiz uchun rahmat!")
    except Exception:
        pass
    await state.clear()
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_kb())
    await callback.answer()


# ─── XABAR RELAY ─────────────────────────────────────────────────────────────

@router.message(StateFilter(
    ChatState.in_friend_chat,
    ChatState.in_group_chat,
    ChatState.in_couple_chat,
    ChatState.in_lover_chat
))
async def relay_message(message: Message, bot: Bot):
    uid = message.from_user.id
    session = await get_session(uid)
    if not session:
        return
    sender = await get_user(uid)
    name   = sender['name'] if sender else "Noma'lum"
    try:
        participants = await get_chat_participants(session['chat_id'])
    except Exception:
        return

    # Sevgilim chatida rasm → couple galleryga ham saqlash
    from database import get_couple
    couple = None
    if session.get('type') == 'lover' and message.photo:
        couple = await get_couple(uid)

    for p in participants:
        if p == uid:
            continue
        try:
            await relay_to(bot, p, message, name, couple)
        except Exception:
            pass


async def relay_to(bot: Bot, uid: int, msg: Message, name: str, couple=None):
    h = f"{name}:\n"
    if msg.text:
        await bot.send_message(uid, h + msg.text)
    elif msg.photo:
        fid = msg.photo[-1].file_id
        if couple:
            try:
                await add_couple_photo(couple['id'], uid, fid)
            except Exception:
                pass
        await bot.send_photo(uid, fid, caption=h + "Rasm")
    elif msg.voice:
        await bot.send_voice(uid, msg.voice.file_id, caption=h + "Ovozli xabar")
    elif msg.video:
        await bot.send_video(uid, msg.video.file_id, caption=h + "Video")
    elif msg.video_note:
        await bot.send_message(uid, h + "Video xabar")
        await bot.send_video_note(uid, msg.video_note.file_id)
    elif msg.sticker:
        await bot.send_message(uid, h + "Sticker")
        await bot.send_sticker(uid, msg.sticker.file_id)
    elif msg.document:
        await bot.send_document(uid, msg.document.file_id, caption=h + "Fayl")
    elif msg.audio:
        await bot.send_audio(uid, msg.audio.file_id, caption=h + "Audio")
    elif msg.location:
        await bot.send_message(uid, h + "Joylashuv")
        await bot.send_location(uid, msg.location.latitude, msg.location.longitude)


# ─── USERNAME QIDIRISH ───────────────────────────────────────────────────────

@router.callback_query(F.data == "friends:find")
async def cb_find_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FindUser.username)
    await callback.message.answer(
        "Foydalanuvchi qidirish\n\n"
        "Username kiriting (masalan: Ali_2005 yoki @Ali_2005):")
    await callback.answer()


@router.message(FindUser.username)
async def find_username(message: Message, state: FSMContext):
    username = (message.text or '').strip().lstrip('@')
    if not username:
        return await message.answer("Username kiriting.")
    me = await get_user(message.from_user.id)
    if me and username.lower() == me['username'].lower():
        return await message.answer("Ozingizni qidirib bolmaydi.")
    target = await get_user_by_username(username)
    if not target:
        return await message.answer(f"@{username} topilmadi. Username togri kiritilganini tekshiring.")

    await state.update_data(target_id=target['telegram_id'])
    await state.set_state(FindUser.message_text)

    g         = 'Erkak' if target.get('gender') == 'erkak' else 'Ayol'
    has_voice = bool(target.get('voice_intro_id'))
    inter     = "  ".join(get_interests(target)) or "Yoq"

    await message.answer(
        f"Foydalanuvchi topildi!\n\n"
        f"Ism: {target['name']}\n"
        f"Username: @{target['username']}\n"
        f"Yosh: {target['age']}\n"
        f"Jins: {g}\n"
        f"Ovozli tanishuv: {'Bor' if has_voice else 'Yoq'}\n"
        f"Qiziqishlar: {inter}\n\n"
        "Nima deb yubormoqchisiz? Xabaringizni yozing:")
    if has_voice:
        try:
            await message.answer_voice(target['voice_intro_id'],
                                       caption=f"{target['name']} ning ovozli tanishuvi")
        except Exception:
            pass


@router.message(FindUser.message_text)
async def find_message(message: Message, state: FSMContext):
    text = (message.text or '').strip()
    if not text:
        return await message.answer("Matn kiriting.")
    data   = await state.get_data()
    tid    = data.get('target_id', 0)
    target = await get_user(tid)
    if not target:
        await state.clear()
        return await message.answer("Foydalanuvchi topilmadi.", reply_markup=main_menu_kb())
    await state.update_data(msg_text=text)
    await message.answer(
        f"Kimga: {target['name']} (@{target['username']})\n"
        f"Xabar: {text}\n\n"
        "Qanday yubormoqchisiz?",
        reply_markup=find_type_kb(tid))


@router.callback_query(F.data.startswith("findtype:chat:"))
async def find_send_chat(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data      = await state.get_data()
    target_id = int(callback.data.split(':')[2])
    msg_text  = data.get('msg_text', '')
    await state.clear()
    me     = await get_user(callback.from_user.id)
    target = await get_user(target_id)
    if not me or not target:
        await callback.message.answer("Xatolik yuz berdi.", reply_markup=main_menu_kb())
        await callback.answer()
        return
    try:
        await bot.send_message(
            target_id,
            f"Yangi xabar!\n\nKimdan: {me['name']} (@{me['username']})\nXabar: {msg_text}")
        try:
            await callback.message.edit_text(f"Xabar {target['name']} ga yuborildi!")
        except Exception:
            pass
    except Exception:
        try:
            await callback.message.edit_text("Xabar yuborishda xatolik. Foydalanuvchi botni bloklagan.")
        except Exception:
            pass
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("findtype:couple:"))
async def find_send_couple(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data      = await state.get_data()
    target_id = int(callback.data.split(':')[2])
    msg_text  = data.get('msg_text', '')
    await state.clear()
    from_id = callback.from_user.id
    me      = await get_user(from_id)
    target  = await get_user(target_id)
    if not me or not target:
        await callback.message.answer("Xatolik.", reply_markup=main_menu_kb())
        await callback.answer()
        return
    if await get_couple(from_id):
        try:
            await callback.message.edit_text("Sizda allaqachon sevgilim bor!")
        except Exception:
            pass
        await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_kb())
        await callback.answer()
        return
    rid = await create_couple_request(from_id, target_id)
    try:
        await bot.send_message(
            target_id,
            f"Sevgilim bolish taklifi!\n\n"
            f"{me['name']} (@{me['username']}) sizga murojaat qilmoqda:\n\n"
            f"\"{msg_text}\"\n\n"
            "Bu sorov 12 soat amal qiladi.",
            reply_markup=find_couple_request_kb(rid))
        try:
            await callback.message.edit_text(
                f"Sevgilim bolish taklifi {target['name']} ga yuborildi!\n"
                "12 soat ichida javob kutiladi.")
        except Exception:
            pass
    except Exception:
        try:
            await callback.message.edit_text("Sorov yuborishda xatolik.")
        except Exception:
            pass
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_kb())
    asyncio.create_task(_find_timeout(rid, from_id, bot))
    await callback.answer()


async def _find_timeout(request_id: int, from_id: int, bot: Bot):
    await asyncio.sleep(FIND_REQUEST_TIMEOUT)
    req = await get_couple_request(request_id)
    if req and req['status'] == 'pending':
        await update_request_status(request_id, 'expired')
        try:
            await bot.send_message(
                from_id,
                "Sevgilim bolish taklifingizga 12 soat ichida javob berilmadi. Sorov bekor qilindi.",
                reply_markup=main_menu_kb())
        except Exception:
            pass


@router.callback_query(F.data.startswith("fcouple:accept:"))
async def fcouple_accept(callback: CallbackQuery, bot: Bot):
    rid = int(callback.data.split(':')[2])
    req = await get_couple_request(rid)
    if not req or req['status'] != 'pending':
        return await callback.answer("Sorov muddati otgan.", show_alert=True)
    await update_request_status(rid, 'accepted')
    fid, tid = req['from_id'], req['to_id']
    if await get_couple(fid) or await get_couple(tid):
        try:
            await callback.message.edit_text("Sizdan biri allaqachon juft.")
        except Exception:
            pass
        await callback.answer()
        return
    await create_couple(fid, tid)
    me      = await get_user(tid)
    partner = await get_user(fid)
    me_name = me['name'] if me else "U"
    p_name  = partner['name'] if partner else "U"
    try:
        await callback.message.edit_text(f"Tabriklaymiz! Siz {p_name} ning sevgilisi boldingiz!")
    except Exception:
        pass
    try:
        await bot.send_message(
            fid,
            f"Tabriklaymiz! {me_name} taklifingizni qabul qildi! Sevgilim bolimiga qoshildingiz!",
            reply_markup=main_menu_kb())
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("fcouple:reject:"))
async def fcouple_reject(callback: CallbackQuery, bot: Bot):
    rid = int(callback.data.split(':')[2])
    req = await get_couple_request(rid)
    if not req:
        return await callback.answer()
    await update_request_status(rid, 'rejected')
    try:
        await callback.message.edit_text("Taklif rad etildi.")
    except Exception:
        pass
    to_u = await get_user(req['to_id'])
    n    = to_u['name'] if to_u else "U"
    try:
        await bot.send_message(
            req['from_id'],
            f"{n} sevgilim bolish taklifingizni rad etdi.",
            reply_markup=main_menu_kb())
    except Exception:
        pass
    await callback.answer()
