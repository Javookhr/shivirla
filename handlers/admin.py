from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from states import AdminState
from database import (
    add_channel, get_channels, get_user,
    get_user_count, get_monthly_new_users, get_couple_count,
    get_all_users, get_pending_gifts, complete_gift_order
)
from buttons import admin_menu_kb, main_menu_kb, broadcast_confirm_kb
from config import ADMIN_IDS

router = Router()
pending_broadcasts: dict[int, dict] = {}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command('admin'))
async def admin_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Admin panel:", reply_markup=admin_menu_kb())


@router.message(F.text == "🏠 Asosiy menyu")
async def admin_back(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Asosiy menyu:", reply_markup=main_menu_kb())


@router.message(F.text == "📢 Obuna kanal")
async def channel_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    channels = await get_channels()
    info = ""
    if channels:
        info = "\n\nMavjud kanallar:\n"
        for ch in channels:
            info += f"• {ch['name']} (@{ch['username']})\n"
    await state.set_state(AdminState.channel_name)
    await message.answer(f"Yangi kanal qoshish{info}\n\nKanal nomini kiriting:")


@router.message(AdminState.channel_name)
async def channel_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(ch_name=message.text)
    await state.set_state(AdminState.channel_username)
    await message.answer("Kanal @username sini kiriting:")


@router.message(AdminState.channel_username)
async def channel_username_step(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    username = (message.text or '').replace('@', '').strip()
    await state.update_data(ch_username=username)
    await state.set_state(AdminState.channel_id)
    await message.answer("Kanal ID sini kiriting (masalan: -1001234567890):")


@router.message(AdminState.channel_id)
async def channel_id_check(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    channel_id = (message.text or '').strip()
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(channel_id, me.id)
        if member.status not in ('administrator', 'creator'):
            await message.answer("Bot kanalda admin emas! Admin qiling va qaytadan urinib koring.")
            await state.clear()
            await message.answer("Admin panel:", reply_markup=admin_menu_kb())
            return
    except Exception:
        await message.answer("Kanal topilmadi yoki bot kanalda emas.")
        await state.clear()
        await message.answer("Admin panel:", reply_markup=admin_menu_kb())
        return
    await add_channel(data['ch_name'], data['ch_username'], channel_id)
    await state.clear()
    await message.answer(
        f"Kanal qoshildi!\n{data['ch_name']} (@{data['ch_username']})",
        reply_markup=admin_menu_kb()
    )


@router.message(F.text == "📣 Reklama yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminState.broadcast_content)
    await message.answer("Reklama xabarini yuboring (rasm, matn yoki ikkalasi):")


@router.message(AdminState.broadcast_content)
async def broadcast_preview(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    pending_broadcasts[message.from_user.id] = {
        'text': message.text or message.caption,
        'photo_id': message.photo[-1].file_id if message.photo else None,
    }
    await state.set_state(AdminState.broadcast_confirm)
    preview = "Korinis:\n\n" + (message.text or message.caption or '')
    if message.photo:
        await message.answer(preview, reply_markup=broadcast_confirm_kb())
    else:
        await message.answer(preview, reply_markup=broadcast_confirm_kb())


@router.callback_query(AdminState.broadcast_confirm, F.data == "broadcast:confirm")
async def broadcast_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    data = pending_broadcasts.pop(callback.from_user.id, None)
    await state.clear()
    if not data:
        return await callback.answer("Malumot topilmadi.", show_alert=True)
    users = await get_all_users()
    sent = failed = 0
    try:
        await callback.message.edit_text("Reklama yuborilmoqda...")
    except Exception:
        pass
    for user in users:
        uid = user['telegram_id']
        try:
            if data['photo_id']:
                await bot.send_photo(uid, data['photo_id'], caption=data.get('text') or '')
            else:
                await bot.send_message(uid, data.get('text') or '')
            sent += 1
        except Exception:
            failed += 1
    await callback.message.answer(
        f"Reklama yuborildi!\n\nYuborildi: {sent} ta\nYuborilmadi: {failed} ta",
        reply_markup=admin_menu_kb()
    )
    await callback.answer()


@router.callback_query(AdminState.broadcast_confirm, F.data == "broadcast:cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    pending_broadcasts.pop(callback.from_user.id, None)
    await state.clear()
    try:
        await callback.message.edit_text("Reklama bekor qilindi.")
    except Exception:
        pass
    await callback.message.answer("Admin panel:", reply_markup=admin_menu_kb())
    await callback.answer()


@router.message(F.text == "📊 Statistika")
async def statistics(message: Message):
    if not is_admin(message.from_user.id):
        return
    total = await get_user_count()
    this_month = await get_monthly_new_users()
    couples = await get_couple_count()
    channels = await get_channels()
    pending = await get_pending_gifts()
    await message.answer(
        f"Bot statistikasi\n\n"
        f"Jami foydalanuvchilar: {total}\n"
        f"Bu oy yangi: {this_month}\n"
        f"Juftlar (sevgilimlar): {couples}\n"
        f"Kanallar: {len(channels)} ta\n"
        f"Kutilayotgan sovga buyurtmalari: {len(pending)} ta",
        reply_markup=admin_menu_kb()
    )


@router.message(F.text == "🎁 Sovga buyurtmalari")
async def gift_orders(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    pending = await get_pending_gifts()
    if not pending:
        await message.answer("Kutilayotgan buyurtmalar yoq.", reply_markup=admin_menu_kb())
        return
    from buttons import admin_gift_confirm_kb
    await message.answer(f"Kutilayotgan buyurtmalar: {len(pending)} ta")
    for order in pending:
        await message.answer(
            f"Buyurtma #{order['id']}\n"
            f"Foydalanuvchi: {order['name']} (@{order['username']})\n"
            f"Telegram ID: {order['user_id']}\n"
            f"Sovga: {order['gift_name']}\n"
            f"Narx: {order['price']:,} kumush\n"
            f"Sana: {order['created_at'][:16]}",
            reply_markup=admin_gift_confirm_kb(order['id'])
        )
