"""Бои."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from keyboards import battle_mode_kb
from game.battle import do_battle_animated

router = Router()


@router.message(F.text == "⚔️ Бой")
@router.message(Command("battle"))
async def cmd_battle(message: Message):
    await message.answer(
        "Выбери режим боя:\n\n"
        "⚔️ <b>Обычный</b> — стандартные награды\n"
        "🏆 <b>Рейтинговый</b> — больше трофеев и наград, но и риск выше",
        reply_markup=battle_mode_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.in_({"battle_normal", "battle_ranked"}))
async def cb_battle_mode(callback: CallbackQuery):
    mode = "ranked" if callback.data == "battle_ranked" else "normal"
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await do_battle_animated(callback.message, mode=mode, user_id=callback.from_user.id)
