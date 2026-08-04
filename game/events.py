"""Случайные ивенты."""
import random
import threading
import time

_event_lock = threading.Lock()
CURRENT_EVENT = {"type": None, "name": "", "ends": 0}

EVENT_TYPES = {
    "double_coins": ("💰 x2 монеты", 2.0, 1.0),
    "double_pp": ("⚡ x2 очки силы", 1.0, 2.0),
    "more_cases": ("🎁 Больше кейсов", 1.0, 1.0),
    "double_xp": ("🎟 x2 XP сезона", 1.0, 1.0),
}


def get_active_event():
    with _event_lock:
        if CURRENT_EVENT["type"] and time.time() < CURRENT_EVENT["ends"]:
            return CURRENT_EVENT
        if CURRENT_EVENT["type"] and time.time() >= CURRENT_EVENT["ends"]:
            CURRENT_EVENT["type"] = None
            CURRENT_EVENT["name"] = ""
            CURRENT_EVENT["ends"] = 0
        # 8% шанс запустить ивент при проверке (раз в бой/ежедневку)
        if random.random() < 0.08 and CURRENT_EVENT["type"] is None:
            etype = random.choice(list(EVENT_TYPES.keys()))
            name, _, _ = EVENT_TYPES[etype]
            CURRENT_EVENT["type"] = etype
            CURRENT_EVENT["name"] = name
            CURRENT_EVENT["ends"] = time.time() + random.randint(45, 90) * 60  # 45-90 мин
        return CURRENT_EVENT if CURRENT_EVENT["type"] else None
