"""Антифлуд: лимит сообщений и callback на пользователя."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from config import ADMIN_IDS

# Окно и лимиты
WINDOW_SEC = 2.0
MAX_MESSAGES = 3      # сообщений за WINDOW_SEC
MAX_CALLBACKS = 5     # callback за WINDOW_SEC
BLOCK_SEC = 3.0       # молчать столько секунд после флуда

_msg_hits: dict[int, deque] = defaultdict(deque)
_cb_hits: dict[int, deque] = defaultdict(deque)
_blocked_until: dict[int, float] = {}


def _prune(dq: deque, now: float) -> None:
    while dq and now - dq[0] > WINDOW_SEC:
        dq.popleft()


def _is_blocked(uid: int, now: float) -> float:
    until = _blocked_until.get(uid, 0)
    if until > now:
        return until - now
    return 0


def _register(dq: deque, uid: int, now: float, limit: int) -> bool:
    """True = слишком часто (флуд)."""
    _prune(dq, now)
    dq.append(now)
    if len(dq) > limit:
        _blocked_until[uid] = now + BLOCK_SEC
        dq.clear()
        return True
    return False


class AntiFloodMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
            kind = "msg"
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            kind = "cb"
        else:
            return await handler(event, data)

        if not user or user.is_bot:
            return await handler(event, data)

        uid = user.id
        if uid in ADMIN_IDS:
            return await handler(event, data)

        now = time.time()
        left = _is_blocked(uid, now)
        if left > 0:
            if isinstance(event, CallbackQuery):
                await event.answer(f"Слишком быстро. Подожди {int(left)+1} сек.", show_alert=True)
            elif isinstance(event, Message):
                # не спамим ответами на каждый клик — раз в блок
                if int(left) >= BLOCK_SEC - 1:
                    await event.answer(f"🚫 Антифлуд: подожди {int(left)+1} сек.")
            return None

        if kind == "msg":
            if _register(_msg_hits[uid], uid, now, MAX_MESSAGES):
                await event.answer(f"🚫 Слишком много сообщений. Пауза {int(BLOCK_SEC)} сек.")
                return None
        else:
            if _register(_cb_hits[uid], uid, now, MAX_CALLBACKS):
                await event.answer(f"Слишком быстро. Пауза {int(BLOCK_SEC)} сек.", show_alert=True)
                return None

        return await handler(event, data)
