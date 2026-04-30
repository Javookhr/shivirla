# Circular import muammosini hal qilish uchun
# Bu fayl hech qanday aiogram import qilmaydi

ALL_INTERESTS: dict[str, str] = {
    "M": "Musiqa",
    "S": "Sport",
    "G": "Oyinlar",
    "K": "Kino",
    "B": "Kitob",
    "T": "Sayohat",
    "O": "Oshpazlik",
    "A": "Sanat",
    "C": "Texnologiya",
    "P": "Fotografiya",
    "F": "Fitnes",
    "E": "Teatr",
    "N": "Tabiat",
    "L": "Mantiqiy oyinlar",
    "D": "Raqslar",
    "H": "Hayvonlar",
}

INTEREST_EMOJIS: dict[str, str] = {
    "M": "🎵",
    "S": "⚽",
    "G": "🎮",
    "K": "🎬",
    "B": "📚",
    "T": "✈",
    "O": "🍳",
    "A": "🎨",
    "C": "💻",
    "P": "📸",
    "F": "🏋",
    "E": "🎭",
    "N": "🌿",
    "L": "🧩",
    "D": "💃",
    "H": "🐾",
}


def interest_label(code: str) -> str:
    """Return 'emoji name' for display."""
    emoji = INTEREST_EMOJIS.get(code, "•")
    name = ALL_INTERESTS.get(code, code)
    return f"{emoji} {name}"
