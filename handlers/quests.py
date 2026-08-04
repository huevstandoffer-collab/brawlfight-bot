"""Ежедневка, задания, достижения."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from game.daily import claim_daily, show_quests, show_achievements, check_achievements

router = Router()


@router.message(F.text == "🎁 Ежедневка")
@router.message(Command("daily"))
async def cmd_daily(message: Message):
    text = await claim_daily(message.from_user.id)
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "📋 Задания")
async def cmd_quests(message: Message):
    text = await show_quests(message.from_user.id)
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🏅 Достижения")
async def cmd_achievements(message: Message):
    await check_achievements(message.from_user.id)
    text = await show_achievements(message.from_user.id)
    await message.answer(text, parse_mode="HTML")
