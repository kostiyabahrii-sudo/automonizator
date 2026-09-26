"""Логіка одного циклу публікації: взяти картинку -> запостити -> архівувати."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import random
import re
import shutil
from pathlib import Path

from .config import Config
from .pinterest_client import PinterestAPIError, PinterestClient

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5, encoding="utf-8"),
            logging.StreamHandler()
        ],
    )


def pick_next_image(pending_dir: Path) -> Path | None:
    pending_dir.mkdir(parents=True, exist_ok=True)
    candidates = sorted(
        p for p in pending_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )
    return candidates[0] if candidates else None


def build_title(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    stem = re.sub(r"\s+", " ", stem)
    return stem.title() if stem else "Untitled"


def pick_description(descriptions: list[str]) -> str:
    return random.choice(descriptions)


def run_once(config: Config) -> bool:
    """Публікує один пін, якщо є що постити. Повертає True, якщо щось запостили."""
    image_path = pick_next_image(config.pending_dir)
    if image_path is None:
        logging.info("Немає нових картинок у %s — пропускаю цикл.", config.pending_dir)
        return False

    title = build_title(image_path.name) if config.title_from_filename else image_path.stem
    description = pick_description(config.descriptions)
    alt_text = title if config.alt_text_from_title else ""

    from .state import load_state, save_state

    state = load_state(config.state_file)
    client = PinterestClient(config.app_id, config.app_secret, config.refresh_token, state)

    try:
        result = client.create_pin(
            board_id=config.board_id,
            image_path=image_path,
            title=title,
            description=description,
            link=config.link,
            alt_text=alt_text,
        )
        save_state(config.state_file, state)
    except PinterestAPIError as e:
        save_state(config.state_file, state)
        logging.error("Помилка публікації %s: %s", image_path.name, e)
        _move_to(image_path, config.failed_dir)
        return False
    except Exception:
        save_state(config.state_file, state)
        logging.exception("Неочікувана помилка під час публікації %s", image_path.name)
        _move_to(image_path, config.failed_dir)
        return False

    pin_id = result.get("id", "?")
    logging.info("Опубліковано пін %s з файлу %s (title=%r)", pin_id, image_path.name, title)
    _move_to(image_path, config.posted_dir)
    return True


def _move_to(image_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / image_path.name
    if destination.exists():
        destination = target_dir / f"{image_path.stem}_{int(image_path.stat().st_mtime)}{image_path.suffix}"
    shutil.move(str(image_path), str(destination))
