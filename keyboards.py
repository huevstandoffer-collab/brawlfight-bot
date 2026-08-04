"""Клавиатуры бота."""
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)

from data.brawlers import BRAWLERS, UPGRADE_COST
from data.constants import SHOP_ITEMS


def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚔️ Бой"), KeyboardButton(text="🎁 Ежедневка")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📦 Коллекция")],
            [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="⬆️ Прокачка")],
            [KeyboardButton(text="📋 Задания"), KeyboardButton(text="🏅 Достижения")],
            [KeyboardButton(text="🎁 Открыть кейс"), KeyboardButton(text="🎟 Пропуск")],
            [KeyboardButton(text="📜 История"), KeyboardButton(text="🏆 Топ")],
            [KeyboardButton(text="📅 Топ недели")],
            [KeyboardButton(text="🎲 Рулетка"), KeyboardButton(text="🌊 Волны")],
            [KeyboardButton(text="🗼 Башня"), KeyboardButton(text="👹 Босс")],
            [KeyboardButton(text="🗝️ Сундук"), KeyboardButton(text="🎮 Мини-игры")],
            [KeyboardButton(text="🎲 Мне повезёт"), KeyboardButton(text="🌵 Война")],
            [KeyboardButton(text="🥷 Укради очко")],
            [KeyboardButton(text="✏️ Ник"), KeyboardButton(text="📖 Гайд")],
        ],
        resize_keyboard=True
    )


def battle_mode_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Обычный бой", callback_data="battle_normal")],
        [InlineKeyboardButton(text="🏆 Рейтинговый бой", callback_data="battle_ranked")],
        [InlineKeyboardButton(text="« Отмена", callback_data="back_main")],
    ])


def shop_kb():
    buttons = []
    for key, item in SHOP_ITEMS.items():
        price = f"{item['price_crystals']}💎" if item['price_crystals'] else f"{item['price_coins']}💰"
        buttons.append([InlineKeyboardButton(text=f"{item['name']} — {price}", callback_data=f"buy_{key}")])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def brawler_select_kb(owned: dict):
    buttons, row = [], []
    for bid, data in BRAWLERS.items():
        if bid in owned:
            text = f"{data['emoji']} {data['name']} (ур.{owned[bid]})"
            row.append(InlineKeyboardButton(text=text, callback_data=f"select_{bid}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def upgrade_kb(owned: dict):
    buttons = []
    for bid, level in sorted(owned.items(), key=lambda x: BRAWLERS[x[0]]["name"]):
        data = BRAWLERS[bid]
        if level < 11:
            cost_c, cost_pp = UPGRADE_COST.get(level, (9999, 9999))
            text = f"{data['emoji']} {data['name']} ур.{level}→{level+1} ({cost_c}💰 {cost_pp}⚡)"
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"upgrade_{bid}")])
        else:
            buttons.append([InlineKeyboardButton(text=f"{data['emoji']} {data['name']} — МАКС", callback_data="noop")])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


