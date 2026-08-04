"""Логика боёв."""
import asyncio
import json
import random
import time
from datetime import datetime, date, timedelta

from aiogram.types import Message

from config import BATTLE_COOLDOWN, CASE_DROP_CHANCE
from data.brawlers import BRAWLERS
from db import (
    get_user, update_user, get_user_brawlers, get_random_opponent,
)
from game.events import get_active_event
from game.daily import update_quest, check_achievements
from game.chaos import is_glitch_active, war_reward_mult, get_glitch_status

# Защита от спама кнопки «Бой»
_battle_locks = set()


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

    glitch = is_glitch_active()
    if glitch:
        # Баг как фича: побеждает более слабый
        i_win = my_power < opp_power
    else:
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

    # бафф войны эмодзи (x2 если твоя сторона победила)
    war_side = user.get("war_side")
    wmult = war_reward_mult(war_side)
    if wmult > 1:
        coins_gain = int(coins_gain * wmult)
        pp_gain = int(pp_gain * wmult)
        ws_bonus += f"\n🌵🔫 Война эмодзи: x{wmult:.0f} награда!"

    if glitch:
        # зеркальные трофеи чуть сильнее по модулю
        if trophies_change > 0:
            trophies_change = max(1, int(trophies_change * 1.25))
        elif trophies_change < 0:
            trophies_change = -max(1, int(abs(trophies_change) * 1.25))
        ws_bonus += "\n🐛 ГЛЮЧНЫЙ БОЙ: победил слабейший!"

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


