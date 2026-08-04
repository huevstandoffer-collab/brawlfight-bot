"""Рулетка, волны, башня, босс, сундук."""
import asyncio
import random
import time
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.types import Message

from data.brawlers import BRAWLERS
from data.constants import BOSS_POOL
from db import get_user, update_user, get_user_brawlers

router = Router()


def _week_key():
    return (date.today() - timedelta(days=date.today().weekday())).isoformat()


@router.message(F.text == "🎲 Рулетка")
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


@router.message(F.text == "🌊 Волны")
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


@router.message(F.text == "🗼 Башня")
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


@router.message(F.text == "👹 Босс")
async def cmd_boss(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return

    BOSS_HIT_CD = 30            # сек между ударами
    BOSS_RESPAWN_SEC = 15 * 60  # 15 мин после убийства

    now = time.time()
    wk = _week_key()

    prev = user.get("boss_damage") or 0
    if user.get("boss_week") != wk:
        prev = 0
        await update_user(message.from_user.id, boss_damage=0, boss_week=wk, boss_respawn_at=0)

    respawn_at = float(user.get("boss_respawn_at") or 0)
    if respawn_at > now:
        left = int(respawn_at - now)
        mins, secs = divmod(left, 60)
        await message.answer(
            f"💀 Босс повержен!\nРеспавн через <b>{mins}м {secs}с</b>.",
            parse_mode="HTML"
        )
        return
    if respawn_at and respawn_at <= now and prev > 0:
        prev = 0
        await update_user(message.from_user.id, boss_damage=0, boss_respawn_at=0)

    last_hit = float(user.get("last_boss_hit") or 0)
    if now - last_hit < BOSS_HIT_CD:
        left = int(BOSS_HIT_CD - (now - last_hit))
        await message.answer(
            f"⏳ Подожди ещё <b>{left}</b> сек. перед следующим ударом.",
            parse_mode="HTML"
        )
        return

    boss_idx = hash(wk) % len(BOSS_POOL)
    boss_name, boss_hp = BOSS_POOL[boss_idx]
    owned = await get_user_brawlers(message.from_user.id)
    bid = user["selected_brawler"]
    if bid not in owned:
        bid = 1
    level = owned.get(bid, 1)
    power = BRAWLERS[bid]["base_power"] * (1 + 0.10 * (level - 1))
    damage = int(power * random.uniform(0.7, 1.3) + level * 5)

    total = prev + damage
    killed = total >= boss_hp
    if killed:
        total = boss_hp

    coins = damage // 3
    pp = damage // 5
    keys = 1 if damage >= 150 else 0
    kill_bonus_coins = 0
    kill_bonus_crystals = 0
    if killed:
        kill_bonus_coins = 200
        kill_bonus_crystals = 3
        keys += 1

    kw = dict(
        coins=user["coins"] + coins + kill_bonus_coins,
        power_points=user["power_points"] + pp,
        keys=(user.get("keys") or 0) + keys,
        boss_damage=total,
        boss_week=wk,
        last_boss_hit=now,
    )
    if kill_bonus_crystals:
        kw["crystals"] = user["crystals"] + kill_bonus_crystals
    if killed:
        kw["boss_respawn_at"] = now + BOSS_RESPAWN_SEC
    await update_user(message.from_user.id, **kw)

    pct = min(100, int(total / boss_hp * 100))
    text = (
        f"👹 <b>Арена босса</b>\n\n"
        f"Босс недели: <b>{boss_name}</b>\n"
        f"HP: {boss_hp}\n\n"
        f"Твой удар: <b>{damage}</b> урона\n"
        f"Всего: <b>{total}</b> / {boss_hp} ({pct}%)\n\n"
        f"💰 +{coins}  ⚡ +{pp}"
    )
    if keys and not killed:
        text += "\n🗝️ +1 ключ"
    if killed:
        text += (
            f"\n\n🏆 <b>Босс повержен!</b>\n"
            f"💰 +{kill_bonus_coins}  💎 +{kill_bonus_crystals}  🗝️ +1\n"
            f"Респавн через 15 минут."
        )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🗝️ Сундук")
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


