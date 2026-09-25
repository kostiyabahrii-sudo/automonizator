"""Одноразовий інтерактивний скрипт: авторизує застосунок у Pinterest і
зберігає refresh_token у .env, щоб scheduler.py міг далі оновлювати
access_token самостійно без участі людини.

Запуск: python -m pinterest_autopost.oauth_setup
"""
from __future__ import annotations

import os
import urllib.parse
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key

ROOT_DIR = Path(__file__).resolve().parent.parent
AUTH_URL = "https://www.pinterest.com/oauth/"
TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"

# Мінімальний набір прав, достатній для читання дошок і публікації пінів.
SCOPES = "boards:read,pins:read,pins:write"


def main() -> None:
    env_path = ROOT_DIR / ".env"
    load_dotenv(env_path)

    app_id = os.environ.get("PINTEREST_APP_ID") or input("PINTEREST_APP_ID: ").strip()
    app_secret = os.environ.get("PINTEREST_APP_SECRET") or input("PINTEREST_APP_SECRET: ").strip()
    redirect_uri = input(
        "Redirect URI, точно як вказано у налаштуваннях застосунку "
        "(напр. https://localhost/callback): "
    ).strip()

    params = {
        "response_type": "code",
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
    }
    print("\n1) Відкрий у браузері (де залогінений потрібний Pinterest-акаунт):\n")
    print(AUTH_URL + "?" + urllib.parse.urlencode(params))
    print(
        "\n2) Підтверди доступ. Тебе перекине на redirect_uri з параметром "
        "?code=..., навіть якщо сторінка покаже помилку 'не вдається "
        "відкрити' — код буде видно в адресному рядку.\n"
    )
    code = input("Встав сюди значення параметра code: ").strip()

    resp = requests.post(
        TOKEN_URL,
        auth=(app_id, app_secret),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"Помилка обміну коду на токен: {resp.status_code} {resp.text}")
        raise SystemExit(1)

    data = resp.json()
    refresh_token = data["refresh_token"]

    if not env_path.exists():
        env_path.write_text("", encoding="utf-8")
    set_key(str(env_path), "PINTEREST_APP_ID", app_id)
    set_key(str(env_path), "PINTEREST_APP_SECRET", app_secret)
    set_key(str(env_path), "PINTEREST_REFRESH_TOKEN", refresh_token)

    print(f"\nГотово. refresh_token збережено у {env_path}.")
    print("Тепер заповни PINTEREST_BOARD_ID у .env (можна взяти зі скрипта scripts/list_boards.py)")


if __name__ == "__main__":
    main()
