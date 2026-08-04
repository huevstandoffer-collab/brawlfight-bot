"""Старт, гайд, ник, fallback."""
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery

from db import create_user, update_user
from keyboards import main_kb
from middlewares.subscription import is_subscribed, sub_keyboard, SUB_TEXT

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    await create_user(user_id, username)

    text = (
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        f"Добро пожаловать в <b>BrawlFight</b>!\n\n"
        f"Ты получил 🔫 <b>Shelly</b> (уровень 1)\n\n"
        f"⚔️ Сражайся • 📦 Собирай бравлеров\n"
        f"⬆️ Прокачивай • 🛒 Покупай кейсы\n"
        f"🎁 Забирай ежедневные награды\n\n"
        f"Используй кнопки внизу 👇"
    )
    await message.answer(text, reply_markup=main_kb(), parse_mode="HTML")


@router.message(F.text == "📖 Гайд")
@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📖 <b>Гайд по BrawlFight</b>\n\n"
        "⚔️ <b>Бой</b> — обычный или рейтинговый 1на1. Бой проходит автоматически за 3–5 сек.\n"
        "• Обычный — стандартные награды\n"
        "• Рейтинговый — больше трофеев и наград, но и штраф выше\n\n"
        "🎁 <b>Ежедневка</b> — награда раз в день. Чем дольше стрик — тем жирнее приз.\n\n"
        "👤 <b>Профиль</b> — трофеи, ранг, ресурсы, выбранный бравлер.\n\n"
        "📦 <b>Коллекция</b> — все твои бравлеры. Нажми, чтобы выбрать бойца на бой.\n\n"
        "⬆️ <b>Прокачка</b> — улучшай бравлеров за монеты и очки силы (макс. 11 ур.).\n\n"
        "🛒 <b>Магазин</b> — кейсы за кристаллы, очки силы и кристаллы за монеты.\n\n"
        "🎁 <b>Открыть кейс</b> — шанс выбить нового бравлера или ресурсы.\n\n"
        "📋 <b>Задания</b> — ежедневные квесты. Сложность зависит от твоих трофеев.\n\n"
        "🏅 <b>Достижения</b> — разовые цели с наградами.\n\n"
        "🎟 <b>Пропуск</b> — сезонный пропуск: играй бои → получай XP → забирай награды.\n\n"
        "📜 <b>История</b> — последние 10 боёв.\n\n"
        "🏆 <b>Топ</b> — топ-20 игроков и твоё место в рейтинге.\n\n"
        "🎮 <b>Мини-игры</b> — угадай бравлера, слоты, showdown, мемо и другое.\n\n✏️ <b>Ник</b> — сменить отображаемое имя: <code>/setnick Имя</code>\n\n"
        "💡 <b>Советы</b>\n"
        "• Заходи каждый день за ежедневкой\n"
        "• Прокачивай бойца перед рейтинговыми боями\n"
        "• Выполняй задания — там хорошие награды\n"
        "• Кейсы лучше копить и открывать пачкой"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "✏️ Ник")
@router.message(Command("nick"))
async def cmd_nick(message: Message):
    await message.answer(
        "✏️ Чтобы сменить ник, напиши:\n"
        "<code>/setnick ТвойНик</code>\n\n"
        "От 2 до 16 символов. Без &lt; &gt; { } [ ]",
        parse_mode="HTML"
    )


@router.message(Command("setnick"))
async def set_nick(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /setnick ТвойНик")
        return
    text = parts[1].strip()
    if not (2 <= len(text) <= 16):
        await message.answer("Ник должен быть от 2 до 16 символов.")
        return
    if any(ch in text for ch in "<>{}[]"):
        await message.answer("Ник содержит запрещённые символы.")
        return
    await update_user(message.from_user.id, nickname=text)
    await message.answer(f"✅ Ник изменён на: <b>{text}</b>", parse_mode="HTML")


@router.callback_query(F.data == "back_main")
async def cb_back(callback):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback):
    await callback.answer()


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery):
    ok = await is_subscribed(callback.bot, callback.from_user.id)
    if ok:
        await callback.answer("Подписка есть! ✅", show_alert=True)
        # создаём юзера если вдруг первый заход через кнопку
        username = callback.from_user.username or callback.from_user.first_name
        await create_user(callback.from_user.id, username)
        try:
            await callback.message.edit_text(
                "✅ Подписка подтверждена! Добро пожаловать в <b>BrawlFight</b>.\n"
                "Жми /start или кнопки меню 👇",
                parse_mode="HTML",
            )
        except Exception:
            pass
        await callback.message.answer("Меню:", reply_markup=main_kb())
    else:
        await callback.answer("Подписка не найдена. Подпишись и нажми ещё раз.", show_alert=True)
        try:
            await callback.message.edit_text(SUB_TEXT, reply_markup=sub_keyboard(), parse_mode="HTML")
        except Exception:
            await callback.message.answer(SUB_TEXT, reply_markup=sub_keyboard(), parse_mode="HTML")
