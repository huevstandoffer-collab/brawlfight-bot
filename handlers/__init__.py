"""Регистрация всех роутеров. Fallback — всегда последним."""
from aiogram import Dispatcher

from handlers import (
    start, battle, profile, collection, shop, quests, season, modes, admin, fallback,
)


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(battle.router)
    dp.include_router(profile.router)
    dp.include_router(collection.router)
    dp.include_router(shop.router)
    dp.include_router(quests.router)
    dp.include_router(season.router)
    dp.include_router(modes.router)
    dp.include_router(admin.router)
    # fallback всегда в конце
    dp.include_router(fallback.router)
