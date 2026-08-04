"""Сезонный пропуск."""
import json

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from data.constants import SEASON_REWARDS
from db import get_user, update_user

router = Router()


@router.message(F.text == "🎟 Пропуск")
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

    buttons = []
    for lvl, reward in SEASON_REWARDS.items():
        if lvl not in claimed and xp >= reward["xp"]:
            buttons.append([InlineKeyboardButton(text=f"Забрать ур.{lvl}", callback_data=f"season_claim_{lvl}")])
    if buttons:
        buttons.append([InlineKeyboardButton(text="« Закрыть", callback_data="back_main")])
        await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    else:
        await message.answer("\n".join(lines) + "\n\nИграй бои, чтобы получать XP сезона!", parse_mode="HTML")


@router.callback_query(F.data.startswith("season_claim_"))
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
