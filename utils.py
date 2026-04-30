import asyncio
from datetime import datetime
from typing import Optional
from aiogram import Bot
from database import get_channels


# ─── ACTIVE SESSIONS ─────────────────────────────────────────────────────────
# user_id -> {'chat_id': int, 'type': str, 'started_at': datetime}
active_sessions: dict[int, dict] = {}

# user_id -> {'section': str, 'started': datetime}
section_timers: dict[int, dict] = {}

# user_id -> queue_type  (in queue, not yet matched)
in_search_queue: dict[int, str] = {}

_lock = asyncio.Lock()


async def start_session(user_id: int, chat_id: int, chat_type: str):
    async with _lock:
        active_sessions[user_id] = {
            'chat_id': chat_id,
            'type': chat_type,
            'started_at': datetime.now()
        }


async def end_session(user_id: int) -> Optional[dict]:
    async with _lock:
        return active_sessions.pop(user_id, None)


async def get_session(user_id: int) -> Optional[dict]:
    return active_sessions.get(user_id)


def start_section_timer(user_id: int, section: str):
    section_timers[user_id] = {'section': section, 'started': datetime.now()}


def stop_section_timer(user_id: int) -> tuple[str, int]:
    data = section_timers.pop(user_id, None)
    if not data:
        return ('unknown', 0)
    elapsed = (datetime.now() - data['started']).seconds // 60
    return (data['section'], elapsed)


# ─── SUBSCRIPTION CHECK ───────────────────────────────────────────────────────

async def check_subscriptions(bot: Bot, user_id: int) -> list[dict]:
    channels = await get_channels()
    not_subscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch['channel_id'], user_id)
            if member.status in ('left', 'kicked', 'banned'):
                not_subscribed.append(ch)
        except Exception:
            not_subscribed.append(ch)
    return not_subscribed


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def format_minutes(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    if h:
        return f"{h} soat {m} daqiqa"
    return f"{m} daqiqa"


def format_time(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return dt_str


async def safe_edit(msg, text: str, **kwargs):
    """Edit text safely — delete+answer if message has no text (e.g. photo)."""
    try:
        await msg.edit_text(text, **kwargs)
    except Exception:
        try:
            await msg.delete()
        except Exception:
            pass
        await msg.answer(text, **kwargs)


SECTION_NAMES = {
    'friend': 'Dost qidirish',
    'group':  'Guruh chat',
    'couple': 'Juft topish',
    'lover':  'Sevgilim chat',
}
