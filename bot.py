"""
BrawlFight Bot - Full Version
Ежедневные награды, стрик, магазин, задания, достижения, анимация боя
Для PythonAnywhere Free (с прокси)
"""

import asyncio
import os
import random
import time
import json
from datetime import datetime, date

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    FSInputFile, BufferedInputFile,
)
from aiogram.fsm.storage.memory import MemoryStorage

# ====================== НАСТРОЙКИ ======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8720173063:AAHmE_D0g2g0hFgtEUjcWg6l-IjN1Zmz0Y4")
# На Railway с Volume монтируем в /data — база не теряется при деплое
DB_PATH = os.getenv("DB_PATH", "brawl_bot.db")
# Админы: через переменную ADMIN_IDS (через запятую) или список ниже
_ADMIN_ENV = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = set()
if _ADMIN_ENV:
    for x in _ADMIN_ENV.split(","):
        x = x.strip()
        if x.isdigit():
            ADMIN_IDS.add(int(x))
# Можно добавить свой Telegram ID вручную:
# ADMIN_IDS.add(123456789)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def require_admin(message: Message) -> bool:
    """Проверка прав. False = доступа нет (сообщение уже отправлено)."""
    if not ADMIN_IDS:
        await message.answer(
            "⚠️ Список админов пуст.\n\n"
            "1. Напиши /myid — скопируй свой ID\n"
            "2. В Railway → Variables добавь:\n"
            "   Key: <code>ADMIN_IDS</code>\n"
            "   Value: <code>твой_id</code>\n"
            "3. Сделай Redeploy",
            parse_mode="HTML"
        )
        return False
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа. Только для администраторов.")
        return False
    return True

BATTLE_COOLDOWN = 18
CASE_DROP_CHANCE = 12
# Защита от спама кнопки «Бой»
_battle_locks = set()

# ===== Случайные ивенты =====
import threading
_event_lock = threading.Lock()
CURRENT_EVENT = {"type": None, "name": "", "ends": 0}

EVENT_TYPES = {
    "double_coins": ("💰 x2 монеты", 2.0, 1.0),
    "double_pp": ("⚡ x2 очки силы", 1.0, 2.0),
    "more_cases": ("🎁 Больше кейсов", 1.0, 1.0),
    "double_xp": ("🎟 x2 XP сезона", 1.0, 1.0),
}

def get_active_event():
    with _event_lock:
        if CURRENT_EVENT["type"] and time.time() < CURRENT_EVENT["ends"]:
            return CURRENT_EVENT
        if CURRENT_EVENT["type"] and time.time() >= CURRENT_EVENT["ends"]:
            CURRENT_EVENT["type"] = None
            CURRENT_EVENT["name"] = ""
            CURRENT_EVENT["ends"] = 0
        # 8% шанс запустить ивент при проверке (раз в бой/ежедневку)
        if random.random() < 0.08 and CURRENT_EVENT["type"] is None:
            etype = random.choice(list(EVENT_TYPES.keys()))
            name, _, _ = EVENT_TYPES[etype]
            CURRENT_EVENT["type"] = etype
            CURRENT_EVENT["name"] = name
            CURRENT_EVENT["ends"] = time.time() + random.randint(45, 90) * 60  # 45-90 мин
        return CURRENT_EVENT if CURRENT_EVENT["type"] else None


