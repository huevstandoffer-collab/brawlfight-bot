"""Мини-игры BrawlFight."""
from __future__ import annotations

import asyncio
import json
import random
import time
from datetime import date

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from data.brawlers import BRAWLERS, RARITY_ORDER, RARITY_EMOJI
from db import get_user, update_user

router = Router()

# in-memory sessions (сбрасываются при рестарте — ок для мини-игр)
_sessions: dict[int, dict] = {}

DAILY_FREE = 5          # бесплатных запусков мини-игр в день (суммарно)
EXTRA_COST = 30         # монет за попытку сверх лимита


# ─── helpers ───────────────────────────────────────────────

def _today() -> str:
    return str(date.today())


async def _load_mg(user_id: int) -> dict:
    user = await get_user(user_id)
    if not user:
        return {}
    data = json.loads(user.get("minigame_data") or "{}")
    if data.get("date") != _today():
        data = {"date": _today(), "plays": 0}
        await update_user(user_id, minigame_data=json.dumps(data))
    return data


async def _add_play(user_id: int) -> dict:
    data = await _load_mg(user_id)
    data["plays"] = data.get("plays", 0) + 1
    data["date"] = _today()
    await update_user(user_id, minigame_data=json.dumps(data))
    return data


async def _can_play(user_id: int) -> tuple[bool, str]:
    """Проверка лимита. Возвращает (ok, сообщение_ошибки)."""
    user = await get_user(user_id)
    if not user:
        return False, "Сначала /start"
    data = await _load_mg(user_id)
    plays = data.get("plays", 0)
    if plays < DAILY_FREE:
        return True, ""
    if user["coins"] >= EXTRA_COST:
        return True, ""
    return False, (
        f"Свободные попытки на сегодня кончились ({DAILY_FREE}/{DAILY_FREE}).\n"
        f"Дальше по {EXTRA_COST}💰. У тебя {user['coins']}💰."
    )


async def _spend_play(user_id: int) -> None:
    user = await get_user(user_id)
    data = await _load_mg(user_id)
    if data.get("plays", 0) >= DAILY_FREE:
        await update_user(user_id, coins=user["coins"] - EXTRA_COST)
    await _add_play(user_id)


