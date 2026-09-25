"""Точка входу для cron: перевіряє, чи настав час постити, і якщо так —
публікує один пін і одразу завершується.

Навмисно НЕ є довготривалим демоном/циклом зі sleep(): процес живе секунди,
займає пам'ять лише під час свого виконання, а решту часу нічого не
"крутиться у фоні". Виклик раз на N хвилин через cron/systemd timer.
"""
from __future__ import annotations

import argparse
import logging
import random
import time
from pathlib import Path

from .config import load_config
from .poster import run_once, setup_logging
from .state import load_state, save_state


def next_due_timestamp(config) -> float:
    hours = random.uniform(config.interval_hours_min, config.interval_hours_max)
    return time.time() + hours * 3600


def main() -> None:
    parser = argparse.ArgumentParser(description="Pinterest auto-poster (cron entrypoint)")
    parser.add_argument("--config", default=None, help="Шлях до config.yaml")
    parser.add_argument(
        "--force", action="store_true", help="Ігнорувати таймер і запостити зараз (для тестів)"
    )
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.log_file)

    state = load_state(config.state_file)
    now = time.time()
    next_due_at = state.get("next_due_at", 0)

    if not args.force and now < next_due_at:
        remaining_min = int((next_due_at - now) / 60)
        logging.info("Ще не час постити, залишилось ~%d хв.", remaining_min)
        return

    posted = run_once(config)

    state = load_state(config.state_file)
    if posted:
        state["last_post_at"] = now
    state["next_due_at"] = next_due_timestamp(config)
    save_state(config.state_file, state)
    logging.info(
        "Наступна публікація запланована через %.1f год.",
        (state["next_due_at"] - now) / 3600,
    )


if __name__ == "__main__":
    main()
