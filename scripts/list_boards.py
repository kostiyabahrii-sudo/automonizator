"""Друкує список дошок акаунта разом з їх ID — щоб знайти PINTEREST_BOARD_ID.

Запуск: python -m scripts.list_boards
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pinterest_autopost.config import load_config
from pinterest_autopost.pinterest_client import PinterestClient, API_BASE
from pinterest_autopost.state import load_state, save_state
import requests


def main() -> None:
    config = load_config()
    state = load_state(config.state_file)
    client = PinterestClient(config.app_id, config.app_secret, config.refresh_token, state)

    resp = requests.get(f"{API_BASE}/boards", headers=client._headers(), timeout=30)
    save_state(config.state_file, state)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        print("Дошок не знайдено (або в токена немає boards:read).")
        return
    for board in items:
        print(f"{board['id']}\t{board.get('name')}")


if __name__ == "__main__":
    main()
