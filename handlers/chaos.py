"""Хаос: Мне повезёт, война эмодзи, укради очко."""
from __future__ import annotations

import random
import time
from datetime import date

import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import DB_PATH
from data.brawlers import BRAWLERS
from db import get_user, update_user, add_brawler, get_user_brawlers
from game.chaos import get_war_status, vote_war, get_glitch_status

router = Router()


def _today() -> str:
    return str(date.today())


# ─── 6. Мне повезёт ─────────────────────────────────────────

@router.message(F.text == "🎲 Мне повезёт")
async def cmd_lucky(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return

    last = user.get("last_lucky") or ""
    if last == _today():
        await message.answer("🎲 Сегодня уже крутил «Мне повезёт». Завтра снова!")
        return

    msg = await message.answer("🎲 Крутим судьбу...")
    await _sleep()
    roll = random.random() * 100

    # Исходы (примерно)
    # 08%  +400..600 монет
    # 10%  +5..10 кристаллов
    # 08%  обычный кейс
    # 04%  эпик кейс
    # 05%  +50..100 трофеев
    # 10%  −50..120 монет
    # 05%  −10..25 трофеев
    # 04%  телепорт башни −1..3 этажа
    # 03%  случайный Rare/SR бравлер если нет
    # 03%  титул-ник префикс (просто сообщение + мелкий бонус)
    # rest пусто / мелочь

    text = "🎲 <b>Мне повезёт</b>\n\n"
    kw = {"last_lucky": _today()}

    if roll < 8:
        gain = random.randint(400, 600)
        kw["coins"] = user["coins"] + gain
        text += f"💎 ДЖЕКПОТ МОНЕТ!\n💰 +{gain}"
    elif roll < 18:
        gain = random.randint(5, 10)
        kw["crystals"] = user["crystals"] + gain
        text += f"✨ Кристальный дождь!\n💎 +{gain}"
    elif roll < 26:
        kw["cases"] = user["cases"] + 1
        text += "🎁 Обычный кейс!"
    elif roll < 30:
        kw["cases_epic"] = user.get("cases_epic", 0) + 1
        text += "🎁 Эпический кейс!"
    elif roll < 35:
        gain = random.randint(50, 100)
        kw["trophies"] = user["trophies"] + gain
        text += f"🏆 Трофейный взрыв!\n🏆 +{gain}"
    elif roll < 45:
        lost = min(user["coins"], random.randint(50, 120))
        kw["coins"] = user["coins"] - lost
        text += f"💀 Не повезло...\n💰 −{lost}"
    elif roll < 50:
        lost = min(user["trophies"], random.randint(10, 25))
        kw["trophies"] = user["trophies"] - lost
        text += f"📉 Трофеи укатили\n🏆 −{lost}"
    elif roll < 54:
        floor = user.get("tower_floor") or 1
        drop = random.randint(1, 3)
        new_floor = max(1, floor - drop)
        kw["tower_floor"] = new_floor
        text += f"🗼 Телепорт вниз по башне!\nЭтаж {floor} → {new_floor}"
    elif roll < 57:
        owned = await get_user_brawlers(message.from_user.id)
        candidates = [
            bid for bid, d in BRAWLERS.items()
            if d["rarity"] in ("Rare", "Super Rare") and bid not in owned
        ]
        if candidates:
            bid = random.choice(candidates)
            await add_brawler(message.from_user.id, bid, 1)
            d = BRAWLERS[bid]
            text += f"🎉 Новый бравлер!\n{d['emoji']} <b>{d['name']}</b> ({d['rarity']})"
        else:
            gain = random.randint(80, 150)
            kw["coins"] = user["coins"] + gain
            text += f"Все редкие уже есть → 💰 +{gain}"
    elif roll < 60:
        gain = random.randint(30, 60)
        kw["coins"] = user["coins"] + gain
        text += f"🍀 Мелочь, но приятно\n💰 +{gain}"
    else:
        text += "💨 Пусто. Вселенная промолчала."

    await update_user(message.from_user.id, **kw)
    await msg.edit_text(text, parse_mode="HTML")


async def _sleep():
    import asyncio
    await asyncio.sleep(1.2)


# ─── 7. Война эмодзи ────────────────────────────────────────

@router.message(F.text == "🌵 Война")
async def cmd_war(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return

    st = get_war_status()
    gl = get_glitch_status()

    if st["active"]:
        left = int(st["ends"] - time.time())
        text = (
            "🌵 <b>Война эмодзи</b> — СЕЙЧАС\n\n"
            f"🌵 Кактусы: <b>{st['cactus']}</b>\n"
            f"🔫 Стрелки: <b>{st['gun']}</b>\n"
            f"До конца: ~{left // 60}м {left % 60}с\n\n"
            "Победившая сторона получит <b>x2 монеты и PP</b> на час после войны.\n"
            "Выбери сторону:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🌵 Кактусы", callback_data="war_cactus"),
            InlineKeyboardButton(text="🔫 Стрелки", callback_data="war_gun"),
        ]])
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        left = int(max(0, st["next_at"] - time.time()))
        buff = ""
        if st["buff_side"] and st["buff_ends"] > time.time():
            bl = int(st["buff_ends"] - time.time())
            side = "🌵 Кактусы" if st["buff_side"] == "cactus" else "🔫 Стрелки"
            buff = f"\n\n🔥 Бафф: <b>{side}</b> x2 ещё ~{bl // 60} мин"
        text = (
            "🌵 <b>Война эмодзи</b>\n\n"
            "Сейчас перемирие.\n"
            f"Следующая война через ~{left // 60} мин."
            f"{buff}\n\n"
            "Когда начнётся — жми 🌵 или 🔫. Чья сторона наберёт больше голосов, "
            "той x2 награды с боёв на час."
        )
        if gl["active"]:
            gl_left = int(gl["ends"] - time.time())
            text += f"\n\n🐛 Сейчас ещё и <b>ГЛЮЧНЫЙ РЕЖИМ</b> (~{gl_left // 60}м)!"
        await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.in_({"war_cactus", "war_gun"}))
