"""Тонкий клієнт для офіційного Pinterest API v5.

Навмисно НЕ використовує браузерну автоматизацію (Selenium/Playwright) чи
емуляцію кліків людини. Publishing через офіційний Content API — це
санкціонований Pinterest спосіб для застосунків на кшталт Tailwind/Buffer/
Later: запити йдуть від імені авторизованого застосунку в межах офіційних
рейт-лімітів, тому Pinterest не сприймає це як "ботову" підозрілу
активність (на відміну від скрапінгу чи імітації браузера).
"""
from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any

import requests

API_BASE = "https://api.pinterest.com/v5"
TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"

# Токен оновлюємо трохи заздалегідь, щоб не зловити 401 всередині запиту.
REFRESH_MARGIN_SECONDS = 300


class PinterestAPIError(RuntimeError):
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"Pinterest API error {status_code}: {payload}")


class PinterestClient:
    def __init__(self, app_id: str, app_secret: str, refresh_token: str, state: dict):
        self.app_id = app_id
        self.app_secret = app_secret
        self.refresh_token = refresh_token
        self.state = state

    # -- OAuth ---------------------------------------------------------

    def _token_valid(self) -> bool:
        token = self.state.get("access_token")
        expires_at = self.state.get("access_token_expires_at", 0)
        return bool(token) and time.time() < (expires_at - REFRESH_MARGIN_SECONDS)

    def refresh_access_token(self) -> None:
        resp = requests.post(
            TOKEN_URL,
            auth=(self.app_id, self.app_secret),
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise PinterestAPIError(resp.status_code, _safe_json(resp))
        data = resp.json()
        self.state["access_token"] = data["access_token"]
        self.state["access_token_expires_at"] = time.time() + int(
            data.get("expires_in", 2592000)
        )
        # Pinterest інколи повертає новий refresh_token — зберігаємо, якщо є.
        if data.get("refresh_token"):
            self.refresh_token = data["refresh_token"]
            self.state["refresh_token"] = data["refresh_token"]

    def _ensure_token(self) -> str:
        if not self._token_valid():
            self.refresh_access_token()
        return self.state["access_token"]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._ensure_token()}"}

    # -- API calls -------------------------------------------------------

    def get_account(self) -> dict:
        resp = requests.get(f"{API_BASE}/user_account", headers=self._headers(), timeout=30)
        if resp.status_code != 200:
            raise PinterestAPIError(resp.status_code, _safe_json(resp))
        return resp.json()

    def create_pin(
        self,
        board_id: str,
        image_path: Path,
        title: str,
        description: str,
        link: str = "",
        alt_text: str = "",
    ) -> dict:
        content_type = _guess_content_type(image_path)
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")

        body: dict[str, Any] = {
            "board_id": board_id,
            "title": title[:100],
            "description": description[:500],
            "media_source": {
                "source_type": "image_base64",
                "content_type": content_type,
                "data": b64,
            },
        }
        if link:
            body["link"] = link
        if alt_text:
            body["alt_text"] = alt_text[:500]

        resp = self._request_with_retry("POST", f"{API_BASE}/pins", json_body=body)
        return resp.json()

    def _request_with_retry(
        self, method: str, url: str, json_body: dict | None = None, max_retries: int = 3
    ) -> requests.Response:
        for attempt in range(max_retries):
            resp = requests.request(
                method, url, headers=self._headers(), json=json_body, timeout=60
            )
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30))
                time.sleep(min(retry_after, 120))
                continue
            if resp.status_code == 401 and attempt == 0:
                # токен міг протухнути саме зараз — примусово оновлюємо й пробуємо ще раз
                self.refresh_access_token()
                continue
            if resp.status_code >= 400:
                raise PinterestAPIError(resp.status_code, _safe_json(resp))
            return resp
        raise PinterestAPIError(resp.status_code, _safe_json(resp))


def _guess_content_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")


def _safe_json(resp: requests.Response):
    try:
        return resp.json()
    except ValueError:
        return resp.text
