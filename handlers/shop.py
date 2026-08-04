"""Магазин и кейсы."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from db import get_user
from keyboards import shop_kb
from game.cases import buy_item, open_case

router = Router()


@router.message(F.text == "🛒 Магазин")
async def cmd_shop(message: Message):
    user = await get_user(message.from_user.id)
    text = (
        f"🛒 <b>Магазин BrawlFight</b>\n\n"
        f"💎 Кристаллы: {user['crystals']}\n"
        f"💰 Монеты: {user['coins']}\n\n"
        f"Выбери товар:"
    )
    await message.answer(text, reply_markup=shop_kb(), parse_mode="HTML")


@router.callback_query(F.data.startswith("buy_"))
async def cb_buy(callback: CallbackQuery):
    item_key = callback.data.replace("buy_", "")
    result = await buy_item(callback.from_user.id, item_key)
    await callback.answer(result[:200], show_alert=True)
    user = await get_user(callback.from_user.id)
    text = f"🛒 <b>Магазин</b>\n\n💎 {user['crystals']} | 💰 {user['coins']}\n\nВыбери товар:"
    await callback.message.edit_text(text, reply_markup=shop_kb(), parse_mode="HTML")


@router.message(F.text == "🎁 Открыть кейс")
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


@router.callback_query(F.data.startswith("open_"))
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