def _menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="❓ Угадай бравлера", callback_data="mg_guess"),
            InlineKeyboardButton(text="⚖️ Кто сильнее", callback_data="mg_stronger"),
        ],
        [
            InlineKeyboardButton(text="🧠 Мемо", callback_data="mg_memo"),
            InlineKeyboardButton(text="⚡ Реакция", callback_data="mg_react"),
        ],
        [
            InlineKeyboardButton(text="🎰 Слоты", callback_data="mg_slots"),
            InlineKeyboardButton(text="🏁 Гонка", callback_data="mg_race"),
        ],
        [
            InlineKeyboardButton(text="📦 Сундук-ловушка", callback_data="mg_trap"),
            InlineKeyboardButton(text="💀 Showdown", callback_data="mg_showdown"),
        ],
        [
            InlineKeyboardButton(text="💎 Кристаллы", callback_data="mg_gems"),
            InlineKeyboardButton(text="💥 Супер-дуэль", callback_data="mg_super"),
        ],
        [
            InlineKeyboardButton(text="📌 Пины", callback_data="mg_pins"),
            InlineKeyboardButton(text="📊 Тир-лист", callback_data="mg_tier"),
        ],
        [InlineKeyboardButton(text="« Закрыть", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _brawler_pool(n: int = 4) -> list[int]:
    ids = list(BRAWLERS.keys())
    random.shuffle(ids)
    return ids[:n]


def _power(bid: int, level: int = 5) -> float:
    return BRAWLERS[bid]["base_power"] * (1 + 0.10 * (level - 1))


# ─── меню ──────────────────────────────────────────────────

@router.message(F.text == "🎮 Мини-игры")
async def cmd_minigames(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    data = await _load_mg(message.from_user.id)
    plays = data.get("plays", 0)
    left = max(0, DAILY_FREE - plays)
    text = (
        "🎮 <b>Мини-игры</b>\n\n"
        f"Бесплатных попыток сегодня: <b>{left}</b>/{DAILY_FREE}\n"
        f"Дальше: {EXTRA_COST}💰 за игру\n\n"
        "Выбери игру:"
    )
    await message.answer(text, reply_markup=_menu_kb(), parse_mode="HTML")


# ─── 1. Угадай бравлера ────────────────────────────────────

@router.callback_query(F.data == "mg_guess")
async def mg_guess_start(callback: CallbackQuery):
    ok, err = await _can_play(callback.from_user.id)
    if not ok:
        await callback.answer(err[:200], show_alert=True)
        return
    await _spend_play(callback.from_user.id)
    await callback.answer()

    target = random.choice(list(BRAWLERS.keys()))
    t = BRAWLERS[target]
    opts = _brawler_pool(3)
    if target not in opts:
        opts[0] = target
    random.shuffle(opts)

    hints = [
        f"Редкость: {RARITY_EMOJI.get(t['rarity'], '⚪')} {t['rarity']}",
        f"Эмодзи: {t['emoji']}",
        f"Сила ≈ {t['base_power']}",
        f"Имя начинается на «{t['name'][0]}»",
    ]
    random.shuffle(hints)
    shown = hints[:2]

    _sessions[callback.from_user.id] = {
        "game": "guess",
        "target": target,
        "opts": opts,
    }
    buttons = [
        [InlineKeyboardButton(
            text=f"{BRAWLERS[b]['emoji']} {BRAWLERS[b]['name']}",
            callback_data=f"mg_guess_a_{b}"
        )]
        for b in opts
    ]
    await callback.message.edit_text(
        "❓ <b>Угадай бравлера</b>\n\n"
        + "\n".join(f"• {h}" for h in shown)
        + "\n\nКто это?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("mg_guess_a_"))
async def mg_guess_answer(callback: CallbackQuery):
    sess = _sessions.get(callback.from_user.id)
    if not sess or sess.get("game") != "guess":
        await callback.answer("Сессия истекла, открой мини-игры снова", show_alert=True)
        return
    await callback.answer()
    pick = int(callback.data.split("_")[-1])
    target = sess["target"]
    t = BRAWLERS[target]
    _sessions.pop(callback.from_user.id, None)

    if pick == target:
        reward = random.randint(40, 80)
        user = await get_user(callback.from_user.id)
        await update_user(callback.from_user.id, coins=user["coins"] + reward)
        text = f"✅ Верно! Это {t['emoji']} <b>{t['name']}</b>\n💰 +{reward}"
    else:
        text = (
            f"❌ Мимо. Это был {t['emoji']} <b>{t['name']}</b>\n"
            f"Ты выбрал {BRAWLERS[pick]['emoji']} {BRAWLERS[pick]['name']}"
        )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_menu_kb())


# ─── 2. Кто сильнее ────────────────────────────────────────

@router.callback_query(F.data == "mg_stronger")
async def mg_stronger_start(callback: CallbackQuery):
    ok, err = await _can_play(callback.from_user.id)
    if not ok:
        await callback.answer(err[:200], show_alert=True)
        return
    await _spend_play(callback.from_user.id)
    await callback.answer()

    a, b = random.sample(list(BRAWLERS.keys()), 2)
    la, lb = random.randint(1, 9), random.randint(1, 9)
    pa, pb = _power(a, la), _power(b, lb)
    # правильный ответ без рандома боя
    if abs(pa - pb) < 3:
        correct = "eq"
    elif pa > pb:
        correct = "left"
    else:
        correct = "right"

    _sessions[callback.from_user.id] = {
        "game": "stronger",
        "correct": correct,
        "a": a, "b": b, "la": la, "lb": lb, "pa": pa, "pb": pb,
    }
    da, db = BRAWLERS[a], BRAWLERS[b]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👈 {da['emoji']} {da['name']}", callback_data="mg_str_left")],
        [InlineKeyboardButton(text="⚖️ Почти равны", callback_data="mg_str_eq")],
        [InlineKeyboardButton(text=f"👉 {db['emoji']} {db['name']}", callback_data="mg_str_right")],
    ])
    await callback.message.edit_text(
        "⚖️ <b>Кто сильнее?</b>\n\n"
        f"{da['emoji']} <b>{da['name']}</b> ур.{la}\n"
        f"vs\n"
        f"{db['emoji']} <b>{db['name']}</b> ур.{lb}\n\n"
        "Кто победит по силе?",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.in_({"mg_str_left", "mg_str_eq", "mg_str_right"}))
async def mg_stronger_answer(callback: CallbackQuery):
    sess = _sessions.get(callback.from_user.id)
    if not sess or sess.get("game") != "stronger":
        await callback.answer("Сессия истекла", show_alert=True)
        return
    await callback.answer()
    pick = callback.data.replace("mg_str_", "")
    correct = sess["correct"]
    _sessions.pop(callback.from_user.id, None)
    da, db = BRAWLERS[sess["a"]], BRAWLERS[sess["b"]]

    if pick == correct:
        reward = random.randint(35, 70)
        user = await get_user(callback.from_user.id)
        await update_user(callback.from_user.id, coins=user["coins"] + reward)
        result = f"✅ Верно! 💰 +{reward}"
    else:
        result = "❌ Не угадал"
    text = (
        f"{result}\n\n"
        f"{da['emoji']} {da['name']} — {sess['pa']:.0f}\n"
        f"{db['emoji']} {db['name']} — {sess['pb']:.0f}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_menu_kb())


# ─── 5. Мемо ───────────────────────────────────────────────

@router.callback_query(F.data == "mg_memo")
async def mg_memo_start(callback: CallbackQuery):
    ok, err = await _can_play(callback.from_user.id)
    if not ok:
        await callback.answer(err[:200], show_alert=True)
        return
    await _spend_play(callback.from_user.id)
    await callback.answer()

    picks = random.sample(list(BRAWLERS.keys()), 4)
    cards = picks * 2
    random.shuffle(cards)
    # board: list of bid; opened indices; matched set; first pick
    _sessions[callback.from_user.id] = {
        "game": "memo",
        "cards": cards,
        "opened": [],
        "matched": set(),
        "first": None,
        "moves": 0,
        "max_moves": 12,
    }
    await callback.message.edit_text(
        "🧠 <b>Мемо</b>\nНайди пары бравлеров. Ходов: 12",
        reply_markup=_memo_kb(callback.from_user.id),
        parse_mode="HTML",
    )


def _memo_kb(uid: int) -> InlineKeyboardMarkup:
    sess = _sessions[uid]
    buttons, row = [], []
    for i, bid in enumerate(sess["cards"]):
        if i in sess["matched"] or i in sess["opened"]:
            text = BRAWLERS[bid]["emoji"]
            data = "mg_memo_noop"
        else:
            text = "❓"
            data = f"mg_memo_{i}"
        row.append(InlineKeyboardButton(text=text, callback_data=data))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "mg_memo_noop")
async def mg_memo_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("mg_memo_"))
async def mg_memo_click(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions.get(uid)
    if not sess or sess.get("game") != "memo":
        await callback.answer("Сессия истекла", show_alert=True)
        return
    if callback.data == "mg_memo_noop":
        await callback.answer()
        return
    idx = int(callback.data.split("_")[-1])
    if idx in sess["matched"] or idx in sess["opened"]:
        await callback.answer()
        return

    if sess["first"] is None:
        sess["first"] = idx
        sess["opened"] = [idx]
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=_memo_kb(uid))
        return

    # second card
    first = sess["first"]
    sess["opened"] = [first, idx]
    sess["moves"] += 1
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=_memo_kb(uid))
    await asyncio.sleep(0.7)

    if sess["cards"][first] == sess["cards"][idx]:
        sess["matched"].add(first)
        sess["matched"].add(idx)
    sess["opened"] = []
    sess["first"] = None

    if len(sess["matched"]) == 8:
        reward = random.randint(80, 140)
        user = await get_user(uid)
        await update_user(uid, coins=user["coins"] + reward)
        _sessions.pop(uid, None)
        await callback.message.edit_text(
            f"🧠 <b>Мемо — победа!</b>\nХодов: {sess['moves']}\n💰 +{reward}",
            parse_mode="HTML",
            reply_markup=_menu_kb(),
        )
        return

    if sess["moves"] >= sess["max_moves"]:
        _sessions.pop(uid, None)
        await callback.message.edit_text(
            f"🧠 Ходы закончились ({sess['max_moves']}). Попробуй ещё!",
            reply_markup=_menu_kb(),
        )
        return

    await callback.message.edit_text(
        f"🧠 <b>Мемо</b>\nХод {sess['moves']}/{sess['max_moves']} · пары {len(sess['matched'])//2}/4",
        reply_markup=_memo_kb(uid),
        parse_mode="HTML",
    )


