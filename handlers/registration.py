from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from states import Registration
from database import get_user, create_user, username_exists
from buttons import gender_kb, photo_ask_kb, main_menu_kb, admin_menu_kb
from config import MIN_AGE, MAX_AGE, MIN_PASSWORD_LENGTH, ADMIN_IDS

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    if user_id in ADMIN_IDS:
        user = await get_user(user_id)
        name = user['name'] if user else "Admin"
        await message.answer(
            f"Salom, <b>{name}</b>! Admin paneliga xush kelibsiz.",
            reply_markup=admin_menu_kb(),
            parse_mode='HTML'
        )
        return

    user = await get_user(user_id)
    if user:
        await message.answer(
            f"Xush kelibsiz, <b>{user['name']}</b>! Botga qaytganingizdan xursandmiz!",
            reply_markup=main_menu_kb(),
            parse_mode='HTML'
        )
        return

    await state.set_state(Registration.age)
    await message.answer(
        "Xush kelibsiz!\n\n"
        "Royxatdan otish uchun bir necha savolga javob bering.\n\n"
        f"Yoshingizni kiriting ({MIN_AGE}-{MAX_AGE} orasida):"
    )


@router.message(Registration.age)
async def reg_age(message: Message, state: FSMContext):
    text = (message.text or '').strip()
    if not text.isdigit():
        return await message.answer("Faqat son kiriting.")
    age = int(text)
    if not (MIN_AGE <= age <= MAX_AGE):
        return await message.answer(f"Yosh {MIN_AGE} dan {MAX_AGE} gacha bolishi kerak.")
    await state.update_data(age=age)
    await state.set_state(Registration.name)
    await message.answer("Yaxshi! Ismingizni kiriting:")


@router.message(Registration.name)
async def reg_name(message: Message, state: FSMContext):
    name = (message.text or '').strip()
    if len(name) < 2:
        return await message.answer("Ism kamida 2 ta harf bolishi kerak.")
    await state.update_data(name=name)
    await state.set_state(Registration.username)
    await message.answer("Username kiriting (masalan: Ali_2005):")


@router.message(Registration.username)
async def reg_username(message: Message, state: FSMContext):
    username = (message.text or '').strip().lstrip('@')
    if len(username) < 3:
        return await message.answer("Username kamida 3 ta belgi bolishi kerak.")
    if ' ' in username:
        return await message.answer("Username da bosh joy bolmasligi kerak.")
    if await username_exists(username):
        return await message.answer("Bu username band. Boshqa username kiriting.")
    await state.update_data(username=username)
    await state.set_state(Registration.password)
    await message.answer(
        f"@{username} bosh!\n\n"
        f"Parol kiriting (kamida {MIN_PASSWORD_LENGTH} ta belgi):"
    )


@router.message(Registration.password)
async def reg_password(message: Message, state: FSMContext):
    pwd = message.text or ''
    if len(pwd) < MIN_PASSWORD_LENGTH:
        return await message.answer(
            f"Parol kamida {MIN_PASSWORD_LENGTH} ta belgi bolishi kerak."
        )
    await state.update_data(password=pwd)
    await state.set_state(Registration.password_confirm)
    await message.answer("Parolni qayta kiriting:")


@router.message(Registration.password_confirm)
async def reg_password_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    if message.text != data['password']:
        return await message.answer("Parollar mos kelmadi. Qaytadan kiriting:")
    await state.set_state(Registration.gender)
    await message.answer("Parol saqlandi!\n\nJinsingizni tanlang:", reply_markup=gender_kb())


@router.callback_query(Registration.gender, F.data.startswith('gender:'))
async def reg_gender(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.split(':')[1]
    await state.update_data(gender=gender)
    label = "Erkak" if gender == 'erkak' else "Ayol"
    try:
        await callback.message.edit_text(
            f"{label} tanlandi.\n\nProfilingizga rasm qoyasizmi?",
            reply_markup=photo_ask_kb()
        )
    except Exception:
        await callback.message.answer(
            "Profilingizga rasm qoyasizmi?", reply_markup=photo_ask_kb()
        )
    await state.set_state(Registration.photo)
    await callback.answer()


@router.callback_query(Registration.photo, F.data == 'photo:no')
async def reg_photo_skip(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ok = await create_user(
        telegram_id=callback.from_user.id,
        name=data['name'], username=data['username'],
        password=data['password'], age=data['age'],
        gender=data['gender'], photo_id=None
    )
    await state.clear()
    if ok:
        await callback.message.answer(
            f"Malumotlar tasdiqlandi! Xush kelibsiz, <b>{data['name']}</b>!",
            reply_markup=main_menu_kb(), parse_mode='HTML'
        )
    else:
        await callback.message.answer("Xatolik yuz berdi. /start bosing.")
    await callback.answer()


@router.callback_query(Registration.photo, F.data == 'photo:yes')
async def reg_photo_ask(callback: CallbackQuery):
    try:
        await callback.message.edit_text("Rasmingizni yuboring:")
    except Exception:
        await callback.message.answer("Rasmingizni yuboring:")
    await callback.answer()


@router.message(Registration.photo, F.photo)
async def reg_photo_save(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    ok = await create_user(
        telegram_id=message.from_user.id,
        name=data['name'], username=data['username'],
        password=data['password'], age=data['age'],
        gender=data['gender'], photo_id=photo_id
    )
    await state.clear()
    if ok:
        await message.answer(
            f"Malumotlar tasdiqlandi! Xush kelibsiz, <b>{data['name']}</b>!",
            reply_markup=main_menu_kb(), parse_mode='HTML'
        )
    else:
        await message.answer("Xatolik yuz berdi. /start bosing.")


@router.message(Registration.photo)
async def reg_photo_wrong(message: Message):
    await message.answer("Iltimos, rasm yuboring.")
