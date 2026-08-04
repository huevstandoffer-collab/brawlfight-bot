"""Админ-команды."""
import os

import aiosqlite
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from config import ADMIN_IDS, DB_PATH
from db import get_user  # noqa: F401

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def require_admin(message: Message) -> bool:
    """Проверка прав. False = доступа нет (сообщение уже отправлено)."""
    if not ADMIN_IDS:
        await message.answer(
            "⚠️ Список админов пуст.\n\n"
            "1. Напиши /myid — скопируй свой ID\n"
            "2. В Railway → Variables добавь:\n"
            "   Key: <code>ADMIN_IDS</code>\n"
            "   Value: <code>твой_id</code>\n"
            "3. Сделай Redeploy",
            parse_mode="HTML"
        )
        return False
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа. Только для администраторов.")
        return False
    return True


async def cmd_myid(message: Message):
    await message.answer(f"Твой Telegram ID: <code>{message.from_user.id}</code>", parse_mode="HTML")


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await require_admin(message):
        return
    await message.answer(
        "🛠 <b>Админ-панель</b>\n\n"
        "/backup — скачать базу данных\n"
        "/restore — ответь этой командой на файл .db для восстановления\n"
        "/stats — общая статистика бота\n"
        "/myid — узнать свой ID",
        parse_mode="HTML"
    )


@router.message(Command("backup"))
async def cmd_backup(message: Message):
    if not await require_admin(message):
        return
    if not os.path.exists(DB_PATH):
        await message.answer("Файл базы не найден")
        return
    try:
        doc = FSInputFile(DB_PATH, filename="brawl_bot_backup.db")
        await message.answer_document(doc, caption="📦 Бэкап базы BrawlFight")
    except Exception as e:
        await message.answer(f"Ошибка бэкапа: {e}")


@router.message(Command("restore"))
async def cmd_restore(message: Message):
    if not await require_admin(message):
        return
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.answer(
            "Чтобы восстановить базу:\n"
            "1. Отправь файл .db боту\n"
            "2. Ответь на это сообщение командой /restore"
        )
        return
    doc = message.reply_to_message.document
    try:
        file = await message.bot.get_file(doc.file_id)
        data = await message.bot.download_file(file.file_path)
        content = data.read()
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        with open(DB_PATH, "wb") as f:
            f.write(content)
        await message.answer("✅ База восстановлена! Перезапусти бота (Redeploy), чтобы точно подхватило.")
    except Exception as e:
        await message.answer(f"Ошибка восстановления: {e}")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not await require_admin(message):
        return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            users = (await cur.fetchone())[0]
        async with db.execute("SELECT SUM(wins), SUM(losses) FROM users") as cur:
            row = await cur.fetchone()
            wins, losses = row[0] or 0, row[1] or 0
        async with db.execute("SELECT COUNT(*) FROM user_brawlers") as cur:
            brawlers = (await cur.fetchone())[0]
    await message.answer(
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Игроков: {users}\n"
        f"⚔️ Побед / поражений: {wins} / {losses}\n"
        f"📦 Всего бравлеров у игроков: {brawlers}",
        parse_mode="HTML"
    )