# ─── 6. Реакция ────────────────────────────────────────────

@router.callback_query(F.data == "mg_react")
async def mg_react_start(callback: CallbackQuery):
    ok, err = await _can_play(callback.from_user.id)
    if not ok:
        await callback.answer(err[:200], show_alert=True)
        return
    await _spend_play(callback.from_user.id)
    await callback.answer()

    _sessions[callback.from_user.id] = {"game": "react", "score": 0, "lives": 3}
    await callback.message.edit_text(
        "⚡ <b>Реакция</b>\nЖми только на ⚔️!\nОстальные эмодзи — минус жизнь.\n\nГотов?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Старт!", callback_data="mg_react_go")]
        ]),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "mg_react_go")
async def mg_react_go(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions.get(uid)
    if not sess or sess.get("game") != "react":
        await callback.answer("Сессия истекла", show_alert=True)
        return
    await callback.answer()
    await _react_round(callback)


async def _react_round(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions[uid]
    icons = ["💎", "🎁", "💰", "🌵", "🔫", "⚡", "🏆"]
    # 35% шанс что цель — ⚔️
    if random.random() < 0.38:
        shown = "⚔️"
        is_target = True
    else:
        shown = random.choice(icons)
        is_target = False
    sess["target"] = is_target
    sess["token"] = random.randint(1, 10**9)
    token = sess["token"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=shown, callback_data=f"mg_react_hit_{token}")]
    ])
    await callback.message.edit_text(
        f"⚡ Очки: <b>{sess['score']}</b> · Жизни: {'❤️' * sess['lives']}\n\nЖми, если это ⚔️!",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("mg_react_hit_"))
