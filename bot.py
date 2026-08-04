"""
BrawlFight Bot — точка входа.
Ежедневные награды, стрик, магазин, задания, достижения, анимация боя.
"""
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DB_PATH
from db import init_db
from handlers import register_handlers


async def main():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    register_handlers(dp)
    print("BrawlFight бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
