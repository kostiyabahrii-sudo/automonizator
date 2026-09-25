"""Завантаження конфігурації з config.yaml + .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    app_id: str
    app_secret: str
    refresh_token: str
    board_id: str

    pending_dir: Path
    posted_dir: Path
    failed_dir: Path
    state_file: Path
    log_file: Path

    interval_hours_min: float
    interval_hours_max: float

    descriptions: list[str] = field(default_factory=list)
    link: str = ""
    title_from_filename: bool = True
    alt_text_from_title: bool = True

    @property
    def env_file(self) -> Path:
        return ROOT_DIR / ".env"


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT_DIR / p


def load_config(config_path: str | Path | None = None) -> Config:
    load_dotenv(ROOT_DIR / ".env")

    config_path = Path(config_path) if config_path else ROOT_DIR / "config.yaml"
    if not config_path.exists():
        example = ROOT_DIR / "config.example.yaml"
        raise FileNotFoundError(
            f"Не знайдено {config_path}. Скопіюй {example} у {config_path} "
            "і заповни своїми значеннями."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    app_id = os.environ.get("PINTEREST_APP_ID", "")
    app_secret = os.environ.get("PINTEREST_APP_SECRET", "")
    refresh_token = os.environ.get("PINTEREST_REFRESH_TOKEN", "")
    board_id = os.environ.get("PINTEREST_BOARD_ID", "")

    missing = [
        name
        for name, val in [
            ("PINTEREST_APP_ID", app_id),
            ("PINTEREST_APP_SECRET", app_secret),
            ("PINTEREST_BOARD_ID", board_id),
        ]
        if not val
    ]
    if missing:
        raise RuntimeError(
            "У .env не заповнені змінні: " + ", ".join(missing) +
            ". Скопіюй .env.example у .env і заповни."
        )

    raw_desc = raw.get("description", "")
    descriptions = raw_desc if isinstance(raw_desc, list) else [raw_desc]
    descriptions = [d.strip() for d in descriptions if str(d).strip()]
    if not descriptions:
        raise RuntimeError("У config.yaml не задано 'description'.")

    return Config(
        app_id=app_id,
        app_secret=app_secret,
        refresh_token=refresh_token,
        board_id=board_id,
        pending_dir=_resolve(raw.get("pending_dir", "posts/pending")),
        posted_dir=_resolve(raw.get("posted_dir", "posts/posted")),
        failed_dir=_resolve(raw.get("failed_dir", "posts/failed")),
        state_file=_resolve(raw.get("state_file", "state/state.json")),
        log_file=_resolve(raw.get("log_file", "logs/poster.log")),
        interval_hours_min=float(raw.get("interval_hours_min", 5)),
        interval_hours_max=float(raw.get("interval_hours_max", 6)),
        descriptions=descriptions,
        link=raw.get("link", "") or "",
        title_from_filename=bool(raw.get("title_from_filename", True)),
        alt_text_from_title=bool(raw.get("alt_text_from_title", True)),
    )