# ====================== БРАВЛЕРЫ ======================
BRAWLERS = {
    1: {"name": "Шелли", "rarity": "Starting", "base_power": 100, "emoji": "🔫", "img_id": 16000000},
    2: {"name": "Кольт", "rarity": "Rare", "base_power": 110, "emoji": "🤠", "img_id": 16000001},
    3: {"name": "Булл", "rarity": "Rare", "base_power": 120, "emoji": "🐂", "img_id": 16000002},
    4: {"name": "Брок", "rarity": "Rare", "base_power": 112, "emoji": "🚀", "img_id": 16000003},
    5: {"name": "Рико", "rarity": "Super Rare", "base_power": 113, "emoji": "🤖", "img_id": 16000004},
    6: {"name": "Спайк", "rarity": "Legendary", "base_power": 135, "emoji": "🌵", "img_id": 16000005},
    7: {"name": "Барли", "rarity": "Rare", "base_power": 107, "emoji": "🍺", "img_id": 16000006},
    8: {"name": "Джесси", "rarity": "Super Rare", "base_power": 115, "emoji": "🔧", "img_id": 16000007},
    9: {"name": "Нита", "rarity": "Rare", "base_power": 105, "emoji": "🐻", "img_id": 16000008},
    10: {"name": "Динамайк", "rarity": "Super Rare", "base_power": 108, "emoji": "💣", "img_id": 16000009},
    11: {"name": "Эль Примо", "rarity": "Rare", "base_power": 130, "emoji": "💪", "img_id": 16000010},
    12: {"name": "Мортис", "rarity": "Mythic", "base_power": 130, "emoji": "🦇", "img_id": 16000011},
    13: {"name": "Ворон", "rarity": "Legendary", "base_power": 132, "emoji": "🐦‍⬛", "img_id": 16000012},
    14: {"name": "Поко", "rarity": "Rare", "base_power": 110, "emoji": "🎸", "img_id": 16000013},
    15: {"name": "Бо", "rarity": "Epic", "base_power": 118, "emoji": "🏹", "img_id": 16000014},
    16: {"name": "Пайпер", "rarity": "Epic", "base_power": 120, "emoji": "🎯", "img_id": 16000015},
    17: {"name": "Пэм", "rarity": "Epic", "base_power": 119, "emoji": "🛠️", "img_id": 16000016},
    18: {"name": "Тара", "rarity": "Mythic", "base_power": 128, "emoji": "🃏", "img_id": 16000017},
    19: {"name": "Дэррил", "rarity": "Super Rare", "base_power": 122, "emoji": "🛢️", "img_id": 16000018},
    20: {"name": "Пенни", "rarity": "Super Rare", "base_power": 114, "emoji": "🏴‍☠️", "img_id": 16000019},
    21: {"name": "Фрэнк", "rarity": "Epic", "base_power": 140, "emoji": "🔨", "img_id": 16000020},
    22: {"name": "Джин", "rarity": "Mythic", "base_power": 125, "emoji": "🧞", "img_id": 16000021},
    23: {"name": "Тик", "rarity": "Super Rare", "base_power": 105, "emoji": "🧨", "img_id": 16000022},
    24: {"name": "Леон", "rarity": "Legendary", "base_power": 140, "emoji": "🥷", "img_id": 16000023},
    25: {"name": "Роза", "rarity": "Rare", "base_power": 125, "emoji": "🌿", "img_id": 16000024},
    26: {"name": "Карл", "rarity": "Super Rare", "base_power": 117, "emoji": "⛏️", "img_id": 16000025},
    27: {"name": "Биби", "rarity": "Epic", "base_power": 125, "emoji": "🏏", "img_id": 16000026},
    28: {"name": "8-Бит", "rarity": "Super Rare", "base_power": 125, "emoji": "👾", "img_id": 16000027},
    29: {"name": "Сэнди", "rarity": "Legendary", "base_power": 128, "emoji": "😴", "img_id": 16000028},
    30: {"name": "Беа", "rarity": "Epic", "base_power": 115, "emoji": "🐝", "img_id": 16000029},
    31: {"name": "Эмз", "rarity": "Epic", "base_power": 115, "emoji": "💅", "img_id": 16000030},
    32: {"name": "Мистер П.", "rarity": "Mythic", "base_power": 118, "emoji": "🐧", "img_id": 16000031},
    33: {"name": "Макс", "rarity": "Mythic", "base_power": 122, "emoji": "⚡", "img_id": 16000032},
    34: {"name": "Джеки", "rarity": "Super Rare", "base_power": 128, "emoji": "🔧", "img_id": 16000034},
    35: {"name": "Гэйл", "rarity": "Epic", "base_power": 120, "emoji": "❄️", "img_id": 16000035},
    36: {"name": "Нани", "rarity": "Epic", "base_power": 118, "emoji": "🤖", "img_id": 16000036},
    37: {"name": "Сёрдж", "rarity": "Legendary", "base_power": 138, "emoji": "⚡", "img_id": 16000037},
    38: {"name": "Колетт", "rarity": "Epic", "base_power": 116, "emoji": "📒", "img_id": 16000038},
    39: {"name": "Лу", "rarity": "Mythic", "base_power": 115, "emoji": "🧊", "img_id": 16000039},
    40: {"name": "Байрон", "rarity": "Mythic", "base_power": 118, "emoji": "💉", "img_id": 16000040},
    41: {"name": "Эдгар", "rarity": "Epic", "base_power": 125, "emoji": "🧛", "img_id": 16000041},
    42: {"name": "Раффс", "rarity": "Mythic", "base_power": 117, "emoji": "🐕", "img_id": 16000042},
    43: {"name": "Сту", "rarity": "Epic", "base_power": 120, "emoji": "🎬", "img_id": 16000043},
    44: {"name": "Бэль", "rarity": "Epic", "base_power": 118, "emoji": "🎯", "img_id": 16000044},
    45: {"name": "Сквук", "rarity": "Mythic", "base_power": 112, "emoji": "🟢", "img_id": 16000045},
    46: {"name": "Базз", "rarity": "Mythic", "base_power": 128, "emoji": "🦈", "img_id": 16000046},
    47: {"name": "Грифф", "rarity": "Epic", "base_power": 118, "emoji": "💰", "img_id": 16000047},
    48: {"name": "Эш", "rarity": "Epic", "base_power": 130, "emoji": "🧹", "img_id": 16000048},
    49: {"name": "Мэг", "rarity": "Legendary", "base_power": 135, "emoji": "🤖", "img_id": 16000049},
    50: {"name": "Лола", "rarity": "Epic", "base_power": 120, "emoji": "🌟", "img_id": 16000050},
    51: {"name": "Фэнг", "rarity": "Mythic", "base_power": 125, "emoji": "🦵", "img_id": 16000051},
    52: {"name": "Ева", "rarity": "Mythic", "base_power": 115, "emoji": "🥚", "img_id": 16000052},
    53: {"name": "Джанет", "rarity": "Mythic", "base_power": 118, "emoji": "🎤", "img_id": 16000053},
    54: {"name": "Бонни", "rarity": "Epic", "base_power": 122, "emoji": "🔫", "img_id": 16000054},
    55: {"name": "Оттис", "rarity": "Mythic", "base_power": 120, "emoji": "🎨", "img_id": 16000055},
    56: {"name": "Сэм", "rarity": "Epic", "base_power": 128, "emoji": "🥊", "img_id": 16000056},
    57: {"name": "Гас", "rarity": "Super Rare", "base_power": 110, "emoji": "👻", "img_id": 16000057},
    58: {"name": "Бастер", "rarity": "Mythic", "base_power": 130, "emoji": "🎬", "img_id": 16000058},
    59: {"name": "Честер", "rarity": "Legendary", "base_power": 125, "emoji": "🎲", "img_id": 16000059},
    60: {"name": "Гром", "rarity": "Epic", "base_power": 115, "emoji": "📬", "img_id": 16000060},
    61: {"name": "Чак", "rarity": "Mythic", "base_power": 120, "emoji": "🚂", "img_id": 16000062},
    62: {"name": "Дуг", "rarity": "Mythic", "base_power": 125, "emoji": "🌭", "img_id": 16000063},
    63: {"name": "Корделиус", "rarity": "Legendary", "base_power": 130, "emoji": "🍄", "img_id": 16000064},
    64: {"name": "Перл", "rarity": "Epic", "base_power": 122, "emoji": "🔥", "img_id": 16000065},
    65: {"name": "Чарли", "rarity": "Mythic", "base_power": 118, "emoji": "🕷️", "img_id": 16000066},
    66: {"name": "Мико", "rarity": "Mythic", "base_power": 120, "emoji": "🐵", "img_id": 16000067},
    67: {"name": "Кит", "rarity": "Legendary", "base_power": 125, "emoji": "🐱", "img_id": 16000068},
    68: {"name": "Ларри и Лори", "rarity": "Epic", "base_power": 118, "emoji": "🎫", "img_id": 16000069},
    69: {"name": "Хэнк", "rarity": "Epic", "base_power": 128, "emoji": "🦐", "img_id": 16000070},
    70: {"name": "Мэйси", "rarity": "Epic", "base_power": 118, "emoji": "🎯", "img_id": 16000071},
    71: {"name": "Манди", "rarity": "Epic", "base_power": 115, "emoji": "🍬", "img_id": 16000072},
    72: {"name": "Р-Т", "rarity": "Mythic", "base_power": 120, "emoji": "📺", "img_id": 16000073},
    73: {"name": "Виллоу", "rarity": "Mythic", "base_power": 115, "emoji": "🪵", "img_id": 16000074},
    74: {"name": "Мо", "rarity": "Mythic", "base_power": 122, "emoji": "🐹", "img_id": 16000080},
    75: {"name": "Клэнси", "rarity": "Mythic", "base_power": 125, "emoji": "🦞", "img_id": 16000081},
    76: {"name": "Лилли", "rarity": "Mythic", "base_power": 118, "emoji": "🌸", "img_id": 16000082},
    77: {"name": "Драко", "rarity": "Legendary", "base_power": 135, "emoji": "🐉", "img_id": 16000083},
    78: {"name": "Анджело", "rarity": "Epic", "base_power": 115, "emoji": "🏹", "img_id": 16000084},
    79: {"name": "Мелоди", "rarity": "Mythic", "base_power": 120, "emoji": "🎵", "img_id": 16000085},
    80: {"name": "Берри", "rarity": "Epic", "base_power": 115, "emoji": "🍹", "img_id": 16000086},
    81: {"name": "Джуджу", "rarity": "Mythic", "base_power": 118, "emoji": "🪄", "img_id": 16000087},
    82: {"name": "Шейд", "rarity": "Epic", "base_power": 122, "emoji": "🌑", "img_id": 16000088},
    83: {"name": "Кэндзи", "rarity": "Legendary", "base_power": 132, "emoji": "⚔️", "img_id": 16000089},
    84: {"name": "Олли", "rarity": "Mythic", "base_power": 125, "emoji": "🛹", "img_id": 16000090},
    85: {"name": "Мипл", "rarity": "Epic", "base_power": 115, "emoji": "🎲", "img_id": 16000091},
    86: {"name": "Аллли", "rarity": "Mythic", "base_power": 120, "emoji": "🐊", "img_id": 16000092},
    87: {"name": "Финкс", "rarity": "Mythic", "base_power": 118, "emoji": "⏳", "img_id": 16000093},
    88: {"name": "Луми", "rarity": "Mythic", "base_power": 120, "emoji": "💡", "img_id": 16000094},
    89: {"name": "Грэй", "rarity": "Mythic", "base_power": 118, "emoji": "🚪", "img_id": 16000095},
    90: {"name": "Джае-Йонг", "rarity": "Mythic", "base_power": 122, "emoji": "🎤", "img_id": 16000096},
    91: {"name": "Казе", "rarity": "Ultra Legendary", "base_power": 145, "emoji": "🎎", "img_id": 16000097},
    92: {"name": "Сириус", "rarity": "Mythic", "base_power": 125, "emoji": "⭐", "img_id": 16000098},
    93: {"name": "Транк", "rarity": "Epic", "base_power": 128, "emoji": "🐘", "img_id": 16000099},
    94: {"name": "Пирс", "rarity": "Epic", "base_power": 120, "emoji": "🔫", "img_id": 16000100},
    95: {"name": "Мина", "rarity": "Mythic", "base_power": 118, "emoji": "⛏️", "img_id": 16000101},
    96: {"name": "Зигги", "rarity": "Epic", "base_power": 115, "emoji": "⚡", "img_id": 16000102},
    97: {"name": "Наджия", "rarity": "Mythic", "base_power": 120, "emoji": "🗡️", "img_id": 16000103},
    98: {"name": "Дамиан", "rarity": "Mythic", "base_power": 130, "emoji": "🎤", "img_id": 16000104},
    99: {"name": "Старр Нова", "rarity": "Mythic", "base_power": 125, "emoji": "✨", "img_id": 16000105},
    100: {"name": "Болт", "rarity": "Epic", "base_power": 128, "emoji": "🏎️", "img_id": 16000106},
    101: {"name": "Нори", "rarity": "Legendary", "base_power": 135, "emoji": "🍣", "img_id": 16000107},
    102: {"name": "Венди", "rarity": "Mythic", "base_power": 120, "emoji": "💨", "img_id": 16000108},
}

# Ранги по трофеям
RANKS = [
    (0,    "🥉 Бронза",     "bronze"),
    (100,  "🥈 Серебро",    "silver"),
    (300,  "🥇 Золото",     "gold"),
    (600,  "💎 Алмаз",      "diamond"),
    (1000, "🏆 Мастер",     "master"),
    (1500, "👑 Легенда",    "legend"),
]

def get_rank(trophies: int) -> str:
    rank_name = RANKS[0][1]
    for threshold, name, _ in RANKS:
        if trophies >= threshold:
            rank_name = name
    return rank_name

RARITY_ORDER = {"Starting": 0, "Rare": 1, "Super Rare": 2, "Epic": 3, "Mythic": 4, "Legendary": 5}
RARITY_EMOJI = {"Starting": "⚪", "Rare": "🟢", "Super Rare": "🔵", "Epic": "🟣", "Mythic": "🔴", "Legendary": "🟡"}

UPGRADE_COST = {
    1: (40, 25), 2: (70, 45), 3: (110, 75), 4: (170, 120),
    5: (250, 180), 6: (360, 260), 7: (500, 370),
    8: (700, 520), 9: (950, 720), 10: (1300, 1000),
}

# Магазин
SHOP_ITEMS = {
    "case_normal":   {"name": "🎁 Обычный кейс",     "price_crystals": 15,  "price_coins": 0},
    "case_epic":     {"name": "🎁 Эпический кейс",   "price_crystals": 45,  "price_coins": 0},
    "case_legend":   {"name": "🎁 Легендарный кейс", "price_crystals": 120, "price_coins": 0},
    "pp_100":        {"name": "⚡ 100 очков силы",   "price_crystals": 0,   "price_coins": 80},
    "pp_300":        {"name": "⚡ 300 очков силы",   "price_crystals": 0,   "price_coins": 220},
    "crystals_10":   {"name": "💎 10 кристаллов",    "price_crystals": 0,   "price_coins": 350},
}

# Достижения
ACHIEVEMENTS = {
    "brawlers_5":   {"name": "Собрать 5 бравлеров",     "check": lambda u, owned: len(owned) >= 5,  "reward_coins": 100, "reward_crystals": 3},
    "brawlers_15":  {"name": "Собрать 15 бравлеров",    "check": lambda u, owned: len(owned) >= 15, "reward_coins": 300, "reward_crystals": 8},
    "trophies_200": {"name": "Достичь 200 трофеев",     "check": lambda u, owned: u["trophies"] >= 200, "reward_coins": 150, "reward_crystals": 5},
    "trophies_500": {"name": "Достичь 500 трофеев",     "check": lambda u, owned: u["trophies"] >= 500, "reward_coins": 400, "reward_crystals": 12},
    "wins_50":      {"name": "Выиграть 50 боёв",        "check": lambda u, owned: u["wins"] >= 50,  "reward_coins": 250, "reward_crystals": 7},
    "wins_100":     {"name": "Выиграть 100 боёв",       "check": lambda u, owned: u["wins"] >= 100, "reward_coins": 500, "reward_crystals": 15},
}