async def mg_react_hit(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions.get(uid)
    if not sess or sess.get("game") != "react":
        await callback.answer("Сессия истекла", show_alert=True)
        return
    token = int(callback.data.split("_")[-1])
    if token != sess.get("token"):
        await callback.answer()
        return
    await callback.answer()

    if sess["target"]:
        sess["score"] += 1
    else:
        sess["lives"] -= 1

    if sess["lives"] <= 0 or sess["score"] >= 12:
        score = sess["score"]
        _sessions.pop(uid, None)
        reward = score * 12
        if reward:
            user = await get_user(uid)
            await update_user(uid, coins=user["coins"] + reward)
        text = (
            f"⚡ <b>Реакция — финиш</b>\n"
            f"Очки: <b>{score}</b>\n"
            f"💰 +{reward}"
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_menu_kb())
        return

    await _react_round(callback)


# ─── 7. Слоты ──────────────────────────────────────────────

SLOT_ICONS = ["🌵", "🔫", "🦇", "💰", "💎", "🎁", "⚡"]


@router.callback_query(F.data == "mg_slots")
async def mg_slots(callback: CallbackQuery):
    ok, err = await _can_play(callback.from_user.id)
    if not ok:
        await callback.answer(err[:200], show_alert=True)
        return
    await _spend_play(callback.from_user.id)
    await callback.answer()

    msg = callback.message
    await msg.edit_text("🎰 Крутим...")
    await asyncio.sleep(0.6)
    for _ in range(3):
        preview = [random.choice(SLOT_ICONS) for _ in range(3)]
        await msg.edit_text("🎰 " + " | ".join(preview))
        await asyncio.sleep(0.35)

    a, b, c = [random.choice(SLOT_ICONS) for _ in range(3)]
    # чуть подкрутим шансы
    if random.random() < 0.12:
        a = b = c = random.choice(SLOT_ICONS)

    reward_coins = 0
    reward_crystals = 0
    reward_case = 0
    if a == b == c:
        if a == "💎":
            reward_crystals = 5
            title = "💎 ДЖЕКПОТ кристаллов!"
        elif a == "🎁":
            reward_case = 1
            title = "🎁 ДЖЕКПОТ — кейс!"
        elif a == "💰":
            reward_coins = 250
            title = "💰 ДЖЕКПОТ монет!"
        else:
            reward_coins = 120
            title = f"🔥 Три {a}!"
    elif a == b or b == c or a == c:
        reward_coins = 40
        title = "✨ Пара — небольшой приз"
    else:
        title = "Пусто... в следующий раз"

    user = await get_user(callback.from_user.id)
    kw = {}
    if reward_coins:
        kw["coins"] = user["coins"] + reward_coins
    if reward_crystals:
        kw["crystals"] = user["crystals"] + reward_crystals
    if reward_case:
        kw["cases"] = user["cases"] + reward_case
    if kw:
        await update_user(callback.from_user.id, **kw)

    lines = [f"🎰 <b>{a} | {b} | {c}</b>", "", title]
    if reward_coins:
        lines.append(f"💰 +{reward_coins}")
    if reward_crystals:
        lines.append(f"💎 +{reward_crystals}")
    if reward_case:
        lines.append("🎁 +1 обычный кейс")
    await msg.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=_menu_kb())


# ─── 9. Гонка трофеев ──────────────────────────────────────

@router.callback_query(F.data == "mg_race")
async def mg_race_start(callback: CallbackQuery):
    ok, err = await _can_play(callback.from_user.id)
    if not ok:
        await callback.answer(err[:200], show_alert=True)
        return
    await _spend_play(callback.from_user.id)
    await callback.answer()
    _sessions[callback.from_user.id] = {
        "game": "race", "lap": 0, "you": 0, "bot": 0, "total": 5,
    }
    await _race_turn(callback)


