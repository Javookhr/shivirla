from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import get_user, get_coins, deduct_coins, create_gift_order, complete_gift_order
from buttons import gifts_kb, gift_confirm_kb, main_menu_kb, admin_gift_confirm_kb
from config import GIFTS, ADMIN_IDS

router = Router()


@router.message(F.text == "🎁 Sovgalar")
async def gifts_menu(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    coins = await get_coins(user_id)
    await message.answer(
        f"Sovgalar\n\n"
        f"Sizning kumushingiz: {coins:,} ta\n\n"
        f"Har 10 daqiqada bot ishlatganingiz uchun {5} ta kumush beriladi.\n\n"
        "Quyidagi sovgalardan birini tanlang:",
        reply_markup=gifts_kb()
    )


@router.callback_query(F.data.startswith("gift:") & ~F.data.startswith("giftbuy:") & ~F.data.startswith("giftdone:"))
async def gift_select(callback: CallbackQuery):
    action = callback.data[5:]
    if action == 'cancel':
        try:
            await callback.message.edit_text("Bekor qilindi.")
        except Exception:
            pass
        await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_kb())
        await callback.answer()
        return

    gift_key = action
    gift = GIFTS.get(gift_key)
    if not gift:
        return await callback.answer()

    user_id = callback.from_user.id
    coins = await get_coins(user_id)

    if coins < gift['price']:
        needed = gift['price'] - coins
        await callback.answer(
            f"Yetarli kumush yoq!\nSizda: {coins:,} ta\nKerak: {gift['price']:,} ta\nYetishmaydi: {needed:,} ta",
            show_alert=True
        )
        return

    try:
        await callback.message.edit_text(
            f"Tasdiqlash\n\n"
            f"Sovga: {gift['emoji']} {gift['name']}\n"
            f"Narx: {gift['price']:,} kumush\n"
            f"Sizda: {coins:,} kumush\n\n"
            "Tasdiqlaysizmi?",
            reply_markup=gift_confirm_kb(gift_key)
        )
    except Exception:
        await callback.message.answer(
            f"Tasdiqlash\n\n"
            f"Sovga: {gift['emoji']} {gift['name']}\n"
            f"Narx: {gift['price']:,} kumush\n\n"
            "Tasdiqlaysizmi?",
            reply_markup=gift_confirm_kb(gift_key)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("giftbuy:"))
async def gift_buy(callback: CallbackQuery, bot: Bot):
    gift_key = callback.data[8:]
    gift = GIFTS.get(gift_key)
    if not gift:
        return await callback.answer()

    user_id = callback.from_user.id
    success = await deduct_coins(user_id, gift['price'])

    if not success:
        await callback.answer("Yetarli kumush yoq!", show_alert=True)
        return

    order_id = await create_gift_order(user_id, gift_key, gift['name'], gift['price'])
    remaining = await get_coins(user_id)
    user = await get_user(user_id)

    try:
        await callback.message.edit_text(
            f"Buyurtma qabul qilindi!\n\n"
            f"Sovga: {gift['emoji']} {gift['name']}\n"
            f"Buyurtma #{order_id}\n\n"
            f"Qolgan kumush: {remaining:,} ta\n\n"
            "Admin 24 soat ichida qayta ishlaydi va sovga yuboriladi."
        )
    except Exception:
        pass
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_kb())

    # Admin ga xabar
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"Yangi sovga buyurtmasi!\n\n"
                f"Buyurtma #{order_id}\n"
                f"Foydalanuvchi: {user['name']} (@{user['username']})\n"
                f"Telegram ID: {user_id}\n"
                f"Sovga: {gift['emoji']} {gift['name']}\n"
                f"Narx: {gift['price']:,} kumush",
                reply_markup=admin_gift_confirm_kb(order_id)
            )
        except Exception:
            pass
    await callback.answer("Buyurtma qabul qilindi!")


@router.callback_query(F.data.startswith("giftdone:"))
async def gift_done(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("Ruxsat yoq.", show_alert=True)
    order_id = int(callback.data[9:])
    await complete_gift_order(order_id)
    try:
        await callback.message.edit_text(
            callback.message.text + "\n\nSATUS: Bajarildi"
        )
    except Exception:
        pass
    await callback.answer("Bajarildi deb belgilandi!")