async def cb_war_vote(callback: CallbackQuery):
    side = "cactus" if callback.data == "war_cactus" else "gun"
    # один голос на войну на игрока — храним в last_war_vote timestamp window
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала /start", show_alert=True)
        return

    st = get_war_status()
    if not st["active"]:
        await callback.answer("Война уже закончилась", show_alert=True)
        return

    # анти-спам: 1 голос в 30 сек с игрока (можно много, но не флуд)
    last = float(user.get("last_war_vote") or 0)
    now = time.time()
    if now - last < 30:
        await callback.answer(f"Подожди {int(30 - (now - last))} сек", show_alert=True)
        return

    ok, msg = vote_war(side)
    if ok:
        await update_user(
            callback.from_user.id,
            last_war_vote=now,
            war_side=side,
        )
    await callback.answer(msg[:200], show_alert=True)
    try:
        st2 = get_war_status()
        if st2["active"]:
            left = int(st2["ends"] - time.time())
            await callback.message.edit_text(
                "🌵 <b>Война эмодзи</b> — СЕЙЧАС\n\n"
                f"🌵 Кактусы: <b>{st2['cactus']}</b>\n"
                f"🔫 Стрелки: <b>{st2['gun']}</b>\n"
                f"До конца: ~{left // 60}м {left % 60}с\n\n"
                "Жми снова через 30 сек, если хочешь ещё голос!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="🌵 Кактусы", callback_data="war_cactus"),
                    InlineKeyboardButton(text="🔫 Стрелки", callback_data="war_gun"),
                ]]),
                parse_mode="HTML",
            )
    except Exception:
        pass


# ─── 9. Укради очко ─────────────────────────────────────────

@router.message(F.text == "🥷 Укради очко")
async def cmd_steal(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return

    if (user.get("last_steal") or "") == _today():
        await message.answer("🥷 Сегодня уже воровал. Завтра снова.")
        return

    if user["trophies"] < 50:
        await message.answer("🥷 Нужно хотя бы 50 своих трофеев, чтобы воровать.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT user_id, username, nickname, trophies
            FROM users
            WHERE user_id != ? AND trophies >= 30
            ORDER BY trophies DESC
            LIMIT 20
            """,
            (message.from_user.id,),
        ) as cur:
            rows = await cur.fetchall()

    if not rows:
        await message.answer("🥷 Некого грабить — топ пуст.")
        return

    victim = random.choice(list(rows))
    chance = 0.30
    success = random.random() < chance
    v_name = victim["nickname"] or victim["username"] or "Игрок"

    await update_user(message.from_user.id, last_steal=_today())

    if success:
        # забрать 1 трофей
        new_v = max(0, victim["trophies"] - 1)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET trophies = ? WHERE user_id = ?",
                (new_v, victim["user_id"]),
            )
            await db.commit()
        await update_user(
            message.from_user.id,
            trophies=user["trophies"] + 1,
        )
        text = (
            f"🥷 <b>Украдено!</b>\n\n"
            f"У <b>{v_name}</b> ({victim['trophies']}🏆) спёрот 1 трофей.\n"
            f"Теперь у тебя: <b>{user['trophies'] + 1}</b>🏆"
        )
    else:
        # неудача — иногда мелкий штраф
        if random.random() < 0.35 and user["coins"] >= 20:
            await update_user(message.from_user.id, coins=user["coins"] - 20)
            text = (
                f"🥷 Поймали!\n"
                f"Цель: <b>{v_name}</b> — не вышло.\n"
                f"Штраф: 💰 −20"
            )
        else:
            text = (
                f"🥷 Мимо...\n"
                f"Цель: <b>{v_name}</b> был начеку.\n"
                f"Трофеи на месте."
            )

    await message.answer(text, parse_mode="HTML")