async def _race_turn(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions[uid]
    if sess["lap"] >= sess["total"]:
        you, bot = sess["you"], sess["bot"]
        _sessions.pop(uid, None)
        if you > bot:
            reward = random.randint(70, 120)
            user = await get_user(uid)
            await update_user(uid, coins=user["coins"] + reward)
            result = f"🏁 Победа! {you}:{bot}\n💰 +{reward}"
        elif you == bot:
            reward = 30
            user = await get_user(uid)
            await update_user(uid, coins=user["coins"] + reward)
            result = f"🏁 Ничья {you}:{bot}\n💰 +{reward}"
        else:
            result = f"🏁 Поражение {you}:{bot}"
        await callback.message.edit_text(result, reply_markup=_menu_kb())
        return

    sess["lap"] += 1
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚔️ Атака", callback_data="mg_race_atk"),
            InlineKeyboardButton(text="🛡 Защита", callback_data="mg_race_def"),
            InlineKeyboardButton(text="🎲 Риск", callback_data="mg_race_risk"),
        ]
    ])
    await callback.message.edit_text(
        f"🏁 <b>Гонка</b> — круг {sess['lap']}/{sess['total']}\n"
        f"Ты: <b>{sess['you']}</b> · Бот: <b>{sess['bot']}</b>\n\nВыбери действие:",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.in_({"mg_race_atk", "mg_race_def", "mg_race_risk"}))
async def mg_race_act(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions.get(uid)
    if not sess or sess.get("game") != "race":
        await callback.answer("Сессия истекла", show_alert=True)
        return
    await callback.answer()
    act = callback.data.replace("mg_race_", "")
    if act == "atk":
        gain = random.randint(8, 16)
    elif act == "def":
        gain = random.randint(4, 10)
    else:
        gain = random.randint(0, 28)
    bot_gain = random.randint(5, 18)
    sess["you"] += gain
    sess["bot"] += bot_gain
    await callback.message.edit_text(
        f"Круг {sess['lap']}: ты +{gain}, бот +{bot_gain}\n"
        f"Счёт {sess['you']}:{sess['bot']}"
    )
    await asyncio.sleep(0.8)
    await _race_turn(callback)


# ─── 10. Сундук с ловушкой ─────────────────────────────────

@router.callback_query(F.data == "mg_trap")
async def mg_trap_start(callback: CallbackQuery):
    ok, err = await _can_play(callback.from_user.id)
    if not ok:
        await callback.answer(err[:200], show_alert=True)
        return
    await _spend_play(callback.from_user.id)
    await callback.answer()

    # 0=prize, 1=empty, 2=trap
    order = [0, 1, 2]
    random.shuffle(order)
    _sessions[callback.from_user.id] = {"game": "trap", "order": order}
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"📦 {i+1}", callback_data=f"mg_trap_{i}")
        for i in range(3)
    ]])
    await callback.message.edit_text(
        "📦 <b>Сундук с ловушкой</b>\n\n"
        "В одном — приз, в одном — пусто, в одном — штраф.\nВыбери:",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("mg_trap_"))
