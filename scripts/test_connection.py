"""Перевіряє, що токен, board_id і доступ до API налаштовані правильно,
без публікації жодного піна.

Запуск: python -m scripts.test_connection
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pinterest_autopost.config import load_config
from pinterest_autopost.pinterest_client import PinterestAPIError, PinterestClient
from pinterest_autopost.state import load_state, save_state


def main() -> None:
    config = load_config()
    state = load_state(config.state_file)
    client = PinterestClient(config.app_id, config.app_secret, config.refresh_token, state)

    try:
        account = client.get_account()
    except PinterestAPIError as e:
        print(f"Помилка: {e}")
        raise SystemExit(1)
    finally:
        save_state(config.state_file, state)

    print("З'єднання ОК. Акаунт:", account.get("username", account))
    print("Board ID у конфізі:", config.board_id)
    print(f"Картинок в черзі ({config.pending_dir}):")
    for p in sorted(config.pending_dir.glob("*")):
        print(" -", p.name)


if __name__ == "__main__":
    main()
