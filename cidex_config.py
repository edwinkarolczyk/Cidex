from __future__ import annotations

import json
import os
from pathlib import Path
import secrets

APP_DIR = Path(os.getenv("APPDATA") or Path.home()) / "Cidex"
CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_API_PORT = 8765
API_TOKEN_LENGTH = 6
API_TOKEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


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


def _new_api_token() -> str:
    return "".join(secrets.choice(API_TOKEN_ALPHABET) for _ in range(API_TOKEN_LENGTH))


def _valid_api_token(token: str) -> bool:
    value = str(token or "").strip().upper()
    return len(value) == API_TOKEN_LENGTH and all(ch in API_TOKEN_ALPHABET for ch in value)


def get_api_token() -> str:
    data = load_config()
    token = str(data.get("api_token") or "").strip().upper()
    if _valid_api_token(token):
        return token

    # Migracja poprzedniego długiego tokenu: przy pierwszym uruchomieniu
    # po aktualizacji nadajemy nowy, krótki kod WMM.
    token = _new_api_token()
    data["api_token"] = token
    save_config(data)
    return token


def set_api_token(token: str) -> None:
    value = str(token or "").strip().upper()
    if not _valid_api_token(value):
        raise ValueError(
            f"Token WMM musi mieć dokładnie {API_TOKEN_LENGTH} znaków: "
            "duże litery i cyfry bez mylących znaków."
        )
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