async def mg_trap_pick(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions.get(uid)
    if not sess or sess.get("game") != "trap":
        await callback.answer("Сессия истекла", show_alert=True)
        return
    await callback.answer()
    idx = int(callback.data.split("_")[-1])
    kind = sess["order"][idx]
    _sessions.pop(uid, None)
    user = await get_user(uid)

    if kind == 0:
        reward = random.randint(80, 160)
        await update_user(uid, coins=user["coins"] + reward)
        text = f"✨ Приз! 💰 +{reward}"
    elif kind == 1:
        text = "💨 Пусто. Ничего не произошло."
    else:
        fine = min(60, user["coins"])
        await update_user(uid, coins=user["coins"] - fine)
        text = f"💣 Ловушка! 💰 −{fine}"
    await callback.message.edit_text(
        f"📦 Сундук {idx+1}\n\n{text}",
        reply_markup=_menu_kb(),
    )


# ─── 11. Showdown ──────────────────────────────────────────

@router.callback_query(F.data == "mg_showdown")
async def mg_showdown_start(callback: CallbackQuery):
    ok, err = await _can_play(callback.from_user.id)
    if not ok:
        await callback.answer(err[:200], show_alert=True)
        return
    await _spend_play(callback.from_user.id)
    await callback.answer()

    names = ["🤖 Бот-А", "🤖 Бот-Б", "🤖 Бот-В"]
    foes = [{"name": n, "hp": random.randint(80, 110)} for n in names]
    _sessions[callback.from_user.id] = {
        "game": "showdown",
        "hp": 100,
        "foes": foes,
        "turn": 0,
    }
    await _showdown_render(callback)


def _showdown_alive(sess) -> list[dict]:
    return [f for f in sess["foes"] if f["hp"] > 0]


async def _showdown_render(callback: CallbackQuery):
    sess = _sessions[callback.from_user.id]
    alive = _showdown_alive(sess)
    if sess["hp"] <= 0 or not alive:
        await _showdown_end(callback)
        return
    lines = [f"💀 <b>Showdown</b> · ход {sess['turn']+1}", f"Твоё HP: <b>{sess['hp']}</b>\n"]
    for f in sess["foes"]:
        mark = "☠️" if f["hp"] <= 0 else f"❤️{f['hp']}"
        lines.append(f"{mark} {f['name']}")
    buttons = []
    for i, f in enumerate(sess["foes"]):
        if f["hp"] > 0:
            buttons.append([InlineKeyboardButton(
                text=f"⚔️ Бить {f['name']}", callback_data=f"mg_sd_hit_{i}"
            )])
    buttons.append([
        InlineKeyboardButton(text="🛡 Прятаться", callback_data="mg_sd_hide"),
        InlineKeyboardButton(text="🎁 Лутать", callback_data="mg_sd_loot"),
    ])
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("mg_sd_"))
async def mg_showdown_act(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions.get(uid)
    if not sess or sess.get("game") != "showdown":
        await callback.answer("Сессия истекла", show_alert=True)
        return
    await callback.answer()
    act = callback.data
    sess["turn"] += 1
    log = []

    if act.startswith("mg_sd_hit_"):
        idx = int(act.split("_")[-1])
        if sess["foes"][idx]["hp"] > 0:
            dmg = random.randint(18, 32)
            sess["foes"][idx]["hp"] -= dmg
            log.append(f"Ты нанёс {dmg} урона {sess['foes'][idx]['name']}")
            if sess["foes"][idx]["hp"] <= 0:
                log.append(f"☠️ {sess['foes'][idx]['name']} выбыл!")
    elif act == "mg_sd_hide":
        sess["hidden"] = True
        log.append("Ты спрятался (50% шанс избежать урона)")
    else:
        heal = random.randint(8, 18)
        sess["hp"] = min(100, sess["hp"] + heal)
        log.append(f"Лут: +{heal} HP")

    # foes act
    for f in _showdown_alive(sess):
        if random.random() < 0.7:
            dmg = random.randint(10, 22)
            if sess.pop("hidden", False) and random.random() < 0.5:
                log.append(f"{f['name']} промахнулся")
            else:
                sess["hp"] -= dmg
                log.append(f"{f['name']} ударил на {dmg}")

    if sess["hp"] <= 0 or not _showdown_alive(sess):
        await callback.message.edit_text("\n".join(log))
        await asyncio.sleep(0.8)
        await _showdown_end(callback)
        return

    await callback.message.edit_text("\n".join(log))
    await asyncio.sleep(0.9)
    await _showdown_render(callback)


async def _showdown_end(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions.pop(uid, None)
    if not sess:
        return
    if sess["hp"] > 0 and not _showdown_alive(sess):
        reward = random.randint(100, 180)
        user = await get_user(uid)
        await update_user(uid, coins=user["coins"] + reward)
        text = f"💀 <b>Showdown — победа!</b>\nHP: {sess['hp']}\n💰 +{reward}"
    else:
        text = f"💀 Showdown — поражение\nХодов: {sess['turn']}"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_menu_kb())


# ─── 12. Захват кристаллов ─────────────────────────────────

@router.callback_query(F.data == "mg_gems")
async def mg_gems_start(callback: CallbackQuery):
    ok, err = await _can_play(callback.from_user.id)
    if not ok:
        await callback.answer(err[:200], show_alert=True)
        return
    await _spend_play(callback.from_user.id)
    await callback.answer()
    _sessions[callback.from_user.id] = {
        "game": "gems", "you": 0, "bot": 0, "goal": 10, "turn": 0,
    }
    await _gems_turn(callback)


async def _gems_turn(callback: CallbackQuery):
    sess = _sessions[callback.from_user.id]
    if sess["you"] >= sess["goal"] or sess["bot"] >= sess["goal"] or sess["turn"] >= 12:
        await _gems_end(callback)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💎 Нести", callback_data="mg_gem_carry"),
        InlineKeyboardButton(text="⚔️ Бить", callback_data="mg_gem_hit"),
        InlineKeyboardButton(text="🕶 Красть", callback_data="mg_gem_steal"),
    ]])
    await callback.message.edit_text(
        f"💎 <b>Кристаллы</b> · до {sess['goal']}\n"
        f"Ты: <b>{sess['you']}</b> · Бот: <b>{sess['bot']}</b>\n\nХод:",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.in_({"mg_gem_carry", "mg_gem_hit", "mg_gem_steal"}))
