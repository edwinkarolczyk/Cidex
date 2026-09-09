from __future__ import annotations

import json
import os
from pathlib import Path
import secrets

APP_DIR = Path(os.getenv("APPDATA") or Path.home()) / "Cidex"
CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_API_PORT = 8765


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
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temp, CONFIG_PATH)


def get_saved_root() -> str:
    return str(load_config().get("wm_root") or "").strip()


def set_saved_root(path: str) -> None:
    data = load_config()
    data["wm_root"] = str(path or "").strip()
    save_config(data)


def get_api_token() -> str:
    data = load_config()
    token = str(data.get("api_token") or "").strip()
    if token:
        return token
    token = secrets.token_urlsafe(24)
    data["api_token"] = token
    save_config(data)
    return token


def set_api_token(token: str) -> None:
    value = str(token or "").strip()
    if not value:
        raise ValueError("Token API nie może być pusty.")
    data = load_config()
    data["api_token"] = value
    save_config(data)


def get_api_port() -> int:
    data = load_config()
    try:
        port = int(data.get("api_port") or DEFAULT_API_PORT)
    except (TypeError, ValueError):
        return DEFAULT_API_PORT
    return port if 1024 <= port <= 65535 else DEFAULT_API_PORT


def set_api_port(port: int) -> None:
    value = int(port)
    if not 1024 <= value <= 65535:
        raise ValueError("Port API musi być z zakresu 1024-65535.")
    data = load_config()
    data["api_port"] = value
    save_config(data)
