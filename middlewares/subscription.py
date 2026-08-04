"""Проверка подписки на канал."""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import (
    Message, CallbackQuery, TelegramObject,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from config import ADMIN_IDS, CHANNEL_USERNAME, CHANNEL_LINK, REQUIRE_SUB

# callback_data для повторной проверки — не блокируем
_ALLOW_CALLBACKS = {"check_sub", "back_main"}


def sub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")],
    ])


SUB_TEXT = (
    "🔒 <b>Доступ только для подписчиков</b>\n\n"
    "Чтобы играть в BrawlFight, подпишись на канал новостей бота:\n"
    f"{CHANNEL_LINK}\n\n"
    "После подписки нажми «✅ Я подписался»."
)


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    if not REQUIRE_SUB:
        return True
    if user_id in ADMIN_IDS:
        return True
    try:
        member = await bot.get_chat_member(
            chat_id=f"@{CHANNEL_USERNAME.lstrip('@')}",
            user_id=user_id,
        )
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.RESTRICTED,  # в канале редко, но ок
        )
    except Exception as e:
        # Бот не админ канала или канал недоступен.
        # Fail-open: не блокируем весь бот. Обязательно сделай бота админом канала.
        print(f"[sub] check failed for {user_id}: {e}")
        return True


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not REQUIRE_SUB:
            return await handler(event, data)

        user = None
        bot: Bot = data["bot"]

        if isinstance(event, Message):
            user = event.from_user
            # /start тоже требует подписку, но сначала создадим юзера в хендлере —
            # middleware просто покажет экран подписки
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            if event.data in _ALLOW_CALLBACKS or (event.data and event.data.startswith("check_sub")):
                return await handler(event, data)
        else:
            return await handler(event, data)

        if not user or user.is_bot:
            return await handler(event, data)

        if await is_subscribed(bot, user.id):
            return await handler(event, data)

        # не подписан
        if isinstance(event, CallbackQuery):
            await event.answer("Сначала подпишись на канал", show_alert=True)
            try:
                await event.message.answer(SUB_TEXT, reply_markup=sub_keyboard(), parse_mode="HTML")
            except Exception:
                pass
            return None

        if isinstance(event, Message):
            await event.answer(SUB_TEXT, reply_markup=sub_keyboard(), parse_mode="HTML")
            return None

        return await handler(event, data)