# ====================== БАЗА ДАННЫХ ======================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                coins INTEGER DEFAULT 150,
                power_points INTEGER DEFAULT 80,
                crystals INTEGER DEFAULT 10,
                trophies INTEGER DEFAULT 0,
                selected_brawler INTEGER DEFAULT 1,
                cases INTEGER DEFAULT 1,
                cases_epic INTEGER DEFAULT 0,
                cases_legend INTEGER DEFAULT 0,
                last_battle REAL DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                last_daily TEXT DEFAULT '',
                quests TEXT DEFAULT '{}',
                achievements TEXT DEFAULT '[]',
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_brawlers (
                user_id INTEGER,
                brawler_id INTEGER,
                level INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, brawler_id)
            )
        """)
        # Новые поля (для уже существующих баз)
        for col, typedef in [
            ("battle_history", "TEXT DEFAULT '[]'"),
            ("season_xp", "INTEGER DEFAULT 0"),
            ("season_claimed", "TEXT DEFAULT '[]'"),
            ("season_premium", "INTEGER DEFAULT 0"),
            ("nickname", "TEXT DEFAULT ''"),
            ("win_streak", "INTEGER DEFAULT 0"),
            ("weekly_wins", "INTEGER DEFAULT 0"),
            ("weekly_reset", "TEXT DEFAULT ''"),
            ("keys", "INTEGER DEFAULT 0"),
            ("tower_floor", "INTEGER DEFAULT 1"),
            ("tower_best", "INTEGER DEFAULT 0"),
            ("pve_best", "INTEGER DEFAULT 0"),
            ("last_roulette", "TEXT DEFAULT ''"),
            ("boss_damage", "INTEGER DEFAULT 0"),
            ("boss_week", "TEXT DEFAULT ''"),
        ]:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
            except Exception:
                pass
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(user_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, created_at, quests, achievements) VALUES (?, ?, ?, '{}', '[]')",
            (user_id, username or "Player", datetime.now().isoformat())
        )
        await db.execute(
            "INSERT OR IGNORE INTO user_brawlers (user_id, brawler_id, level) VALUES (?, 1, 1)",
            (user_id,)
        )
        await db.commit()


async def update_user(user_id: int, **kwargs):
    if not kwargs:
        return
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {sets} WHERE user_id = ?", values)
        await db.commit()


async def get_user_brawlers(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT brawler_id, level FROM user_brawlers WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return {row["brawler_id"]: row["level"] for row in rows}


async def add_brawler(user_id: int, brawler_id: int, level: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_brawlers (user_id, brawler_id, level) VALUES (?, ?, ?)",
            (user_id, brawler_id, level)
        )
        await db.commit()


async def set_brawler_level(user_id: int, brawler_id: int, level: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE user_brawlers SET level = ? WHERE user_id = ? AND brawler_id = ?",
            (level, user_id, brawler_id)
        )
        await db.commit()


async def get_random_opponent(exclude_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, selected_brawler, trophies FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1",
            (exclude_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ====================== КЛАВИАТУРЫ ======================
def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚔️ Бой"), KeyboardButton(text="🎁 Ежедневка")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📦 Коллекция")],
            [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="⬆️ Прокачка")],
            [KeyboardButton(text="📋 Задания"), KeyboardButton(text="🏅 Достижения")],
            [KeyboardButton(text="🎁 Открыть кейс"), KeyboardButton(text="🎟 Пропуск")],
            [KeyboardButton(text="📜 История"), KeyboardButton(text="🏆 Топ")],
            [KeyboardButton(text="📅 Топ недели")],
            [KeyboardButton(text="🎲 Рулетка"), KeyboardButton(text="🌊 Волны")],
            [KeyboardButton(text="🗼 Башня"), KeyboardButton(text="👹 Босс")],
            [KeyboardButton(text="🗝️ Сундук")],
            [KeyboardButton(text="✏️ Ник"), KeyboardButton(text="📖 Гайд")],
        ],
        resize_keyboard=True
    )


def battle_mode_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Обычный бой", callback_data="battle_normal")],
        [InlineKeyboardButton(text="🏆 Рейтинговый бой", callback_data="battle_ranked")],
        [InlineKeyboardButton(text="« Отмена", callback_data="back_main")],
    ])


def shop_kb():
    buttons = []
    for key, item in SHOP_ITEMS.items():
        price = f"{item['price_crystals']}💎" if item['price_crystals'] else f"{item['price_coins']}💰"
        buttons.append([InlineKeyboardButton(text=f"{item['name']} — {price}", callback_data=f"buy_{key}")])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def brawler_select_kb(owned: dict):
    buttons, row = [], []
    for bid, data in BRAWLERS.items():
        if bid in owned:
            text = f"{data['emoji']} {data['name']} (ур.{owned[bid]})"
            row.append(InlineKeyboardButton(text=text, callback_data=f"select_{bid}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def upgrade_kb(owned: dict):
    buttons = []
    for bid, level in sorted(owned.items(), key=lambda x: BRAWLERS[x[0]]["name"]):
        data = BRAWLERS[bid]
        if level < 11:
            cost_c, cost_pp = UPGRADE_COST.get(level, (9999, 9999))
            text = f"{data['emoji']} {data['name']} ур.{level}→{level+1} ({cost_c}💰 {cost_pp}⚡)"
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"upgrade_{bid}")])
        else:
            buttons.append([InlineKeyboardButton(text=f"{data['emoji']} {data['name']} — МАКС", callback_data="noop")])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ====================== ЕЖЕДНЕВНЫЕ НАГРАДЫ ======================
async def claim_daily(user_id: int) -> str:
    user = await get_user(user_id)
    if not user:
        return "Сначала /start"

    today = str(date.today())
    last = user.get("last_daily") or ""
    streak = user.get("streak") or 0

    if last == today:
        return "🎁 Ты уже забрал ежедневную награду сегодня!\nПриходи завтра."

    # Проверяем стрик
    from datetime import timedelta
    yesterday = str(date.today() - timedelta(days=1))
    if last == yesterday:
        streak += 1
    else:
        streak = 1

    # Награда зависит от стрика
    coins = 80 + streak * 25
    pp = 40 + streak * 12
    crystals = 1 if streak >= 3 else 0
    cases = 1 if streak % 3 == 0 else 0
    cases_epic = 0
    bonus_text = ""

    # Вехи стрика
    if streak == 7:
        crystals += 5
        cases += 1
        bonus_text += "\n🏅 Бонус 7 дней: +5💎 +1🎁"
    elif streak == 14:
        crystals += 10
        cases_epic = 1
        bonus_text += "\n🏅 Бонус 14 дней: +10💎 +1 эпик-кейс"
    elif streak == 30:
        crystals += 25
        cases_epic = 2
        coins += 500
        bonus_text += "\n👑 Бонус 30 дней: +25💎 +2 эпик-кейса +500💰"
    elif streak >= 7 and streak % 7 == 0:
        crystals += 3
        bonus_text += f"\n🔥 Еженедельный бонус стрика: +3💎"

    # Ивент
    ev = get_active_event()
    if ev and ev["type"] == "double_coins":
        coins *= 2
        bonus_text += f"\n🎉 Ивент {ev['name']}!"
    if ev and ev["type"] == "double_pp":
        pp *= 2
        bonus_text += f"\n🎉 Ивент {ev['name']}!"

    await update_user(
        user_id,
        coins=user["coins"] + coins,
        power_points=user["power_points"] + pp,
        crystals=user["crystals"] + crystals,
        cases=user["cases"] + cases,
        cases_epic=user.get("cases_epic", 0) + cases_epic,
        streak=streak,
        last_daily=today
    )

    text = (
        f"🎁 <b>Ежедневная награда</b>\n\n"
        f"Стрик: <b>{streak} дней</b> 🔥\n\n"
        f"Ты получил:\n"
        f"💰 {coins} монет\n"
        f"⚡ {pp} очков силы\n"
    )
    if crystals:
        text += f"💎 {crystals} кристалл(ов)\n"
    if cases:
        text += f"🎁 {cases} обычный кейс\n"
    if cases_epic:
        text += f"🎁 {cases_epic} эпический кейс\n"
    text += bonus_text
    text += f"\n\nЗавтра награда будет ещё больше!"
    if ev:
        left = int((ev["ends"] - time.time()) / 60)
        text += f"\n\n🎉 Сейчас ивент: <b>{ev['name']}</b> (ещё ~{left} мин)"
    return text


# ====================== ЗАДАНИЯ ======================
def get_default_quests():
    return {
        "battles": 0,
        "wins": 0,
        "upgrade": 0,
        "ranked": 0,
        "cases": 0,
        "reward_claimed": False,
        "date": str(date.today())
    }


async def get_quests(user_id: int):
    user = await get_user(user_id)
    quests = json.loads(user.get("quests") or "{}")
    today = str(date.today())
    if quests.get("date") != today:
        quests = get_default_quests()
        await update_user(user_id, quests=json.dumps(quests))
    return quests


async def update_quest(user_id: int, quest_type: str, amount: int = 1):
    quests = await get_quests(user_id)
    quests[quest_type] = quests.get(quest_type, 0) + amount
    await update_user(user_id, quests=json.dumps(quests))


async def show_quests(user_id: int) -> str:
    user = await get_user(user_id)
    quests = await get_quests(user_id)
    trophies = user["trophies"] if user else 0

    # Сложность зависит от трофеев
    if trophies < 100:
        need_battles, need_wins, need_upgrade, need_ranked = 3, 1, 1, 0
        reward_coins, reward_cases = 150, 0
    elif trophies < 400:
        need_battles, need_wins, need_upgrade, need_ranked = 5, 3, 1, 1
        reward_coins, reward_cases = 250, 1
    else:
        need_battles, need_wins, need_upgrade, need_ranked = 8, 5, 2, 2
        reward_coins, reward_cases = 400, 1

    battles = min(quests.get("battles", 0), need_battles)
    wins = min(quests.get("wins", 0), need_wins)
    upgrade = min(quests.get("upgrade", 0), need_upgrade)
    ranked = min(quests.get("ranked", 0), need_ranked)
    reward_claimed = quests.get("reward_claimed", False)

    text = f"📋 <b>Задания на сегодня</b>\n<i>Сложность под твои трофеи</i>\n\n"
    text += f"{'✅' if battles >= need_battles else '🔲'} Сыграть {need_battles} боёв  ({battles}/{need_battles})\n"
    text += f"{'✅' if wins >= need_wins else '🔲'} Выиграть {need_wins} боёв  ({wins}/{need_wins})\n"
    text += f"{'✅' if upgrade >= need_upgrade else '🔲'} Прокачать бравлера x{need_upgrade}  ({upgrade}/{need_upgrade})\n"
    if need_ranked > 0:
        text += f"{'✅' if ranked >= need_ranked else '🔲'} Рейтинговых боёв: {need_ranked}  ({ranked}/{need_ranked})\n"
    text += "\n"

    all_done = (
        battles >= need_battles and wins >= need_wins
        and upgrade >= need_upgrade and ranked >= need_ranked
    )

    if all_done and not reward_claimed:
        await update_user(
            user_id,
            coins=user["coins"] + reward_coins,
            cases_epic=user.get("cases_epic", 0) + reward_cases
        )
        quests["reward_claimed"] = True
        await update_user(user_id, quests=json.dumps(quests))
        text += (
            "🎉 <b>Все задания выполнены!</b>\n\n"
            f"Ты получил:\n💰 +{reward_coins} монет"
        )
        if reward_cases:
            text += f"\n🎁 +{reward_cases} Эпический кейс"
    elif reward_claimed:
        text += "✅ Награда за задания уже получена сегодня."
    else:
        text += f"Награда: 💰 {reward_coins} монет"
        if reward_cases:
            text += f" + 🎁 Эпический кейс"

    return text


# ====================== ДОСТИЖЕНИЯ ======================
async def check_achievements(user_id: int) -> list:
    user = await get_user(user_id)
    owned = await get_user_brawlers(user_id)
    unlocked = json.loads(user.get("achievements") or "[]")
    newly = []

    for key, ach in ACHIEVEMENTS.items():
        if key not in unlocked and ach["check"](user, owned):
            unlocked.append(key)
            newly.append(ach)
            await update_user(
                user_id,
                coins=user["coins"] + ach["reward_coins"],
                crystals=user["crystals"] + ach["reward_crystals"],
                achievements=json.dumps(unlocked)
            )
            user["coins"] += ach["reward_coins"]
            user["crystals"] += ach["reward_crystals"]
    return newly


async def show_achievements(user_id: int) -> str:
    user = await get_user(user_id)
    owned = await get_user_brawlers(user_id)
    unlocked = json.loads(user.get("achievements") or "[]")

    lines = ["🏅 <b>Достижения</b>\n"]
    for key, ach in ACHIEVEMENTS.items():
        status = "✅" if key in unlocked else "🔲"
        lines.append(f"{status} {ach['name']}")
    return "\n".join(lines)


# ====================== БОЙ С АНИМАЦИЕЙ ======================
def calc_power(brawler_id: int, level: int) -> float:
    base = BRAWLERS[brawler_id]["base_power"]
    power = base * (1 + 0.10 * (level - 1))
    power *= random.uniform(0.87, 1.13)
    return power


async def do_battle_animated(message: Message, mode: str = "normal", user_id: int = None):
    """mode: normal | ranked"""
    if user_id is None:
        user_id = message.from_user.id

    # Защита от спама кнопки Бой
    if user_id in _battle_locks:
        await message.answer("⏳ Бой уже идёт, подожди...")
        return
    _battle_locks.add(user_id)
    try:
        await _do_battle_inner(message, mode, user_id)
    finally:
        _battle_locks.discard(user_id)


async def _do_battle_inner(message: Message, mode: str, user_id: int):
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала /start")
        return

    now = time.time()
    if now - user["last_battle"] < BATTLE_COOLDOWN:
        left = int(BATTLE_COOLDOWN - (now - user["last_battle"]))
        await message.answer(f"⏳ Подожди ещё {left} сек.")
        return

    owned = await get_user_brawlers(user_id)
    selected = user["selected_brawler"]
    if selected not in owned:
        selected = 1
        await update_user(user_id, selected_brawler=1)

    my_level = owned[selected]
    my_power = calc_power(selected, my_level)
    my_brawler = BRAWLERS[selected]

    # Анимация поиска
    msg = await message.answer("🔍 Ищем достойного соперника...")
    await asyncio.sleep(1.4)

    opponent = await get_random_opponent(user_id)
    is_bot = opponent is None or random.random() < 0.42

    if is_bot:
        opp_bid = random.choice(list(BRAWLERS.keys()))
        if user["trophies"] < 100:
            opp_level = random.randint(1, 3)
        elif user["trophies"] < 300:
            opp_level = random.randint(2, 5)
        elif user["trophies"] < 600:
            opp_level = random.randint(4, 7)
        else:
            opp_level = random.randint(6, 10)
        opp_name = f"🤖 Бот ({BRAWLERS[opp_bid]['name']})"
        opp_power = calc_power(opp_bid, opp_level)
        opp_emoji = BRAWLERS[opp_bid]["emoji"]
    else:
        opp_bid = opponent["selected_brawler"]
        opp_owned = await get_user_brawlers(opponent["user_id"])
        opp_level = opp_owned.get(opp_bid, 1)
        opp_power = calc_power(opp_bid, opp_level)
        opp_brawler_name = BRAWLERS.get(opp_bid, BRAWLERS[1])["name"]
        # Используем ник, если задан, иначе username
        display = opponent.get("nickname") or opponent.get("username") or "Игрок"
        opp_name = f"{display} ({opp_brawler_name})"
        opp_emoji = BRAWLERS.get(opp_bid, BRAWLERS[1])["emoji"]

    # Анимация боя
    await msg.edit_text(
        f"⚔️ <b>Бой начался!</b>\n\n"
        f"{my_brawler['emoji']} <b>{my_brawler['name']}</b> ур.{my_level}\n"
        f"vs\n"
        f"{opp_emoji} <b>{opp_name}</b> ур.{opp_level}",
        parse_mode="HTML"
    )
    await asyncio.sleep(1.3)

    await msg.edit_text(
        f"💥 Выстрел! 💥\n"
        f"{my_brawler['emoji']} vs {opp_emoji}\n"
        f"Силы сталкиваются...",
        parse_mode="HTML"
    )
    await asyncio.sleep(1.1)

    i_win = my_power > opp_power
    is_ranked = mode == "ranked"

    # Серия побед
    cur_ws = user.get("win_streak") or 0
    if i_win:
        cur_ws += 1
    else:
        cur_ws = 0

    # Награды
    if is_ranked:
        coins_gain = random.randint(35, 55) if i_win else random.randint(10, 22)
        pp_gain = random.randint(20, 38) if i_win else random.randint(6, 15)
        trophies_change = random.randint(14, 22) if i_win else -random.randint(10, 18)
    else:
        coins_gain = random.randint(28, 48) if i_win else random.randint(12, 26)
        pp_gain = random.randint(16, 32) if i_win else random.randint(8, 18)
        trophies_change = random.randint(9, 16) if i_win else -random.randint(5, 12)

    # Бонус за серию побед
    ws_bonus = ""
    if i_win and cur_ws >= 3:
        mult = 1.0 + min(cur_ws, 10) * 0.05  # до +50%
        coins_gain = int(coins_gain * mult)
        pp_gain = int(pp_gain * mult)
        ws_bonus = f"\n🔥 Серия побед: {cur_ws} (x{mult:.2f} награда)"

    crystals_gain = 1 if (i_win and random.random() < (0.18 if is_ranked else 0.13)) else 0
    case_chance = CASE_DROP_CHANCE + (5 if is_ranked else 0)

    # Ивент
    ev = get_active_event()
    xp_gain = (15 if i_win else 8) + (5 if is_ranked else 0)
    if ev:
        if ev["type"] == "double_coins":
            coins_gain *= 2
            ws_bonus += f"\n🎉 {ev['name']}!"
        elif ev["type"] == "double_pp":
            pp_gain *= 2
            ws_bonus += f"\n🎉 {ev['name']}!"
        elif ev["type"] == "more_cases":
            case_chance += 12
            ws_bonus += f"\n🎉 {ev['name']}!"
        elif ev["type"] == "double_xp":
            xp_gain *= 2
            ws_bonus += f"\n🎉 {ev['name']}!"

    case_dropped = random.random() * 100 < case_chance
    new_trophies = max(0, user["trophies"] + trophies_change)
    season_xp = (user.get("season_xp") or 0) + xp_gain

    # Недельные победы
    from datetime import timedelta
    week_key = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    weekly_wins = user.get("weekly_wins") or 0
    weekly_reset = user.get("weekly_reset") or ""
    if weekly_reset != week_key:
        weekly_wins = 0
        weekly_reset = week_key
    if i_win:
        weekly_wins += 1

    # История боёв
    history = json.loads(user.get("battle_history") or "[]")
    history.insert(0, {
        "result": "win" if i_win else "loss",
        "my": my_brawler["name"],
        "opp": opp_name,
        "trophies": trophies_change,
        "mode": "ranked" if is_ranked else "normal",
        "time": datetime.now().strftime("%d.%m %H:%M")
    })
    history = history[:10]

    await update_user(
        user_id,
        coins=user["coins"] + coins_gain,
        power_points=user["power_points"] + pp_gain,
        crystals=user["crystals"] + crystals_gain,
        trophies=new_trophies,
        cases=user["cases"] + (1 if case_dropped else 0),
        last_battle=now,
        wins=user["wins"] + (1 if i_win else 0),
        losses=user["losses"] + (0 if i_win else 1),
        season_xp=season_xp,
        battle_history=json.dumps(history, ensure_ascii=False),
        win_streak=cur_ws,
        weekly_wins=weekly_wins,
        weekly_reset=weekly_reset,
    )

    # Обновляем задания
    await update_quest(user_id, "battles")
    if i_win:
        await update_quest(user_id, "wins")
    if is_ranked:
        await update_quest(user_id, "ranked")

    # Проверяем достижения
    new_achs = await check_achievements(user_id)

    mode_label = "🏆 Рейтинговый" if is_ranked else "⚔️ Обычный"
    result_emoji = "🏆 <b>ПОБЕДА!</b>" if i_win else "💀 <b>Поражение</b>"
    text = (
        f"{result_emoji} ({mode_label})\n\n"
        f"{my_brawler['emoji']} <b>{my_brawler['name']}</b> ур.{my_level} — {my_power:.0f} силы\n"
        f"{opp_emoji} <b>{opp_name}</b> — {opp_power:.0f} силы\n\n"
        f"📊 Награды:\n"
        f"💰 +{coins_gain} монет\n"
        f"⚡ +{pp_gain} очков силы\n"
        f"🏆 {'+' if trophies_change > 0 else ''}{trophies_change} трофеев (всего {new_trophies})\n"
        f"🎟 +{xp_gain} XP сезона\n"
    )
    if cur_ws > 0 and i_win:
        text += f"🔥 Серия побед: <b>{cur_ws}</b>\n"
    if crystals_gain:
        text += f"💎 +{crystals_gain} кристалл\n"
    if case_dropped:
        text += f"\n🎁 <b>Выпал кейс!</b>"
    text += ws_bonus

    if new_achs:
        text += "\n\n🏅 Новое достижение!"
        for a in new_achs:
            text += f"\n✅ {a['name']}"

    await msg.edit_text(text, parse_mode="HTML")


# ====================== ОТКРЫТИЕ КЕЙСОВ ======================
async def open_case(user_id: int, case_type: str = "normal"):
    """Возвращает (текст, url_картинки или None)"""
    user = await get_user(user_id)
    if not user:
        return "Сначала /start", None

    if case_type == "normal":
        if user["cases"] < 1:
            return "У тебя нет обычных кейсов 🎁", None
        await update_user(user_id, cases=user["cases"] - 1)
        rarity_chances = [(70, "currency"), (18, "Rare"), (8, "Super Rare"), (3, "Epic"), (0.8, "Mythic"), (0.2, "Legendary")]
    elif case_type == "epic":
        if user.get("cases_epic", 0) < 1:
            return "У тебя нет эпических кейсов 🎁", None
        await update_user(user_id, cases_epic=user.get("cases_epic", 0) - 1)
        rarity_chances = [(45, "currency"), (25, "Super Rare"), (18, "Epic"), (9, "Mythic"), (3, "Legendary")]
    else:
        if user.get("cases_legend", 0) < 1:
            return "У тебя нет легендарных кейсов 🎁", None
        await update_user(user_id, cases_legend=user.get("cases_legend", 0) - 1)
        rarity_chances = [(30, "currency"), (25, "Epic"), (28, "Mythic"), (17, "Legendary")]

    roll = random.random() * 100
    cumulative = 0
    reward_type = "currency"
    rarity = "Rare"
    for chance, rtype in rarity_chances:
        cumulative += chance
        if roll < cumulative:
            if rtype == "currency":
                reward_type = "currency"
            else:
                reward_type = "brawler"
                rarity = rtype
            break

    owned = await get_user_brawlers(user_id)

    if reward_type == "currency":
        coins = random.randint(50, 140)
        pp = random.randint(25, 70)
        await update_user(user_id, coins=user["coins"] + coins, power_points=user["power_points"] + pp)
        return f"🎁 Кейс открыт!\n\n💰 {coins} монет\n⚡ {pp} очков силы", None

    candidates = [bid for bid, d in BRAWLERS.items() if d["rarity"] == rarity and bid not in owned]
    if not candidates:
        candidates = [bid for bid, d in BRAWLERS.items() if d["rarity"] == rarity]
    if not candidates:
        coins = random.randint(90, 180)
        await update_user(user_id, coins=user["coins"] + coins)
        return f"🎁 Кейс открыт!\nДубликат → 💰 {coins} монет", None

    new_bid = random.choice(candidates)
    data = BRAWLERS[new_bid]
    img_url = f"https://cdn.brawlify.com/brawlers/borders/{data['img_id']}.png"

    if new_bid in owned:
        coins = random.randint(70, 160)
        await update_user(user_id, coins=user["coins"] + coins)
        return f"🎁 Кейс открыт!\nДубликат {data['emoji']} {data['name']} → 💰 {coins} монет", None
    else:
        await add_brawler(user_id, new_bid, 1)
        await check_achievements(user_id)
        text = (
            f"🎁 Кейс открыт!\n\n"
            f"🎉 <b>Новый бравлер!</b>\n"
            f"{RARITY_EMOJI[data['rarity']]} {data['emoji']} <b>{data['name']}</b>\n"
            f"Редкость: {data['rarity']}\n"
            f"Сила: {data['base_power']}"
        )
        return text, img_url


# ====================== МАГАЗИН ======================
async def buy_item(user_id: int, item_key: str) -> str:
    user = await get_user(user_id)
    if not user or item_key not in SHOP_ITEMS:
        return "Ошибка"

    item = SHOP_ITEMS[item_key]
    if item["price_crystals"] > 0:
        if user["crystals"] < item["price_crystals"]:
            return f"Не хватает кристаллов! Нужно {item['price_crystals']}💎"
        await update_user(user_id, crystals=user["crystals"] - item["price_crystals"])
    else:
        if user["coins"] < item["price_coins"]:
            return f"Не хватает монет! Нужно {item['price_coins']}💰"
        await update_user(user_id, coins=user["coins"] - item["price_coins"])

    # Выдача товара
    if item_key == "case_normal":
        await update_user(user_id, cases=user["cases"] + 1)
        return f"✅ Куплено: {item['name']}\nТеперь у тебя {user['cases']+1} обычных кейсов"
    elif item_key == "case_epic":
        await update_user(user_id, cases_epic=user.get("cases_epic", 0) + 1)
        return f"✅ Куплено: {item['name']}"
    elif item_key == "case_legend":
        await update_user(user_id, cases_legend=user.get("cases_legend", 0) + 1)
        return f"✅ Куплено: {item['name']}"
    elif item_key == "pp_100":
        await update_user(user_id, power_points=user["power_points"] + 100)
        return f"✅ Куплено: ⚡ 100 очков силы"
    elif item_key == "pp_300":
        await update_user(user_id, power_points=user["power_points"] + 300)
        return f"✅ Куплено: ⚡ 300 очков силы"
    elif item_key == "crystals_10":
        await update_user(user_id, crystals=user["crystals"] + 10)
        return f"✅ Куплено: 💎 10 кристаллов"
    return "Ошибка"


# ====================== ХЕНДЛЕРЫ ======================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    await create_user(user_id, username)

    text = (
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        f"Добро пожаловать в <b>BrawlFight</b>!\n\n"
        f"Ты получил 🔫 <b>Shelly</b> (уровень 1)\n\n"
        f"⚔️ Сражайся • 📦 Собирай бравлеров\n"
        f"⬆️ Прокачивай • 🛒 Покупай кейсы\n"
        f"🎁 Забирай ежедневные награды\n\n"
        f"Используй кнопки внизу 👇"
    )
    await message.answer(text, reply_markup=main_kb(), parse_mode="HTML")


@dp.message(F.text == "🎁 Ежедневка")
@dp.message(Command("daily"))
async def cmd_daily(message: Message):
    text = await claim_daily(message.from_user.id)
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "⚔️ Бой")
@dp.message(Command("battle"))
async def cmd_battle(message: Message):
    await message.answer(
        "Выбери режим боя:\n\n"
        "⚔️ <b>Обычный</b> — стандартные награды\n"
        "🏆 <b>Рейтинговый</b> — больше трофеев и наград, но и риск выше",
        reply_markup=battle_mode_kb(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.in_({"battle_normal", "battle_ranked"}))
async def cb_battle_mode(callback: CallbackQuery):
    mode = "ranked" if callback.data == "battle_ranked" else "normal"
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await do_battle_animated(callback.message, mode=mode, user_id=callback.from_user.id)


@dp.message(F.text == "👤 Профиль")
@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    owned = await get_user_brawlers(message.from_user.id)
    selected = BRAWLERS.get(user["selected_brawler"], BRAWLERS[1])
    level = owned.get(user["selected_brawler"], 1)
    total = user["wins"] + user["losses"]
    winrate = round(user["wins"] / total * 100, 1) if total > 0 else 0

    rank = get_rank(user["trophies"])
    nick = user.get("nickname") or user.get("username") or "Игрок"
    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"🏷 Ник: <b>{nick}</b>\n"
        f"🏅 Ранг: <b>{rank}</b>\n"
        f"🏆 Трофеи: <b>{user['trophies']}</b>\n"
        f"🔥 Стрик входа: <b>{user.get('streak', 0)}</b> дн. | Серия побед: <b>{user.get('win_streak', 0)}</b>\n"
        f"💰 Монеты: <b>{user['coins']}</b>\n"
        f"⚡ Очки силы: <b>{user['power_points']}</b>\n"
        f"💎 Кристаллы: <b>{user['crystals']}</b>\n"
        f"🎁 Кейсы: {user['cases']} обыч. | {user.get('cases_epic',0)} эпик | {user.get('cases_legend',0)} лег.\n\n"
        f"🔫 Выбран: {selected['emoji']} <b>{selected['name']}</b> ур.{level}\n"
        f"📦 Бравлеров: <b>{len(owned)}</b>/102\n"
        f"📊 {user['wins']}W / {user['losses']}L ({winrate}%)\n"
        f"🗝️ Ключи: <b>{user.get('keys', 0)}</b> | 🗼 Этаж: {user.get('tower_floor', 1)} (рекорд {user.get('tower_best', 0)})\n"
        f"🌊 Рекорд волн: <b>{user.get('pve_best', 0)}</b>"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "📦 Коллекция")
async def cmd_collection(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    owned = await get_user_brawlers(message.from_user.id)
    lines = ["📦 <b>Твоя коллекция</b>\n"]
    for bid in sorted(owned.keys(), key=lambda x: (RARITY_ORDER[BRAWLERS[x]["rarity"]], BRAWLERS[x]["name"])):
        data = BRAWLERS[bid]
        mark = " ✅" if bid == user["selected_brawler"] else ""
        lines.append(f"{RARITY_EMOJI[data['rarity']]} {data['emoji']} <b>{data['name']}</b> ур.{owned[bid]}{mark}")
    lines.append("\nВыбери бравлера на бой:")
    await message.answer("\n".join(lines), reply_markup=brawler_select_kb(owned), parse_mode="HTML")


@dp.callback_query(F.data.startswith("select_"))
async def cb_select(callback: CallbackQuery):
    bid = int(callback.data.split("_")[1])
    owned = await get_user_brawlers(callback.from_user.id)
    if bid not in owned:
        await callback.answer("Нет такого бравлера", show_alert=True)
        return
    await update_user(callback.from_user.id, selected_brawler=bid)
    data = BRAWLERS[bid]
    await callback.answer(f"Выбран {data['name']}!")
    await callback.message.edit_text(
        f"✅ На бой идёт {data['emoji']} <b>{data['name']}</b> ур.{owned[bid]}",
        parse_mode="HTML"
    )


@dp.message(F.text == "⬆️ Прокачка")
async def cmd_upgrade(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    owned = await get_user_brawlers(message.from_user.id)
    text = f"⬆️ <b>Прокачка</b>\n\n💰 {user['coins']} | ⚡ {user['power_points']}\n\nВыбери бравлера:"
    await message.answer(text, reply_markup=upgrade_kb(owned), parse_mode="HTML")


@dp.callback_query(F.data.startswith("upgrade_"))
async def cb_upgrade(callback: CallbackQuery):
    bid = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    user = await get_user(user_id)
    owned = await get_user_brawlers(user_id)
    if bid not in owned or owned[bid] >= 11:
        await callback.answer("Нельзя прокачать", show_alert=True)
        return
    level = owned[bid]
    cost_c, cost_pp = UPGRADE_COST[level]
    if user["coins"] < cost_c or user["power_points"] < cost_pp:
        await callback.answer(f"Нужно {cost_c}💰 и {cost_pp}⚡", show_alert=True)
        return
    await set_brawler_level(user_id, bid, level + 1)
    await update_user(user_id, coins=user["coins"] - cost_c, power_points=user["power_points"] - cost_pp)
    await update_quest(user_id, "upgrade")
    await check_achievements(user_id)
    owned[bid] = level + 1
    data = BRAWLERS[bid]
    await callback.answer(f"{data['name']} теперь ур.{level+1}!")
    user = await get_user(user_id)
    text = f"⬆️ <b>Прокачка</b>\n\n💰 {user['coins']} | ⚡ {user['power_points']}\n\n✅ {data['emoji']} {data['name']} → ур.{level+1}"
    await callback.message.edit_text(text, reply_markup=upgrade_kb(owned), parse_mode="HTML")


@dp.message(F.text == "🛒 Магазин")
async def cmd_shop(message: Message):
    user = await get_user(message.from_user.id)
    text = (
        f"🛒 <b>Магазин BrawlFight</b>\n\n"
        f"💎 Кристаллы: {user['crystals']}\n"
        f"💰 Монеты: {user['coins']}\n\n"
        f"Выбери товар:"
    )
    await message.answer(text, reply_markup=shop_kb(), parse_mode="HTML")


@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy(callback: CallbackQuery):
    item_key = callback.data.replace("buy_", "")
    result = await buy_item(callback.from_user.id, item_key)
    await callback.answer(result[:200], show_alert=True)
    user = await get_user(callback.from_user.id)
    text = f"🛒 <b>Магазин</b>\n\n💎 {user['crystals']} | 💰 {user['coins']}\n\nВыбери товар:"
    await callback.message.edit_text(text, reply_markup=shop_kb(), parse_mode="HTML")


@dp.message(F.text == "📋 Задания")
async def cmd_quests(message: Message):
    text = await show_quests(message.from_user.id)
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "🏅 Достижения")
async def cmd_achievements(message: Message):
    await check_achievements(message.from_user.id)
    text = await show_achievements(message.from_user.id)
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "🎁 Открыть кейс")
async def cmd_case(message: Message):
    user = await get_user(message.from_user.id)
    buttons = []
    if user["cases"] > 0:
        buttons.append([InlineKeyboardButton(text=f"🎁 Обычный ({user['cases']})", callback_data="open_normal")])
    if user.get("cases_epic", 0) > 0:
        buttons.append([InlineKeyboardButton(text=f"🎁 Эпический ({user['cases_epic']})", callback_data="open_epic")])
    if user.get("cases_legend", 0) > 0:
        buttons.append([InlineKeyboardButton(text=f"🎁 Легендарный ({user['cases_legend']})", callback_data="open_legend")])
    if not buttons:
        await message.answer("У тебя нет кейсов 🎁\nИграй бои или купи в магазине!")
        return
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
    await message.answer("Какой кейс открыть?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.callback_query(F.data.startswith("open_"))
async def cb_open_case(callback: CallbackQuery):
    case_type = callback.data.replace("open_", "")
    result, img_url = await open_case(callback.from_user.id, case_type)
    await callback.answer()
    if img_url:
        try:
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=img_url,
                caption=result,
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(result, parse_mode="HTML")
    else:
        try:
            await callback.message.edit_text(result, parse_mode="HTML")
        except Exception:
            await callback.message.answer(result, parse_mode="HTML")


@dp.message(F.text == "📜 История")
async def cmd_history(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    history = json.loads(user.get("battle_history") or "[]")
    if not history:
        await message.answer("📜 История боёв пуста.\nСыграй несколько боёв!")
        return
    lines = ["📜 <b>Последние бои</b>\n"]
    for h in history:
        res = "✅" if h["result"] == "win" else "❌"
        mode = "🏆" if h.get("mode") == "ranked" else "⚔️"
        tr = h["trophies"]
        tr_str = f"+{tr}" if tr > 0 else str(tr)
        lines.append(f"{res} {mode} {h['my']} vs {h['opp']}  ({tr_str}🏆)  <i>{h['time']}</i>")
    await message.answer("\n".join(lines), parse_mode="HTML")


# ===== Сезонный пропуск =====
SEASON_REWARDS = {
    1:  {"xp": 50,  "coins": 100, "crystals": 0, "cases": 0},
    2:  {"xp": 120, "coins": 150, "crystals": 1, "cases": 0},
    3:  {"xp": 200, "coins": 0,   "crystals": 0, "cases": 1},
    4:  {"xp": 300, "coins": 200, "crystals": 2, "cases": 0},
    5:  {"xp": 420, "coins": 0,   "crystals": 3, "cases": 0},
    6:  {"xp": 550, "coins": 250, "crystals": 0, "cases": 1},
    7:  {"xp": 700, "coins": 0,   "crystals": 5, "cases": 0},
    8:  {"xp": 880, "coins": 300, "crystals": 0, "cases": 0},
    9:  {"xp": 1100,"coins": 0,   "crystals": 0, "cases": 1},
    10: {"xp": 1400,"coins": 500, "crystals": 10,"cases": 0},
}


@dp.message(F.text == "🎟 Пропуск")
async def cmd_season(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    xp = user.get("season_xp") or 0
    claimed = json.loads(user.get("season_claimed") or "[]")

    lines = [f"🎟 <b>Сезонный пропуск</b>\n\nОпыт сезона: <b>{xp}</b> XP\n"]
    for lvl, reward in SEASON_REWARDS.items():
        status = "✅" if lvl in claimed else ("🔓" if xp >= reward["xp"] else "🔒")
        parts = []
        if reward["coins"]:
            parts.append(f"{reward['coins']}💰")
        if reward["crystals"]:
            parts.append(f"{reward['crystals']}💎")
        if reward["cases"]:
            parts.append(f"{reward['cases']}🎁")
        lines.append(f"{status} Ур.{lvl} ({reward['xp']} XP) — {' + '.join(parts)}")

    # Кнопки для клейма
    buttons = []
    for lvl, reward in SEASON_REWARDS.items():
        if lvl not in claimed and xp >= reward["xp"]:
            buttons.append([InlineKeyboardButton(text=f"Забрать ур.{lvl}", callback_data=f"season_claim_{lvl}")])
    if buttons:
        buttons.append([InlineKeyboardButton(text="« Закрыть", callback_data="back_main")])
        await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    else:
        await message.answer("\n".join(lines) + "\n\nИграй бои, чтобы получать XP сезона!", parse_mode="HTML")


@dp.callback_query(F.data.startswith("season_claim_"))
async def cb_season_claim(callback: CallbackQuery):
    lvl = int(callback.data.split("_")[-1])
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка", show_alert=True)
        return
    xp = user.get("season_xp") or 0
    claimed = json.loads(user.get("season_claimed") or "[]")
    if lvl in claimed:
        await callback.answer("Уже получено", show_alert=True)
        return
    reward = SEASON_REWARDS.get(lvl)
    if not reward or xp < reward["xp"]:
        await callback.answer("Ещё не доступно", show_alert=True)
        return

    claimed.append(lvl)
    await update_user(
        callback.from_user.id,
        coins=user["coins"] + reward["coins"],
        crystals=user["crystals"] + reward["crystals"],
        cases=user["cases"] + reward["cases"],
        season_claimed=json.dumps(claimed)
    )
    await callback.answer(f"Получена награда ур.{lvl}!", show_alert=True)
    try:
        await callback.message.edit_text(
            f"✅ Награда уровня {lvl} получена!\n\nНажми «🎟 Пропуск» снова, чтобы увидеть прогресс.",
            parse_mode="HTML"
        )
    except Exception:
        pass



@dp.message(F.text == "📅 Топ недели")
@dp.message(Command("weekly"))
async def cmd_weekly(message: Message):
    from datetime import timedelta
    week_key = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Сброс чужих недель не делаем массово — фильтруем
        async with db.execute(
            """SELECT user_id, username, nickname, weekly_wins, weekly_reset, trophies
               FROM users WHERE weekly_wins > 0 ORDER BY weekly_wins DESC LIMIT 15"""
        ) as cursor:
            rows = await cursor.fetchall()
    lines = ["📅 <b>Топ недели по победам</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    shown = 0
    for i, row in enumerate(rows, 1):
        if (row["weekly_reset"] or "") != week_key:
            continue
        shown += 1
        medal = medals[shown-1] if shown <= 3 else f"{shown}."
        name = row["nickname"] or row["username"] or "Игрок"
        lines.append(f"{medal} <b>{name}</b> — {row['weekly_wins']} побед")
        if shown >= 10:
            break
    if shown == 0:
        lines.append("Пока нет данных за эту неделю. Играй бои!")
    else:
        lines.append("\nНаграда топ-3 выдаётся в конце недели (вручную админом / через ивент).")
    # Ивент
    ev = get_active_event()
    if ev:
        left = int((ev["ends"] - time.time()) / 60)
        lines.append(f"\n🎉 Ивент: <b>{ev['name']}</b> (~{left} мин)")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(F.text == "🏆 Топ")
async def cmd_top(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, nickname, trophies, wins FROM users ORDER BY trophies DESC LIMIT 20"
        ) as cursor:
            rows = await cursor.fetchall()
        # Место игрока во всём топе
        async with db.execute(
            "SELECT COUNT(*) + 1 as place FROM users WHERE trophies > (SELECT trophies FROM users WHERE user_id = ?)",
            (user_id,)
        ) as cursor:
            place_row = await cursor.fetchone()
            my_place = place_row["place"] if place_row else "?"
        async with db.execute("SELECT COUNT(*) as cnt FROM users") as cursor:
            total_row = await cursor.fetchone()
            total_players = total_row["cnt"] if total_row else 0

    if not rows:
        await message.answer("Пока никого нет.")
        return

    lines = ["🏆 <b>Топ-20 по трофеям</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows, 1):
        medal = medals[i-1] if i <= 3 else f"{i}."
        name = row["nickname"] or row["username"] or "Игрок"
        mark = " ⬅️" if row["user_id"] == user_id else ""
        lines.append(f"{medal} <b>{name}</b> — {row['trophies']}🏆 ({row['wins']}W){mark}")

    lines.append(f"\n📍 Твоё место: <b>#{my_place}</b> из {total_players}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(F.text == "✏️ Ник")
@dp.message(Command("nick"))
async def cmd_nick(message: Message):
    await message.answer(
        "✏️ Чтобы сменить ник, напиши:\n"
        "<code>/setnick ТвойНик</code>\n\n"
        "От 2 до 16 символов. Без &lt; &gt; { } [ ]",
        parse_mode="HTML"
    )


@dp.message(Command("setnick"))
async def set_nick(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /setnick ТвойНик")
        return
    text = parts[1].strip()
    if not (2 <= len(text) <= 16):
        await message.answer("Ник должен быть от 2 до 16 символов.")
        return
    if any(ch in text for ch in "<>{}[]"):
        await message.answer("Ник содержит запрещённые символы.")
        return
    await update_user(message.from_user.id, nickname=text)
    await message.answer(f"✅ Ник изменён на: <b>{text}</b>", parse_mode="HTML")


@dp.callback_query(F.data == "back_main")
async def cb_back(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@dp.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()



@dp.message(F.text == "📖 Гайд")
@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📖 <b>Гайд по BrawlFight</b>\n\n"
        "⚔️ <b>Бой</b> — обычный или рейтинговый 1на1. Бой проходит автоматически за 3–5 сек.\n"
        "• Обычный — стандартные награды\n"
        "• Рейтинговый — больше трофеев и наград, но и штраф выше\n\n"
        "🎁 <b>Ежедневка</b> — награда раз в день. Чем дольше стрик — тем жирнее приз.\n\n"
        "👤 <b>Профиль</b> — трофеи, ранг, ресурсы, выбранный бравлер.\n\n"
        "📦 <b>Коллекция</b> — все твои бравлеры. Нажми, чтобы выбрать бойца на бой.\n\n"
        "⬆️ <b>Прокачка</b> — улучшай бравлеров за монеты и очки силы (макс. 11 ур.).\n\n"
        "🛒 <b>Магазин</b> — кейсы за кристаллы, очки силы и кристаллы за монеты.\n\n"
        "🎁 <b>Открыть кейс</b> — шанс выбить нового бравлера или ресурсы.\n\n"
        "📋 <b>Задания</b> — ежедневные квесты. Сложность зависит от твоих трофеев.\n\n"
        "🏅 <b>Достижения</b> — разовые цели с наградами.\n\n"
        "🎟 <b>Пропуск</b> — сезонный пропуск: играй бои → получай XP → забирай награды.\n\n"
        "📜 <b>История</b> — последние 10 боёв.\n\n"
        "🏆 <b>Топ</b> — топ-20 игроков и твоё место в рейтинге.\n\n"
        "✏️ <b>Ник</b> — сменить отображаемое имя: <code>/setnick Имя</code>\n\n"
        "💡 <b>Советы</b>\n"
        "• Заходи каждый день за ежедневкой\n"
        "• Прокачивай бойца перед рейтинговыми боями\n"
        "• Выполняй задания — там хорошие награды\n"
        "• Кейсы лучше копить и открывать пачкой"
    )
    await message.answer(text, parse_mode="HTML")


# ====================== РУЛЕТКА / PVE / БАШНЯ / БОСС / СУНДУК ======================
BOSS_POOL = [
    ("🤖 Мегабот", 500),
    ("🐉 Дракон Старр", 700),
    ("💀 Тёмный Мортис", 600),
    ("⚡ Кибер-Сёрдж", 650),
    ("🌵 Гига-Спайк", 550),
]

def _week_key():
    from datetime import timedelta
    return (date.today() - timedelta(days=date.today().weekday())).isoformat()


@dp.message(F.text == "🎲 Рулетка")
async def cmd_roulette(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    today = str(date.today())
    if user.get("last_roulette") == today:
        await message.answer("🎲 Рулетка уже крутилась сегодня. Приходи завтра!")
        return
    msg = await message.answer("🎲 Крутим рулетку...")
    await asyncio.sleep(1.5)
    roll = random.random() * 100
    if roll < 5:
        reward = ("💎 ДЖЕКПОТ! 15 кристаллов", {"crystals": 15})
    elif roll < 15:
        reward = ("🎁 Эпический кейс", {"cases_epic": 1})
    elif roll < 30:
        reward = ("🎁 Обычный кейс", {"cases": 1})
    elif roll < 45:
        reward = ("💎 5 кристаллов", {"crystals": 5})
    elif roll < 65:
        reward = ("⚡ 150 очков силы", {"power_points": 150})
    elif roll < 85:
        reward = ("💰 200 монет", {"coins": 200})
    else:
        reward = ("💨 Пусто... в следующий раз повезёт", {})
    kw = {k: user.get(k, 0) + v for k, v in reward[1].items()}
    kw["last_roulette"] = today
    await update_user(message.from_user.id, **kw)
    await msg.edit_text(f"🎲 <b>Рулетка</b>\n\n{reward[0]}", parse_mode="HTML")


@dp.message(F.text == "🌊 Волны")
async def cmd_pve(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    owned = await get_user_brawlers(message.from_user.id)
    bid = user["selected_brawler"]
    if bid not in owned:
        bid = 1
    level = owned.get(bid, 1)
    power = BRAWLERS[bid]["base_power"] * (1 + 0.10 * (level - 1))
    b = BRAWLERS[bid]
    wave = 0
    total_coins = 0
    total_pp = 0
    keys = 0
    msg = await message.answer(f"🌊 <b>PvE Волны</b>\n{b['emoji']} {b['name']} ур.{level}\n\nНачинаем...", parse_mode="HTML")
    for w in range(1, 16):
        enemy_power = 80 + w * 18 + random.randint(-10, 15)
        await asyncio.sleep(0.7)
        if power * random.uniform(0.9, 1.1) >= enemy_power:
            wave = w
            c = 15 + w * 8
            p = 8 + w * 4
            total_coins += c
            total_pp += p
            if w % 5 == 0:
                keys += 1
            await msg.edit_text(
                f"🌊 Волна {w}/15 — ✅\nВраг: {enemy_power:.0f} | Ты: {power:.0f}\n💰 +{c}  ⚡ +{p}",
                parse_mode="HTML"
            )
        else:
            await msg.edit_text(
                f"🌊 Волна {w}/15 — ❌ Поражение\nВраг: {enemy_power:.0f} | Ты: {power:.0f}",
                parse_mode="HTML"
            )
            break
    best = max(user.get("pve_best") or 0, wave)
    await update_user(
        message.from_user.id,
        coins=user["coins"] + total_coins,
        power_points=user["power_points"] + total_pp,
        keys=(user.get("keys") or 0) + keys,
        pve_best=best,
    )
    text = (
        f"🌊 <b>Итог волн</b>\n\n"
        f"Пройдено: <b>{wave}</b> волн\n"
        f"💰 +{total_coins} монет\n"
        f"⚡ +{total_pp} очков силы\n"
    )
    if keys:
        text += f"🗝️ +{keys} ключ(ей)\n"
    text += f"🏆 Рекорд: {best} волн"
    await msg.edit_text(text, parse_mode="HTML")


@dp.message(F.text == "🗼 Башня")
async def cmd_tower(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    owned = await get_user_brawlers(message.from_user.id)
    bid = user["selected_brawler"]
    if bid not in owned:
        bid = 1
    level = owned.get(bid, 1)
    power = BRAWLERS[bid]["base_power"] * (1 + 0.10 * (level - 1))
    floor = user.get("tower_floor") or 1
    b = BRAWLERS[bid]
    enemy = 90 + floor * 22
    msg = await message.answer(
        f"🗼 <b>Башня — этаж {floor}</b>\n{b['emoji']} {b['name']} vs враг ({enemy} силы)\n\n⚔️ Бой...",
        parse_mode="HTML"
    )
    await asyncio.sleep(1.8)
    win = power * random.uniform(0.88, 1.12) >= enemy
    if win:
        coins = 30 + floor * 12
        pp = 15 + floor * 6
        keys = 1 if floor % 3 == 0 else 0
        new_floor = floor + 1
        best = max(user.get("tower_best") or 0, floor)
        kw = dict(
            coins=user["coins"] + coins,
            power_points=user["power_points"] + pp,
            tower_floor=new_floor,
            tower_best=best,
        )
        if keys:
            kw["keys"] = (user.get("keys") or 0) + keys
        await update_user(message.from_user.id, **kw)
        text = (
            f"🗼 <b>Этаж {floor} пройден!</b> ✅\n\n"
            f"💰 +{coins}  ⚡ +{pp}\n"
        )
        if keys:
            text += f"🗝️ +1 ключ\n"
        text += f"Следующий этаж: <b>{new_floor}</b>\nРекорд: {best}"
    else:
        # soft reset a bit
        new_floor = max(1, floor - 1)
        await update_user(message.from_user.id, tower_floor=new_floor)
        text = (
            f"🗼 <b>Этаж {floor} — поражение</b> ❌\n\n"
            f"Враг оказался сильнее.\n"
            f"Откат на этаж <b>{new_floor}</b>.\n"
            f"Прокачай бравлера и попробуй снова!"
        )
    await msg.edit_text(text, parse_mode="HTML")


@dp.message(F.text == "👹 Босс")
async def cmd_boss(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    wk = _week_key()
    # фиксированный босс недели
    boss_idx = hash(wk) % len(BOSS_POOL)
    boss_name, boss_hp = BOSS_POOL[boss_idx]
    owned = await get_user_brawlers(message.from_user.id)
    bid = user["selected_brawler"]
    if bid not in owned:
        bid = 1
    level = owned.get(bid, 1)
    power = BRAWLERS[bid]["base_power"] * (1 + 0.10 * (level - 1))
    damage = int(power * random.uniform(0.7, 1.3) + level * 5)
    prev = user.get("boss_damage") or 0
    if user.get("boss_week") != wk:
        prev = 0
    total = prev + damage
    coins = damage // 3
    pp = damage // 5
    keys = 1 if damage >= 150 else 0
    await update_user(
        message.from_user.id,
        coins=user["coins"] + coins,
        power_points=user["power_points"] + pp,
        keys=(user.get("keys") or 0) + keys,
        boss_damage=total,
        boss_week=wk,
    )
    pct = min(100, int(total / boss_hp * 100))
    text = (
        f"👹 <b>Арена босса</b>\n\n"
        f"Босс недели: <b>{boss_name}</b>\n"
        f"HP: {boss_hp}\n\n"
        f"Твой удар: <b>{damage}</b> урона\n"
        f"Всего за неделю: <b>{total}</b> ({pct}%)\n\n"
        f"💰 +{coins}  ⚡ +{pp}"
    )
    if keys:
        text += f"\n🗝️ +1 ключ"
    if total >= boss_hp:
        text += "\n\n🏆 Босс повержен! (личный прогресс)"
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "🗝️ Сундук")
async def cmd_key_chest(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    keys = user.get("keys") or 0
    if keys < 3:
        await message.answer(
            f"🗝️ Нужно <b>3 ключа</b>, чтобы открыть сундук.\n"
            f"У тебя: <b>{keys}</b>\n\n"
            f"Ключи падают с волн, башни и босса.",
            parse_mode="HTML"
        )
        return
    await update_user(message.from_user.id, keys=keys - 3)
    roll = random.random() * 100
    if roll < 8:
        text = "🗝️ Сундук: 💎 12 кристаллов!"
        await update_user(message.from_user.id, crystals=user["crystals"] + 12)
    elif roll < 25:
        text = "🗝️ Сундук: 🎁 Эпический кейс!"
        await update_user(message.from_user.id, cases_epic=user.get("cases_epic", 0) + 1)
    elif roll < 50:
        text = "🗝️ Сундук: 🎁 2 обычных кейса!"
        await update_user(message.from_user.id, cases=user["cases"] + 2)
    elif roll < 75:
        text = "🗝️ Сундук: 💰 350 монет + ⚡ 100 силы!"
        await update_user(message.from_user.id, coins=user["coins"] + 350, power_points=user["power_points"] + 100)
    else:
        text = "🗝️ Сундук: 💰 180 монет"
        await update_user(message.from_user.id, coins=user["coins"] + 180)
    await message.answer(text)


# ====================== АДМИН ======================
@dp.message(Command("myid"))
async def cmd_myid(message: Message):
    await message.answer(f"Твой Telegram ID: <code>{message.from_user.id}</code>", parse_mode="HTML")


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await require_admin(message):
        return
    await message.answer(
        "🛠 <b>Админ-панель</b>\n\n"
        "/backup — скачать базу данных\n"
        "/restore — ответь этой командой на файл .db для восстановления\n"
        "/stats — общая статистика бота\n"
        "/myid — узнать свой ID",
        parse_mode="HTML"
    )


@dp.message(Command("backup"))
async def cmd_backup(message: Message):
    if not await require_admin(message):
        return
    if not os.path.exists(DB_PATH):
        await message.answer("Файл базы не найден")
        return
    try:
        doc = FSInputFile(DB_PATH, filename="brawl_bot_backup.db")
        await message.answer_document(doc, caption="📦 Бэкап базы BrawlFight")
    except Exception as e:
        await message.answer(f"Ошибка бэкапа: {e}")


@dp.message(Command("restore"))
async def cmd_restore(message: Message):
    if not await require_admin(message):
        return
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.answer(
            "Чтобы восстановить базу:\n"
            "1. Отправь файл .db боту\n"
            "2. Ответь на это сообщение командой /restore"
        )
        return
    doc = message.reply_to_message.document
    try:
        file = await bot.get_file(doc.file_id)
        data = await bot.download_file(file.file_path)
        content = data.read()
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        with open(DB_PATH, "wb") as f:
            f.write(content)
        await message.answer("✅ База восстановлена! Перезапусти бота (Redeploy), чтобы точно подхватило.")
    except Exception as e:
        await message.answer(f"Ошибка восстановления: {e}")


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if not await require_admin(message):
        return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            users = (await cur.fetchone())[0]
        async with db.execute("SELECT SUM(wins), SUM(losses) FROM users") as cur:
            row = await cur.fetchone()
            wins, losses = row[0] or 0, row[1] or 0
        async with db.execute("SELECT COUNT(*) FROM user_brawlers") as cur:
            brawlers = (await cur.fetchone())[0]
    await message.answer(
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Игроков: {users}\n"
        f"⚔️ Побед / поражений: {wins} / {losses}\n"
        f"📦 Всего бравлеров у игроков: {brawlers}",
        parse_mode="HTML"
    )


@dp.message()
async def fallback(message: Message):
    await message.answer("Используй кнопки меню 👇", reply_markup=main_kb())


# ====================== ЗАПУСК ======================

async def main():
    # Создаём папку для базы, если её нет (для Railway Volume)
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    await init_db()
    print("BrawlFight бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
