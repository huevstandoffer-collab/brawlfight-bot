"""Catch-all — регистрировать последним."""
from aiogram import Router
from aiogram.types import Message

from keyboards import main_kb

router = Router()


@router.message()
async def fallback(message: Message):
    await message.answer("Используй кнопки меню 👇", reply_markup=main_kb())
