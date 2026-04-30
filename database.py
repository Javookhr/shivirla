import json
import aiosqlite
import hashlib
from datetime import datetime, date
from typing import Optional
from config import DB_NAME


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                photo_id TEXT,
                voice_intro_id TEXT,
                interests TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now')),
                is_active INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT NOT NULL,
                channel_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS friend_queue (
                user_id INTEGER PRIMARY KEY,
                type TEXT NOT NULL,
                gender TEXT,
                joined_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS active_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS chat_participants (
                chat_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (chat_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS couple_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id INTEGER NOT NULL,
                to_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS couples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS couple_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                couple_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                sent_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS user_time (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                section TEXT NOT NULL,
                minutes INTEGER DEFAULT 0,
                log_date TEXT NOT NULL,
                UNIQUE(user_id, section, log_date)
            );
            CREATE TABLE IF NOT EXISTS coins (
                user_id INTEGER PRIMARY KEY,
                amount INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS gift_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                gift_key TEXT NOT NULL,
                gift_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        # Migrations for existing DBs
        for col, defval in [
            ("voice_intro_id", "TEXT"),
            ("interests", "TEXT DEFAULT '[]'"),
        ]:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {defval}")
            except Exception:
                pass
        await db.commit()


# ─── USERS ───────────────────────────────────────────────────────────────────

async def create_user(telegram_id: int, name: str, username: str,
                      password: str, age: int, gender: str,
                      photo_id: Optional[str]) -> bool:
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT INTO users (telegram_id,name,username,password,age,gender,photo_id) "
                "VALUES (?,?,?,?,?,?,?)",
                (telegram_id, name, username, hash_password(password), age, gender, photo_id)
            )
            await db.execute("INSERT OR IGNORE INTO coins(user_id,amount) VALUES(?,0)", (telegram_id,))
            await db.commit()
        return True
    except Exception:
        return False


async def get_user(telegram_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_by_username(username: str) -> Optional[dict]:
    clean = username.lstrip('@').lower()
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE LOWER(username)=?", (clean,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def username_exists(username: str) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE LOWER(username)=?", (username.lower(),)
        ) as cur:
            return await cur.fetchone() is not None


async def update_user_field(telegram_id: int, field: str, value) -> bool:
    allowed = {'name', 'username', 'password', 'age', 'gender',
               'photo_id', 'voice_intro_id', 'interests'}
    if field not in allowed:
        return False
    if field == 'password':
        value = hash_password(value)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE users SET {field}=? WHERE telegram_id=?", (value, telegram_id))
        await db.commit()
    return True


async def get_all_users() -> list[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_user_count() -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            return (await cur.fetchone())[0]


async def get_monthly_new_users() -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        month = datetime.now().strftime('%Y-%m')
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at LIKE ?", (f"{month}%",)
        ) as cur:
            return (await cur.fetchone())[0]


async def get_leaderboard(limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT u.name, u.username, c.amount FROM coins c "
            "JOIN users u ON u.telegram_id=c.user_id ORDER BY c.amount DESC LIMIT ?", (limit,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_user_rank(user_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT COUNT(*)+1 FROM coins WHERE amount > "
            "(SELECT COALESCE(amount,0) FROM coins WHERE user_id=?)", (user_id,)
        ) as cur:
            return (await cur.fetchone())[0]


# ─── CHANNELS ────────────────────────────────────────────────────────────────

async def add_channel(name: str, username: str, channel_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO channels(name,username,channel_id) VALUES(?,?,?)",
            (name, username, channel_id)
        )
        await db.commit()


async def get_channels() -> list[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM channels") as cur:
            return [dict(r) for r in await cur.fetchall()]


# ─── QUEUE ───────────────────────────────────────────────────────────────────

async def join_queue(user_id: int, queue_type: str, gender: Optional[str] = None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO friend_queue(user_id,type,gender) VALUES(?,?,?)",
            (user_id, queue_type, gender)
        )
        await db.commit()


async def leave_queue(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM friend_queue WHERE user_id=?", (user_id,))
        await db.commit()


async def get_all_queue_users() -> list[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM friend_queue") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def find_match(queue_type: str, exclude_id: int,
                     required_gender: Optional[str] = None) -> Optional[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        if required_gender:
            async with db.execute(
                "SELECT user_id FROM friend_queue WHERE type=? AND user_id!=? AND gender=? "
                "ORDER BY joined_at LIMIT 1",
                (queue_type, exclude_id, required_gender)
            ) as cur:
                row = await cur.fetchone()
        else:
            async with db.execute(
                "SELECT user_id FROM friend_queue WHERE type=? AND user_id!=? "
                "ORDER BY joined_at LIMIT 1",
                (queue_type, exclude_id)
            ) as cur:
                row = await cur.fetchone()
        return row[0] if row else None


async def find_match_by_interests(
    queue_type: str, exclude_id: int,
    my_interests: list,
    required_gender: Optional[str] = None
) -> Optional[int]:
    gender_clause = "AND fq.gender=?" if required_gender else ""
    params: list = [queue_type, exclude_id]
    if required_gender:
        params.append(required_gender)

    async with aiosqlite.connect(DB_NAME) as db:
        if my_interests:
            async with db.execute(
                f"SELECT fq.user_id, u.interests FROM friend_queue fq "
                f"JOIN users u ON u.telegram_id=fq.user_id "
                f"WHERE fq.type=? AND fq.user_id!=? {gender_clause} "
                f"ORDER BY fq.joined_at",
                params
            ) as cur:
                rows = await cur.fetchall()

            my_set = set(my_interests)
            best_id: Optional[int] = None
            best_score = 0
            for row in rows:
                uid, interests_json = row
                try:
                    their = set(json.loads(interests_json or '[]'))
                except Exception:
                    their = set()
                score = len(my_set & their)
                if score > best_score:
                    best_score = score
                    best_id = uid
            if best_id:
                return best_id

        async with db.execute(
            f"SELECT user_id FROM friend_queue WHERE type=? AND user_id!=? {gender_clause} "
            f"ORDER BY joined_at LIMIT 1",
            params
        ) as cur:
            row = await cur.fetchone()
        return row[0] if row else None


async def find_group_members(exclude_id: int, max_size: int) -> list[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id FROM friend_queue WHERE type='group' AND user_id!=? "
            "ORDER BY joined_at LIMIT ?",
            (exclude_id, max_size - 1)
        ) as cur:
            rows = await cur.fetchall()
        return [r[0] for r in rows]


# ─── CHATS ───────────────────────────────────────────────────────────────────

async def create_chat(chat_type: str, participants: list[int]) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("INSERT INTO active_chats(type) VALUES(?)", (chat_type,))
        chat_id = cur.lastrowid
        for uid in participants:
            await db.execute(
                "INSERT INTO chat_participants(chat_id,user_id) VALUES(?,?)", (chat_id, uid)
            )
        await db.commit()
    return chat_id


async def get_chat_participants(chat_id: int) -> list[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id FROM chat_participants WHERE chat_id=?", (chat_id,)
        ) as cur:
            return [r[0] for r in await cur.fetchall()]


async def find_joinable_group(max_size: int) -> Optional[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT ac.id, COUNT(cp.user_id) as cnt FROM active_chats ac "
            "JOIN chat_participants cp ON cp.chat_id=ac.id "
            "WHERE ac.type='group' GROUP BY ac.id HAVING cnt < ? "
            "ORDER BY ac.created_at LIMIT 1",
            (max_size,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def add_participant_to_chat(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO chat_participants(chat_id,user_id) VALUES(?,?)",
            (chat_id, user_id)
        )
        await db.commit()


async def delete_chat(chat_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM chat_participants WHERE chat_id=?", (chat_id,))
        await db.execute("DELETE FROM active_chats WHERE id=?", (chat_id,))
        await db.commit()


# ─── COUPLES ─────────────────────────────────────────────────────────────────

async def create_couple_request(from_id: int, to_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "INSERT INTO couple_requests(from_id,to_id) VALUES(?,?)", (from_id, to_id)
        )
        await db.commit()
        return cur.lastrowid


async def get_couple_request(request_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM couple_requests WHERE id=?", (request_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_request_status(request_id: int, status: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE couple_requests SET status=? WHERE id=?", (status, request_id)
        )
        await db.commit()


async def create_couple(user1_id: int, user2_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "INSERT INTO couples(user1_id,user2_id) VALUES(?,?)", (user1_id, user2_id)
        )
        await db.commit()
        return cur.lastrowid


async def get_couple(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM couples WHERE user1_id=? OR user2_id=?", (user_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_partner_id(user_id: int) -> Optional[int]:
    couple = await get_couple(user_id)
    if not couple:
        return None
    return couple['user2_id'] if couple['user1_id'] == user_id else couple['user1_id']


async def get_couple_count() -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM couples") as cur:
            return (await cur.fetchone())[0]


async def add_couple_photo(couple_id: int, sender_id: int, file_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO couple_photos(couple_id,sender_id,file_id) VALUES(?,?,?)",
            (couple_id, sender_id, file_id)
        )
        await db.commit()


async def get_couple_photos(couple_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM couple_photos WHERE couple_id=? ORDER BY sent_at DESC",
            (couple_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def delete_couple_photo(photo_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM couple_photos WHERE id=?", (photo_id,))
        await db.commit()


# ─── COINS & TIME ────────────────────────────────────────────────────────────

async def get_coins(user_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT amount FROM coins WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def add_coins(user_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO coins(user_id,amount) VALUES(?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET amount=amount+?",
            (user_id, amount, amount)
        )
        await db.commit()


async def deduct_coins(user_id: int, amount: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT amount FROM coins WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row or row[0] < amount:
            return False
        await db.execute(
            "UPDATE coins SET amount=amount-? WHERE user_id=?", (amount, user_id)
        )
        await db.commit()
        return True


async def add_time(user_id: int, section: str, minutes: int):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO user_time(user_id,section,minutes,log_date) VALUES(?,?,?,?) "
            "ON CONFLICT(user_id,section,log_date) DO UPDATE SET minutes=minutes+excluded.minutes",
            (user_id, section, minutes, today)
        )
        await db.commit()


async def get_today_time(user_id: int) -> dict:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT section, SUM(minutes) as total FROM user_time "
            "WHERE user_id=? AND log_date=? GROUP BY section",
            (user_id, today)
        ) as cur:
            rows = await cur.fetchall()
        async with db.execute(
            "SELECT SUM(minutes) FROM user_time WHERE user_id=? AND log_date=?",
            (user_id, today)
        ) as cur:
            total_row = await cur.fetchone()
    return {
        'sections': {r[0]: r[1] for r in rows},
        'total': total_row[0] or 0
    }


# ─── GIFT ORDERS ─────────────────────────────────────────────────────────────

async def create_gift_order(user_id: int, gift_key: str,
                            gift_name: str, price: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "INSERT INTO gift_orders(user_id,gift_key,gift_name,price) VALUES(?,?,?,?)",
            (user_id, gift_key, gift_name, price)
        )
        await db.commit()
        return cur.lastrowid


async def complete_gift_order(order_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE gift_orders SET status='completed' WHERE id=?", (order_id,)
        )
        await db.commit()


async def get_pending_gifts() -> list[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT go.*, u.name, u.username FROM gift_orders go "
            "JOIN users u ON u.telegram_id=go.user_id "
            "WHERE go.status='pending' ORDER BY go.created_at"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]
