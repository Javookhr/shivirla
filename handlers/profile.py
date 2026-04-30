import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import EditProfile
from database import get_user, update_user_field, username_exists, get_coins, get_user_rank
from buttons import main_menu_kb, profile_edit_kb, edit_gender_kb, cancel_edit_kb
from utils import format_time, safe_edit
from config import MIN_AGE, MAX_AGE, MIN_PASSWORD_LENGTH

router = Router()


async def show_profile(event, user_id: int):
    user = await get_user(user_id)
    if not user:
        return
    coins = await get_coins(user_id)
    rank = await get_user_rank(user_id)
    has_voice = bool(user.get('voice_intro_id'))
    try:
        interests = json.loads(user.get('interests') or '[]')
    except Exception:
        interests = []
    inter_text = "  ".join(interests) if interests else "Tanlanmagan"

    text = (
        f"Profil\n\n"
        f"Ism: {user['name']}\n"
        f"Username: @{user['username']}\n"
        f"Yosh: {user['age']}\n"
        f"Jins: {'Erkak' if user['gender'] == 'erkak' else 'Ayol'}\n"
        f"Ovozli tanishuv: {'Bor' if has_voice else 'Yoq'}\n"
        f"Qiziqishlar: {inter_text}\n"
        f"Kumush: {coins:,} ta\n"
        f"Reyting: {rank}-orin\n"
        f"Royxatdan: {format_time(user['created_at'])}\n"
    )
    markup = profile_edit_kb()

    if isinstance(event, Message):
        if user.get('photo_id'):
            await event.answer_photo(user['photo_id'], caption=text, reply_markup=markup)
        else:
            await event.answer(text, reply_markup=markup)
    else:
        try:
            await event.message.delete()
        except Exception:
            pass
        if user.get('photo_id'):
            await event.message.answer_photo(user['photo_id'], caption=text, reply_markup=markup)
        else:
            await event.message.answer(text, reply_markup=markup)
        await event.answer()


@router.message(F.text == "👤 Profil")
async def profile_menu(message: Message, state: FSMContext):
    await state.clear()
    await show_profile(message, message.from_user.id)


@router.callback_query(F.data == "edit:name")
async def edit_name_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditProfile.name)
    await safe_edit(callback.message, "Yangi ismingizni kiriting:", reply_markup=cancel_edit_kb())
    await callback.answer()


@router.message(EditProfile.name)
async def edit_name_save(message: Message, state: FSMContext):
    name = (message.text or '').strip()
    if len(name) < 2:
        return await message.answer("Ism kamida 2 ta harf bolishi kerak.")
    await update_user_field(message.from_user.id, 'name', name)
    await state.clear()
    await message.answer("Ism ozgartirildi!", reply_markup=main_menu_kb())


@router.callback_query(F.data == "edit:username")
async def edit_username_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditProfile.username)
    await safe_edit(callback.message, "Yangi username kiriting:", reply_markup=cancel_edit_kb())
    await callback.answer()


@router.message(EditProfile.username)
async def edit_username_save(message: Message, state: FSMContext):
    username = (message.text or '').strip().lstrip('@')
    if len(username) < 3 or ' ' in username:
        return await message.answer("Username notogri (min 3 belgi, bosh joy yoq).")
    if await username_exists(username):
        user = await get_user(message.from_user.id)
        if user['username'].lower() != username.lower():
            return await message.answer("Bu username band.")
    await update_user_field(message.from_user.id, 'username', username)
    await state.clear()
    await message.answer("Username ozgartirildi!", reply_markup=main_menu_kb())


@router.callback_query(F.data == "edit:password")
async def edit_password_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditProfile.password)
    await safe_edit(
        callback.message,
        f"Yangi parol kiriting (kamida {MIN_PASSWORD_LENGTH} ta belgi):",
        reply_markup=cancel_edit_kb()
    )
    await callback.answer()


@router.message(EditProfile.password)
async def edit_password_save(message: Message, state: FSMContext):
    pwd = message.text or ''
    if len(pwd) < MIN_PASSWORD_LENGTH:
        return await message.answer(f"Parol kamida {MIN_PASSWORD_LENGTH} ta belgi bolishi kerak.")
    await state.update_data(new_password=pwd)
    await state.set_state(EditProfile.password_confirm)
    await message.answer("Parolni qayta kiriting:")


@router.message(EditProfile.password_confirm)
async def edit_password_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    if message.text != data.get('new_password'):
        return await message.answer("Parollar mos kelmadi. Qaytadan kiriting:")
    await update_user_field(message.from_user.id, 'password', data['new_password'])
    await state.clear()
    await message.answer("Parol ozgartirildi!", reply_markup=main_menu_kb())


@router.callback_query(F.data == "edit:age")
async def edit_age_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditProfile.age)
    await safe_edit(
        callback.message,
        f"Yangi yoshingizni kiriting ({MIN_AGE}-{MAX_AGE}):",
        reply_markup=cancel_edit_kb()
    )
    await callback.answer()


@router.message(EditProfile.age)
async def edit_age_save(message: Message, state: FSMContext):
    text = (message.text or '').strip()
    if not text.isdigit():
        return await message.answer("Faqat son kiriting.")
    age = int(text)
    if not (MIN_AGE <= age <= MAX_AGE):
        return await message.answer(f"Yosh {MIN_AGE}-{MAX_AGE} orasida bolishi kerak.")
    await update_user_field(message.from_user.id, 'age', age)
    await state.clear()
    await message.answer("Yosh ozgartirildi!", reply_markup=main_menu_kb())


@router.callback_query(F.data == "edit:gender")
async def edit_gender_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditProfile.gender)
    await safe_edit(callback.message, "Yangi jinsingizni tanlang:", reply_markup=edit_gender_kb())
    await callback.answer()


@router.callback_query(EditProfile.gender, F.data.startswith("editgender:"))
async def edit_gender_save(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.split(':')[1]
    await update_user_field(callback.from_user.id, 'gender', gender)
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("Jins ozgartirildi!", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "edit:photo")
async def edit_photo_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditProfile.photo)
    await safe_edit(callback.message, "Yangi rasmingizni yuboring:", reply_markup=cancel_edit_kb())
    await callback.answer()


@router.message(EditProfile.photo, F.photo)
async def edit_photo_save(message: Message, state: FSMContext):
    await update_user_field(message.from_user.id, 'photo_id', message.photo[-1].file_id)
    await state.clear()
    await message.answer("Rasm ozgartirildi!", reply_markup=main_menu_kb())


@router.message(EditProfile.photo)
async def edit_photo_wrong(message: Message):
    await message.answer("Iltimos, rasm yuboring.")
