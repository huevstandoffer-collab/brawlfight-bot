"""Работа с SQLite (aiosqlite)."""
from datetime import datetime

import aiosqlite

from config import DB_PATH


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
            ("last_boss_hit", "REAL DEFAULT 0"),
            ("boss_respawn_at", "REAL DEFAULT 0"),
            ("minigame_data", "TEXT DEFAULT '{}'"),
            ("pins", "TEXT DEFAULT '{}'"),
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


