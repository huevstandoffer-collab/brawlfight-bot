"""Ежедневки, задания, достижения."""
import json
import time
from datetime import date

from db import get_user, update_user, get_user_brawlers
from data.constants import ACHIEVEMENTS
from game.events import get_active_event


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