async def mg_gems_act(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions.get(uid)
    if not sess or sess.get("game") != "gems":
        await callback.answer("Сессия истекла", show_alert=True)
        return
    await callback.answer()
    act = callback.data.replace("mg_gem_", "")
    sess["turn"] += 1
    log = []
    if act == "carry":
        g = random.randint(1, 3)
        sess["you"] += g
        log.append(f"Принёс {g}💎")
    elif act == "hit":
        if random.random() < 0.55 and sess["bot"] > 0:
            lost = min(sess["bot"], random.randint(1, 2))
            sess["bot"] -= lost
            log.append(f"Сбил с бота {lost}💎")
        else:
            log.append("Удар мимо")
    else:
        if random.random() < 0.4 and sess["bot"] > 0:
            stolen = min(sess["bot"], 2)
            sess["bot"] -= stolen
            sess["you"] += stolen
            log.append(f"Украл {stolen}💎")
        else:
            log.append("Кража не удалась")

    # bot
    b = random.choice(["carry", "hit", "steal"])
    if b == "carry":
        g = random.randint(1, 3)
        sess["bot"] += g
        log.append(f"Бот принёс {g}💎")
    elif b == "hit" and sess["you"] > 0 and random.random() < 0.4:
        lost = min(sess["you"], random.randint(1, 2))
        sess["you"] -= lost
        log.append(f"Бот сбил у тебя {lost}💎")
    elif b == "steal" and sess["you"] > 0 and random.random() < 0.3:
        stolen = min(sess["you"], 1)
        sess["you"] -= stolen
        sess["bot"] += stolen
        log.append(f"Бот украл {stolen}💎")

    await callback.message.edit_text("\n".join(log))
    await asyncio.sleep(0.8)
    if sess["you"] >= sess["goal"] or sess["bot"] >= sess["goal"] or sess["turn"] >= 12:
        await _gems_end(callback)
    else:
        await _gems_turn(callback)


async def _gems_end(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions.pop(uid, None)
    if not sess:
        return
    if sess["you"] > sess["bot"]:
        reward = random.randint(70, 130)
        user = await get_user(uid)
        await update_user(uid, coins=user["coins"] + reward)
        text = f"💎 Победа {sess['you']}:{sess['bot']}!\n💰 +{reward}"
    elif sess["you"] == sess["bot"]:
        text = f"💎 Ничья {sess['you']}:{sess['bot']}"
    else:
        text = f"💎 Поражение {sess['you']}:{sess['bot']}"
    await callback.message.edit_text(text, reply_markup=_menu_kb())


# ─── 13. Супер-дуэль ───────────────────────────────────────

@router.callback_query(F.data == "mg_super")
async def mg_super_start(callback: CallbackQuery):
    ok, err = await _can_play(callback.from_user.id)
    if not ok:
        await callback.answer(err[:200], show_alert=True)
        return
    await _spend_play(callback.from_user.id)
    await callback.answer()
    _sessions[callback.from_user.id] = {
        "game": "super", "you_hp": 100, "bot_hp": 100, "ult": 0, "turn": 0,
    }
    await _super_turn(callback)


async def _super_turn(callback: CallbackQuery):
    sess = _sessions[callback.from_user.id]
    if sess["you_hp"] <= 0 or sess["bot_hp"] <= 0 or sess["turn"] >= 10:
        await _super_end(callback)
        return
    buttons = [
        [InlineKeyboardButton(text="⚔️ Удар", callback_data="mg_sup_atk")],
        [InlineKeyboardButton(text="🛡 Блок", callback_data="mg_sup_def")],
    ]
    if sess["ult"] >= 3:
        buttons.append([InlineKeyboardButton(text="💥 УЛЬТ", callback_data="mg_sup_ult")])
    await callback.message.edit_text(
        f"💥 <b>Супер-дуэль</b>\n"
        f"Ты ❤️{sess['you_hp']} · Бот ❤️{sess['bot_hp']}\n"
        f"Заряд ульта: {sess['ult']}/3\n\nВыбор:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )


@router.callback_query(F.data.in_({"mg_sup_atk", "mg_sup_def", "mg_sup_ult"}))
async def mg_super_act(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions.get(uid)
    if not sess or sess.get("game") != "super":
        await callback.answer("Сессия истекла", show_alert=True)
        return
    await callback.answer()
    you = callback.data.replace("mg_sup_", "")
    bot = random.choice(["atk", "def", "ult"] if sess["turn"] >= 2 else ["atk", "def"])
    sess["turn"] += 1
    log = []

    def dmg_atk():
        return random.randint(12, 22)

    # resolve
    if you == "ult" and sess["ult"] >= 3:
        sess["ult"] = 0
        if bot == "def":
            d = random.randint(25, 40)
            log.append(f"Ульт пробил блок на {d}!")
        else:
            d = random.randint(30, 50)
            log.append(f"Ульт на {d}!")
        sess["bot_hp"] -= d
    elif you == "atk":
        sess["ult"] = min(3, sess["ult"] + 1)
        if bot == "def":
            log.append("Бот заблокировал удар")
        else:
            d = dmg_atk()
            sess["bot_hp"] -= d
            log.append(f"Удар на {d}")
    else:
        log.append("Ты в блоке")

    if bot == "ult":
        if you == "def":
            d = random.randint(20, 35)
            log.append(f"Ульт бота через блок: {d}")
        else:
            d = random.randint(28, 45)
            log.append(f"Ульт бота: {d}")
        sess["you_hp"] -= d
    elif bot == "atk":
        if you == "def":
            log.append("Ты заблокировал бота")
        else:
            d = dmg_atk()
            sess["you_hp"] -= d
            log.append(f"Бот ударил на {d}")

    await callback.message.edit_text("\n".join(log))
    await asyncio.sleep(0.85)
    if sess["you_hp"] <= 0 or sess["bot_hp"] <= 0 or sess["turn"] >= 10:
        await _super_end(callback)
    else:
        await _super_turn(callback)


async def _super_end(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions.pop(uid, None)
    if not sess:
        return
    if sess["bot_hp"] <= 0 and sess["you_hp"] > 0:
        reward = random.randint(80, 150)
        user = await get_user(uid)
        await update_user(uid, coins=user["coins"] + reward)
        text = f"💥 Победа! ❤️{sess['you_hp']}\n💰 +{reward}"
    elif sess["you_hp"] <= 0:
        text = "💥 Поражение..."
    else:
        text = f"💥 Время вышло {sess['you_hp']}:{max(0, sess['bot_hp'])}"
    await callback.message.edit_text(text, reply_markup=_menu_kb())


# ─── 14. Пины ──────────────────────────────────────────────

@router.callback_query(F.data == "mg_pins")
async def mg_pins(callback: CallbackQuery):
    ok, err = await _can_play(callback.from_user.id)
    if not ok:
        await callback.answer(err[:200], show_alert=True)
        return
    await _spend_play(callback.from_user.id)
    await callback.answer()

    user = await get_user(callback.from_user.id)
    pins = json.loads(user.get("pins") or "{}")
    bid = random.choice(list(BRAWLERS.keys()))
    b = BRAWLERS[bid]
    key = str(bid)
    pins[key] = pins.get(key, 0) + 1
    await update_user(callback.from_user.id, pins=json.dumps(pins))

    count = pins[key]
    bonus = ""
    if count > 0 and count % 5 == 0:
        reward = 100
        await update_user(callback.from_user.id, coins=user["coins"] + reward)
        bonus = f"\n🎉 Набор из 5 пинов {b['name']}! 💰 +{reward}"

    total = sum(pins.values())
    unique = len(pins)
    text = (
        f"📌 <b>Пин получен!</b>\n\n"
        f"{b['emoji']} {b['name']} (×{count})\n"
        f"Всего пинов: {total} · Уникальных: {unique}"
        f"{bonus}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_menu_kb())


# ─── 15. Тир-лист ──────────────────────────────────────────

# упрощённый «мета» по base_power
def _tier_of(bid: int) -> str:
    p = BRAWLERS[bid]["base_power"]
    if p >= 135:
        return "S"
    if p >= 125:
        return "A"
    if p >= 118:
        return "B"
    if p >= 110:
        return "C"
    return "D"


@router.callback_query(F.data == "mg_tier")
async def mg_tier_start(callback: CallbackQuery):
    ok, err = await _can_play(callback.from_user.id)
    if not ok:
        await callback.answer(err[:200], show_alert=True)
        return
    await _spend_play(callback.from_user.id)
    await callback.answer()

    bid = random.choice(list(BRAWLERS.keys()))
    _sessions[callback.from_user.id] = {
        "game": "tier",
        "bid": bid,
        "correct": _tier_of(bid),
    }
    b = BRAWLERS[bid]
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t, callback_data=f"mg_tier_{t}")
        for t in ("S", "A", "B", "C", "D")
    ]])
    await callback.message.edit_text(
        f"📊 <b>Тир-лист</b>\n\n"
        f"Куда поставить {b['emoji']} <b>{b['name']}</b>?\n"
        f"(по силе в этом боте)",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("mg_tier_"))
async def mg_tier_answer(callback: CallbackQuery):
    uid = callback.from_user.id
    sess = _sessions.get(uid)
    if not sess or sess.get("game") != "tier":
        await callback.answer("Сессия истекла", show_alert=True)
        return
    await callback.answer()
    pick = callback.data.split("_")[-1]
    correct = sess["correct"]
    b = BRAWLERS[sess["bid"]]
    _sessions.pop(uid, None)

    if pick == correct:
        reward = random.randint(40, 75)
        user = await get_user(uid)
        await update_user(uid, coins=user["coins"] + reward)
        text = f"✅ Верно! {b['emoji']} {b['name']} — <b>{correct}</b>\n💰 +{reward}"
    else:
        text = f"❌ Нет. {b['emoji']} {b['name']} — <b>{correct}</b> (ты: {pick})"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_menu_kb())
