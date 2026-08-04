"""Коллекция и прокачка."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from data.brawlers import BRAWLERS, RARITY_ORDER, RARITY_EMOJI, UPGRADE_COST
from db import get_user, update_user, get_user_brawlers, set_brawler_level
from keyboards import brawler_select_kb, upgrade_kb
from game.daily import update_quest, check_achievements

router = Router()


@router.message(F.text == "📦 Коллекция")
async def cmd_collection(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    owned = await get_user_brawlers(message.from_user.id)
    lines = ["📦 <b>Твоя коллекция</b>\n"]
    for bid in sorted(owned.keys(), key=lambda x: (RARITY_ORDER.get(BRAWLERS[x]["rarity"], 99), BRAWLERS[x]["name"])):
        data = BRAWLERS[bid]
        mark = " ✅" if bid == user["selected_brawler"] else ""
        lines.append(f"{RARITY_EMOJI.get(data['rarity'], '⚪')} {data['emoji']} <b>{data['name']}</b> ур.{owned[bid]}{mark}")
    lines.append("\nВыбери бравлера на бой:")
    await message.answer("\n".join(lines), reply_markup=brawler_select_kb(owned), parse_mode="HTML")


@router.callback_query(F.data.startswith("select_"))
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


@router.message(F.text == "⬆️ Прокачка")
async def cmd_upgrade(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    owned = await get_user_brawlers(message.from_user.id)
    text = f"⬆️ <b>Прокачка</b>\n\n💰 {user['coins']} | ⚡ {user['power_points']}\n\nВыбери бравлера:"
    await message.answer(text, reply_markup=upgrade_kb(owned), parse_mode="HTML")


@router.callback_query(F.data.startswith("upgrade_"))
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
