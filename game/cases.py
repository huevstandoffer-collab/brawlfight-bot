"""Кейсы и покупки в магазине."""
import random

from data.brawlers import BRAWLERS, RARITY_EMOJI
from data.constants import SHOP_ITEMS
from db import get_user, update_user, get_user_brawlers, add_brawler
from game.daily import check_achievements


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


