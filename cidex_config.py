from __future__ import annotations

import json
import os
from pathlib import Path

APP_DIR = Path(os.getenv("APPDATA") or Path.home()) / "Cidex"
CONFIG_PATH = APP_DIR / "config.json"


def load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(data: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    temp = CONFIG_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, CONFIG_PATH)


def get_saved_root() -> str:
    return str(load_config().get("wm_root") or "").strip()


def set_saved_root(path: str) -> None:
    data = load_config()
    data["wm_root"] = str(path or "").strip()
    save_config(data)
