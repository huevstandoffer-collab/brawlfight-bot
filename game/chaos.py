"""Хаос-механики: война эмодзи, глючный режим."""
from __future__ import annotations

import random
import threading
import time

_lock = threading.Lock()

# Война эмодзи: два лагеря, окна по 10 минут каждые ~40–70 мин
_war = {
    "active": False,
    "ends": 0.0,
    "next_at": 0.0,
    "cactus": 0,   # 🌵
    "gun": 0,      # 🔫
    "winner": None,  # "cactus" | "gun" | None
    "buff_ends": 0.0,
    "buff_side": None,
}

WAR_DURATION = 10 * 60       # 10 мин голосования
WAR_COOLDOWN = (40 * 60, 70 * 60)  # пауза между войнами
BUFF_DURATION = 60 * 60      # час x2 награды победителям

# Глючный бой: глобальное окно
_glitch = {
    "active": False,
    "ends": 0.0,
    "next_at": 0.0,
}

GLITCH_DURATION = 5 * 60
GLITCH_COOLDOWN = (50 * 60, 90 * 60)


def _ensure_war_schedule(now: float) -> None:
    if _war["active"] and now >= _war["ends"]:
        # подвести итоги
        if _war["cactus"] > _war["gun"]:
            _war["winner"] = "cactus"
            _war["buff_side"] = "cactus"
        elif _war["gun"] > _war["cactus"]:
            _war["winner"] = "gun"
            _war["buff_side"] = "gun"
        else:
            _war["winner"] = None
            _war["buff_side"] = None
        if _war["buff_side"]:
            _war["buff_ends"] = now + BUFF_DURATION
        _war["active"] = False
        _war["next_at"] = now + random.randint(*WAR_COOLDOWN)
        _war["cactus"] = 0
        _war["gun"] = 0
    if not _war["active"]:
        if _war["next_at"] == 0:
            _war["next_at"] = now + random.randint(5 * 60, 15 * 60)
        if now >= _war["next_at"]:
            _war["active"] = True
            _war["ends"] = now + WAR_DURATION
            _war["cactus"] = 0
            _war["gun"] = 0
            _war["winner"] = None
    if _war["buff_ends"] and now >= _war["buff_ends"]:
        _war["buff_ends"] = 0
        _war["buff_side"] = None


def get_war_status() -> dict:
    with _lock:
        now = time.time()
        _ensure_war_schedule(now)
        return {
            "active": _war["active"],
            "ends": _war["ends"],
            "next_at": _war["next_at"],
            "cactus": _war["cactus"],
            "gun": _war["gun"],
            "buff_side": _war["buff_side"],
            "buff_ends": _war["buff_ends"],
            "winner": _war["winner"],
        }


def vote_war(side: str) -> tuple[bool, str]:
    """side: cactus | gun. Возвращает (ok, msg)."""
    with _lock:
        now = time.time()
        _ensure_war_schedule(now)
        if not _war["active"]:
            left = int(max(0, _war["next_at"] - now))
            return False, f"Война сейчас не идёт. Следующая через ~{left // 60} мин."
        if side == "cactus":
            _war["cactus"] += 1
            count = _war["cactus"]
            emoji = "🌵"
        else:
            _war["gun"] += 1
            count = _war["gun"]
            emoji = "🔫"
        left = int(_war["ends"] - now)
        return True, (
            f"{emoji} Голос учтён! Счёт: 🌵 {_war['cactus']} — 🔫 {_war['gun']}\n"
            f"До конца ~{left // 60}м {left % 60}с"
        )


def war_reward_mult(side: str | None) -> float:
    """x2 монеты/PP если игрок на стороне-победителе и бафф активен."""
    with _lock:
        now = time.time()
        _ensure_war_schedule(now)
        if _war["buff_side"] and _war["buff_ends"] > now and side == _war["buff_side"]:
            return 2.0
        return 1.0


def _ensure_glitch_schedule(now: float) -> None:
    if _glitch["active"] and now >= _glitch["ends"]:
        _glitch["active"] = False
        _glitch["next_at"] = now + random.randint(*GLITCH_COOLDOWN)
    if not _glitch["active"]:
        if _glitch["next_at"] == 0:
            _glitch["next_at"] = now + random.randint(10 * 60, 25 * 60)
        if now >= _glitch["next_at"]:
            _glitch["active"] = True
            _glitch["ends"] = now + GLITCH_DURATION


def is_glitch_active() -> bool:
    with _lock:
        now = time.time()
        _ensure_glitch_schedule(now)
        return _glitch["active"]


def get_glitch_status() -> dict:
    with _lock:
        now = time.time()
        _ensure_glitch_schedule(now)
        return {
            "active": _glitch["active"],
            "ends": _glitch["ends"],
            "next_at": _glitch["next_at"],
        }
