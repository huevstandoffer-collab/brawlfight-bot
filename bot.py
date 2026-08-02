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
)
from aiogram.fsm.storage.memory import MemoryStorage

# ====================== НАСТРОЙКИ ======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8720173063:AAHmE_D0g2g0hFgtEUjcWg6l-IjN1Zmz0Y4")
DB_PATH = "brawl_bot.db"

BATTLE_COOLDOWN = 12
CASE_DROP_CHANCE = 22

# ====================== БРАВЛЕРЫ ======================
BRAWLERS = {
    1:  {"name": "Shelly",      "rarity": "Starting",   "base_power": 100, "emoji": "🔫", "img_id": 16000000},
    2:  {"name": "Colt",        "rarity": "Rare",       "base_power": 110, "emoji": "🤠", "img_id": 16000001},
    3:  {"name": "Nita",        "rarity": "Rare",       "base_power": 105, "emoji": "🐻", "img_id": 16000008},
    4:  {"name": "Bull",        "rarity": "Rare",       "base_power": 120, "emoji": "🐂", "img_id": 16000002},
    5:  {"name": "Jessie",      "rarity": "Super Rare", "base_power": 115, "emoji": "🔧", "img_id": 16000007},
    6:  {"name": "Brock",       "rarity": "Rare",       "base_power": 112, "emoji": "🚀", "img_id": 16000003},
    7:  {"name": "Dynamike",    "rarity": "Super Rare", "base_power": 108, "emoji": "💣", "img_id": 16000009},
    8:  {"name": "Bo",          "rarity": "Epic",       "base_power": 118, "emoji": "🏹", "img_id": 16000014},
    9:  {"name": "Tick",        "rarity": "Super Rare", "base_power": 105, "emoji": "🧨", "img_id": 16000022},
    10: {"name": "8-Bit",       "rarity": "Super Rare", "base_power": 125, "emoji": "👾", "img_id": 16000027},
    11: {"name": "Emz",         "rarity": "Epic",       "base_power": 115, "emoji": "💅", "img_id": 16000030},
    12: {"name": "El Primo",    "rarity": "Rare",       "base_power": 130, "emoji": "💪", "img_id": 16000010},
    13: {"name": "Barley",      "rarity": "Rare",       "base_power": 107, "emoji": "🍺", "img_id": 16000006},
    14: {"name": "Poco",        "rarity": "Rare",       "base_power": 110, "emoji": "🎸", "img_id": 16000013},
    15: {"name": "Rosa",        "rarity": "Rare",       "base_power": 125, "emoji": "🌿", "img_id": 16000024},
    16: {"name": "Rico",        "rarity": "Super Rare", "base_power": 113, "emoji": "🤖", "img_id": 16000004},
    17: {"name": "Darryl",      "rarity": "Super Rare", "base_power": 122, "emoji": "🛢️", "img_id": 16000018},
    18: {"name": "Penny",       "rarity": "Super Rare", "base_power": 114, "emoji": "🏴‍☠️", "img_id": 16000019},
    19: {"name": "Carl",        "rarity": "Super Rare", "base_power": 117, "emoji": "⛏️", "img_id": 16000025},
    20: {"name": "Jacky",       "rarity": "Super Rare", "base_power": 128, "emoji": "🔧", "img_id": 16000034},
    21: {"name": "Piper",       "rarity": "Epic",       "base_power": 120, "emoji": "🎯", "img_id": 16000015},
    22: {"name": "Pam",         "rarity": "Epic",       "base_power": 119, "emoji": "🛠️", "img_id": 16000016},
    23: {"name": "Frank",       "rarity": "Epic",       "base_power": 140, "emoji": "🔨", "img_id": 16000020},
    24: {"name": "Gene",        "rarity": "Mythic",     "base_power": 125, "emoji": "🧞", "img_id": 16000021},
    25: {"name": "Mortis",      "rarity": "Mythic",     "base_power": 130, "emoji": "🦇", "img_id": 16000011},
    26: {"name": "Tara",        "rarity": "Mythic",     "base_power": 128, "emoji": "🃏", "img_id": 16000017},
    27: {"name": "Spike",       "rarity": "Legendary",  "base_power": 135, "emoji": "🌵", "img_id": 16000005},
    28: {"name": "Crow",        "rarity": "Legendary",  "base_power": 132, "emoji": "🐦‍⬛", "img_id": 16000012},
    29: {"name": "Leon",        "rarity": "Legendary",  "base_power": 140, "emoji": "🥷", "img_id": 16000023},
    30: {"name": "Surge",       "rarity": "Legendary",  "base_power": 138, "emoji": "⚡", "img_id": 16000043},
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
    1: (20, 10), 2: (35, 20), 3: (55, 35), 4: (80, 55),
    5: (120, 80), 6: (170, 120), 7: (240, 170),
    8: (330, 240), 9: (450, 330), 10: (600, 450),
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
            [KeyboardButton(text="🎁 Открыть кейс"), KeyboardButton(text="🏆 Топ")],
        ],
        resize_keyboard=True
    )


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
    if streak >= 7:
        crystals += 2
    cases = 1 if streak % 3 == 0 else 0

    new_coins = user["coins"] + coins
    new_pp = user["power_points"] + pp
    new_crystals = user["crystals"] + crystals
    new_cases = user["cases"] + cases

    await update_user(
        user_id,
        coins=new_coins,
        power_points=new_pp,
        crystals=new_crystals,
        cases=new_cases,
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
    text += f"\nЗавтра награда будет ещё больше!"
    return text


# ====================== ЗАДАНИЯ ======================
def get_default_quests():
    return {
        "battles": 0,
        "wins": 0,
        "upgrade": 0,
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
    quests = await get_quests(user_id)
    battles = min(quests.get("battles", 0), 5)
    wins = min(quests.get("wins", 0), 3)
    upgrade = min(quests.get("upgrade", 0), 1)
    reward_claimed = quests.get("reward_claimed", False)

    text = (
        f"📋 <b>Задания на сегодня</b>\n\n"
        f"{'✅' if battles >= 5 else '🔲'} Сыграть 5 боёв          ({battles}/5)\n"
        f"{'✅' if wins >= 3 else '🔲'} Выиграть 3 боя          ({wins}/3)\n"
        f"{'✅' if upgrade >= 1 else '🔲'} Прокачать бравлера     ({upgrade}/1)\n\n"
    )

    # Если все задания выполнены и награда ещё не выдана — выдаём сразу
    if battles >= 5 and wins >= 3 and upgrade >= 1 and not reward_claimed:
        user = await get_user(user_id)
        await update_user(
            user_id,
            coins=user["coins"] + 250,
            cases_epic=user.get("cases_epic", 0) + 1
        )
        quests["reward_claimed"] = True
        await update_user(user_id, quests=json.dumps(quests))

        text += (
            "🎉 <b>Все задания выполнены!</b>\n\n"
            "Ты получил награду:\n"
            "💰 +250 монет\n"
            "🎁 +1 Эпический кейс"
        )
    elif reward_claimed:
        text += "✅ Награда за задания уже получена сегодня."
    else:
        text += "Награда за все задания:\n💰 250 монет + 🎁 Эпический кейс"

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


async def do_battle_animated(message: Message):
    user_id = message.from_user.id
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
        opp_name = opponent["username"] or f"Игрок"
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

    # Награды
    coins_gain = random.randint(28, 48) if i_win else random.randint(12, 26)
    pp_gain = random.randint(16, 32) if i_win else random.randint(8, 18)
    trophies_change = random.randint(9, 16) if i_win else -random.randint(5, 12)
    crystals_gain = 1 if (i_win and random.random() < 0.13) else 0
    case_dropped = random.random() * 100 < CASE_DROP_CHANCE

    new_trophies = max(0, user["trophies"] + trophies_change)
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
    )

    # Обновляем задания
    await update_quest(user_id, "battles")
    if i_win:
        await update_quest(user_id, "wins")

    # Проверяем достижения
    new_achs = await check_achievements(user_id)

    result_emoji = "🏆 <b>ПОБЕДА!</b>" if i_win else "💀 <b>Поражение</b>"
    text = (
        f"{result_emoji}\n\n"
        f"{my_brawler['emoji']} <b>{my_brawler['name']}</b> ур.{my_level} — {my_power:.0f} силы\n"
        f"{opp_emoji} <b>{opp_name}</b> — {opp_power:.0f} силы\n\n"
        f"📊 Награды:\n"
        f"💰 +{coins_gain} монет\n"
        f"⚡ +{pp_gain} очков силы\n"
        f"🏆 {'+' if trophies_change > 0 else ''}{trophies_change} трофеев (всего {new_trophies})\n"
    )
    if crystals_gain:
        text += f"💎 +{crystals_gain} кристалл\n"
    if case_dropped:
        text += f"\n🎁 <b>Выпал кейс!</b>"

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
        rarity_chances = [(45, "currency"), (30, "Rare"), (15, "Super Rare"), (7, "Epic"), (2.5, "Mythic"), (0.5, "Legendary")]
    elif case_type == "epic":
        if user.get("cases_epic", 0) < 1:
            return "У тебя нет эпических кейсов 🎁", None
        await update_user(user_id, cases_epic=user.get("cases_epic", 0) - 1)
        rarity_chances = [(20, "currency"), (25, "Super Rare"), (30, "Epic"), (18, "Mythic"), (7, "Legendary")]
    else:
        if user.get("cases_legend", 0) < 1:
            return "У тебя нет легендарных кейсов 🎁", None
        await update_user(user_id, cases_legend=user.get("cases_legend", 0) - 1)
        rarity_chances = [(10, "currency"), (20, "Epic"), (35, "Mythic"), (35, "Legendary")]

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
    await do_battle_animated(message)


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
    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"🏅 Ранг: <b>{rank}</b>\n"
        f"🏆 Трофеи: <b>{user['trophies']}</b>\n"
        f"🔥 Стрик: <b>{user.get('streak', 0)}</b> дней\n"
        f"💰 Монеты: <b>{user['coins']}</b>\n"
        f"⚡ Очки силы: <b>{user['power_points']}</b>\n"
        f"💎 Кристаллы: <b>{user['crystals']}</b>\n"
        f"🎁 Кейсы: {user['cases']} обыч. | {user.get('cases_epic',0)} эпик | {user.get('cases_legend',0)} лег.\n\n"
        f"🔫 Выбран: {selected['emoji']} <b>{selected['name']}</b> ур.{level}\n"
        f"📦 Бравлеров: <b>{len(owned)}</b>/30\n"
        f"📊 {user['wins']}W / {user['losses']}L ({winrate}%)"
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


@dp.message(F.text == "🏆 Топ")
async def cmd_top(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT username, trophies, wins FROM users ORDER BY trophies DESC LIMIT 10") as cursor:
            rows = await cursor.fetchall()
    if not rows:
        await message.answer("Пока никого нет.")
        return
    lines = ["🏆 <b>Топ-10 по трофеям</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows, 1):
        medal = medals[i-1] if i <= 3 else f"{i}."
        lines.append(f"{medal} <b>{row['username'] or 'Игрок'}</b> — {row['trophies']}🏆 ({row['wins']}W)")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.callback_query(F.data == "back_main")
async def cb_back(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@dp.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


@dp.message()
async def fallback(message: Message):
    await message.answer("Используй кнопки меню 👇", reply_markup=main_kb())


# ====================== ЗАПУСК ======================
async def main():
    await init_db()
    print("BrawlFight бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
