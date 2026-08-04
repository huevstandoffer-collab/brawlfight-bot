"""Магазин, достижения, сезонный пропуск, боссы."""
# Магазин
SHOP_ITEMS = {
    "case_normal":   {"name": "🎁 Обычный кейс",     "price_crystals": 15,  "price_coins": 0},
    "case_epic":     {"name": "🎁 Эпический кейс",   "price_crystals": 45,  "price_coins": 0},
    "case_legend":   {"name": "🎁 Легендарный кейс", "price_crystals": 120, "price_coins": 0},
    "pp_100":        {"name": "⚡ 100 очков силы",   "price_crystals": 0,   "price_coins": 80},
    "pp_300":        {"name": "⚡ 300 очков силы",   "price_crystals": 0,   "price_coins": 220},
    "crystals_10":   {"name": "💎 10 кристаллов",    "price_crystals": 0,   "price_coins": 350},
}

# Достижения
ACHIEVEMENTS = {
    "brawlers_5":   {"name": "Собрать 5 бравлеров",     "check": lambda u, owned: len(owned) >= 5,  "reward_coins": 100, "reward_crystals": 3},
    "brawlers_15":  {"name": "Собрать 15 бравлеров",    "check": lambda u, owned: len(owned) >= 15, "reward_coins": 300, "reward_crystals": 8},
    "trophies_200": {"name": "Достичь 200 трофеев",     "check": lambda u, owned: u["trophies"] >= 200, "reward_coins": 150, "reward_crystals": 5},
    "trophies_500": {"name": "Достичь 500 трофеев",     "check": lambda u, owned: u["trophies"] >= 500, "reward_coins": 400, "reward_crystals": 12},
    "wins_50":      {"name": "Выиграть 50 боёв",        "check": lambda u, owned: u["wins"] >= 50,  "reward_coins": 250, "reward_crystals": 7},
    "wins_100":     {"name": "Выиграть 100 боёв",       "check": lambda u, owned: u["wins"] >= 100, "reward_coins": 500, "reward_crystals": 15},
}


SEASON_REWARDS = {
    1:  {"xp": 50,  "coins": 100, "crystals": 0, "cases": 0},
    2:  {"xp": 120, "coins": 150, "crystals": 1, "cases": 0},
    3:  {"xp": 200, "coins": 0,   "crystals": 0, "cases": 1},
    4:  {"xp": 300, "coins": 200, "crystals": 2, "cases": 0},
    5:  {"xp": 420, "coins": 0,   "crystals": 3, "cases": 0},
    6:  {"xp": 550, "coins": 250, "crystals": 0, "cases": 1},
    7:  {"xp": 700, "coins": 0,   "crystals": 5, "cases": 0},
    8:  {"xp": 880, "coins": 300, "crystals": 0, "cases": 0},
    9:  {"xp": 1100,"coins": 0,   "crystals": 0, "cases": 1},
    10: {"xp": 1400,"coins": 500, "crystals": 10,"cases": 0},
}

BOSS_POOL = [
    ("🤖 Мегабот", 500),
    ("🐉 Дракон Старр", 700),
    ("💀 Тёмный Мортис", 600),
    ("⚡ Кибер-Сёрдж", 650),
    ("🌵 Гига-Спайк", 550),
]