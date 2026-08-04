"""Настройки бота BrawlFight."""
import os

# Токен только из переменной окружения (без хардкода)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError(
        "Не задан BOT_TOKEN. Укажи переменную окружения BOT_TOKEN."
    )

# На Railway с Volume монтируем в /data — база не теряется при деплое
DB_PATH = os.getenv("DB_PATH", "brawl_bot.db")

# Админы: через переменную ADMIN_IDS (через запятую)
_ADMIN_ENV = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: set[int] = set()
if _ADMIN_ENV:
    for x in _ADMIN_ENV.split(","):
        x = x.strip()
        if x.isdigit():
            ADMIN_IDS.add(int(x))
# Можно добавить свой Telegram ID вручную:
# ADMIN_IDS.add(123456789)

BATTLE_COOLDOWN = 18
CASE_DROP_CHANCE = 12
