from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from config import GIFTS
from constants import ALL_INTERESTS, INTEREST_EMOJIS, interest_label


# ─── REPLY KEYBOARDS ─────────────────────────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="👥 Yangi Dostlar"),
        KeyboardButton(text="❤️ Sevgilim")
    )
    builder.row(
        KeyboardButton(text="👤 Profil"),
        KeyboardButton(text="⏱ Bizning time")
    )
    builder.row(
        KeyboardButton(text="🎁 Sovgalar")
    )
    return builder.as_markup(resize_keyboard=True)


def admin_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📢 Obuna kanal"))
    builder.row(KeyboardButton(text="📣 Reklama yuborish"))
    builder.row(KeyboardButton(text="📊 Statistika"))
    builder.row(KeyboardButton(text="🎁 Sovga buyurtmalari"))
    builder.row(KeyboardButton(text="🏠 Asosiy menyu"))
    return builder.as_markup(resize_keyboard=True)


def end_chat_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🚪 Suxbatni tugatish"))
    return builder.as_markup(resize_keyboard=True)


# ─── INLINE KEYBOARDS ────────────────────────────────────────────────────────

def gender_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👦 Erkak", callback_data="gender:erkak"),
        InlineKeyboardButton(text="👧 Ayol",  callback_data="gender:ayol")
    )
    return builder.as_markup()


def photo_ask_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha",   callback_data="photo:yes"),
        InlineKeyboardButton(text="❌ Yoq", callback_data="photo:no")
    )
    return builder.as_markup()


def new_friends_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔍 Dost qidirish",      callback_data="friends:search"))
    builder.row(InlineKeyboardButton(text="👥 Guruh chat",          callback_data="friends:group"))
    builder.row(InlineKeyboardButton(text="💑 Juft topish",         callback_data="friends:couple"))
    builder.row(InlineKeyboardButton(text="🔎 Qidirish (username)", callback_data="friends:find"))
    return builder.as_markup()


def couple_rating_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha, yoqdi!", callback_data="rating:yes"),
        InlineKeyboardButton(text="❌ Yoq",        callback_data="rating:no")
    )
    return builder.as_markup()


def lover_section_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💖 Sevganim",          callback_data="lover:my"))
    builder.row(InlineKeyboardButton(text="📸 Sevganim rasmlari", callback_data="lover:photos"))
    return builder.as_markup()


def connect_request_kb(request_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Boglanish",    callback_data=f"connect:accept:{request_id}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"connect:reject:{request_id}")
    )
    return builder.as_markup()


def chat_with_lover_kb(to_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💬 Suxbatlashish", callback_data=f"lover:chat:{to_id}")
    )
    return builder.as_markup()


def find_type_kb(target_tg_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💕 Sevgilim bolish", callback_data=f"findtype:couple:{target_tg_id}"),
        InlineKeyboardButton(text="💬 Oddiy suxbat",    callback_data=f"findtype:chat:{target_tg_id}")
    )
    return builder.as_markup()


def find_couple_request_kb(request_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha, qabul qilaman", callback_data=f"fcouple:accept:{request_id}"),
        InlineKeyboardButton(text="❌ Rad etaman",        callback_data=f"fcouple:reject:{request_id}")
    )
    return builder.as_markup()


def profile_edit_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Ism",      callback_data="edit:name"),
        InlineKeyboardButton(text="🖼 Rasm",     callback_data="edit:photo")
    )
    builder.row(
        InlineKeyboardButton(text="🎂 Yosh",     callback_data="edit:age"),
        InlineKeyboardButton(text="⚧ Jins",      callback_data="edit:gender")
    )
    builder.row(
        InlineKeyboardButton(text="🔑 Parol",    callback_data="edit:password"),
        InlineKeyboardButton(text="📛 Username", callback_data="edit:username")
    )
    builder.row(
        InlineKeyboardButton(text="🎙 Ovozli tanishuv", callback_data="edit:voice")
    )
    builder.row(
        InlineKeyboardButton(text="🎯 Qiziqishlarim",   callback_data="edit:interests")
    )
    return builder.as_markup()


def edit_gender_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👦 Erkak", callback_data="editgender:erkak"),
        InlineKeyboardButton(text="👧 Ayol",  callback_data="editgender:ayol")
    )
    return builder.as_markup()


def cancel_edit_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="edit:cancel")
    )
    return builder.as_markup()


def photo_delete_kb(photo_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Ochirish", callback_data=f"dphoto:{photo_id}")
    )
    return builder.as_markup()


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash",   callback_data="broadcast:confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast:cancel")
    )
    return builder.as_markup()


def gifts_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, info in GIFTS.items():
        label = f"{info['emoji']} {info['name']} — {info['price']:,} kumush"
        builder.row(InlineKeyboardButton(text=label, callback_data=f"gift:{key}"))
    return builder.as_markup()


def gift_confirm_kb(gift_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash",   callback_data=f"giftbuy:{gift_key}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="gift:cancel")
    )
    return builder.as_markup()


def interests_kb(selected: list) -> InlineKeyboardMarkup:
    """Qiziqishlar tanlash klaviaturasi."""
    builder = InlineKeyboardBuilder()
    for code, name in ALL_INTERESTS.items():
        emoji = INTEREST_EMOJIS.get(code, "")
        label_text = f"{emoji} {name}"
        is_sel = label_text in selected
        btn_text = f"✅ {label_text}" if is_sel else f"   {label_text}"
        builder.button(text=btn_text, callback_data=f"int:{code}")
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="Saqlash ✔", callback_data="int:save"),
        InlineKeyboardButton(text="Tozalash 🗑", callback_data="int:clear")
    )
    return builder.as_markup()


def admin_gift_confirm_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"giftdone:{order_id}")
    )
    return builder.as_markup()
