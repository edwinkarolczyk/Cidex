from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys

from wm_store import inspect_root


class MobileApiLaunchError(RuntimeError):
    pass


def app_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def api_command() -> list[str]:
    base = app_directory()
    if getattr(sys, "frozen", False):
        target = base / "Cidex_Api.exe"
        if not target.is_file():
            raise MobileApiLaunchError(
                "Brak Cidex_Api.exe obok Cidex.exe. Pobierz lub zbuduj komplet CIDEX."
            )
        return [str(target)]

    target = base / "api_server.py"
    if not target.is_file():
        raise MobileApiLaunchError("Brak api_server.py w katalogu CIDEX.")
    return [sys.executable, str(target)]


class MobileApiController:
    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None

    @property
    def pid(self) -> int | None:
        return self._process.pid if self.is_running() else None

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self, root: str | Path) -> int:
        if self.is_running():
            assert self._process is not None
            return int(self._process.pid)

        inspect_root(root)
        command = api_command()
        kwargs: dict = {"cwd": str(app_directory())}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        try:
            self._process = subprocess.Popen(command, **kwargs)
        except OSError as exc:
            self._process = None
            raise MobileApiLaunchError(f"Nie udało się uruchomić CIDEX Mobile API: {exc}") from exc
        return int(self._process.pid)

    def stop(self) -> None:
        process = self._process
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        self._process = None
