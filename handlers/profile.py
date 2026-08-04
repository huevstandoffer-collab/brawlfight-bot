"""Профиль, история, топы."""
import json
from datetime import date, timedelta

import aiosqlite
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import DB_PATH
from data.brawlers import BRAWLERS, get_rank
from db import get_user, get_user_brawlers
from game.events import get_active_event
import time

router = Router()


@router.message(F.text == "👤 Профиль")
@router.message(Command("profile"))
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


@router.message(F.text == "📜 История")
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


@router.message(F.text == "📅 Топ недели")
@router.message(Command("weekly"))
async def cmd_weekly(message: Message):
    week_key = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
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
    ev = get_active_event()
    if ev:
        left = int((ev["ends"] - time.time()) / 60)
        lines.append(f"\n🎉 Ивент: <b>{ev['name']}</b> (~{left} мин)")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == "🏆 Топ")
async def cmd_top(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, nickname, trophies, wins FROM users ORDER BY trophies DESC LIMIT 20"
        ) as cursor:
            rows = await cursor.fetchall()
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
