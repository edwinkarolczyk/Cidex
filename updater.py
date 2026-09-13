"""Self-update support for CIDEX Windows builds."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from version import APP_VERSION

RELEASE_API = "https://api.github.com/repos/edwinkarolczyk/Cidex/releases/latest"
ASSET_NAME = "Cidex.exe"
USER_AGENT = "CIDEX-Updater"


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    url: str
    size: int
    title: str


def version_tuple(value: str) -> tuple[int, int, int]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(value or ""))
    if not match:
        return (0, 0, 0)
    return tuple(int(part) for part in match.groups())


class CidexUpdater:
    @staticmethod
    def latest(timeout: int = 10) -> ReleaseInfo | None:
        request = urllib.request.Request(
            RELEASE_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": USER_AGENT,
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise UpdateError(f"Nie udało się sprawdzić aktualizacji: HTTP {exc.code}.") from exc
        except Exception as exc:
            raise UpdateError(f"Nie udało się sprawdzić aktualizacji CIDEX: {exc}") from exc

        title = str(payload.get("name") or payload.get("tag_name") or "").strip()
        version_match = re.search(r"(\d+\.\d+\.\d+)", title)
        version = version_match.group(1) if version_match else ""
        if not version:
            return None

        assets = payload.get("assets") or []
        asset = next(
            (
                item
                for item in assets
                if str(item.get("name") or "").casefold() == ASSET_NAME.casefold()
            ),
            None,
        )
        if asset is None:
            asset = next(
                (
                    item
                    for item in assets
                    if str(item.get("name") or "").lower().endswith(".exe")
                ),
                None,
            )
        if asset is None:
            return None

        url = str(asset.get("browser_download_url") or "").strip()
        if not url:
            return None
        return ReleaseInfo(
            version=version,
            url=url,
            size=int(asset.get("size") or 0),
            title=title or f"CIDEX {version}",
        )

    @staticmethod
    def is_newer(info: ReleaseInfo) -> bool:
        return version_tuple(info.version) > version_tuple(APP_VERSION)

    @staticmethod
    def download(
        info: ReleaseInfo,
        on_progress: Callable[[float], None] | None = None,
        attempts: int = 4,
    ) -> Path:
        target = Path(tempfile.gettempdir()) / f"CIDEX-update-{info.version}.exe"
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            existing = target.stat().st_size if target.exists() else 0
            if info.size > 0 and existing > info.size:
                target.unlink(missing_ok=True)
                existing = 0
            if info.size > 0 and existing == info.size:
                if on_progress:
                    on_progress(1.0)
                return target

            request = urllib.request.Request(
                info.url,
                headers={
                    "Accept": "application/octet-stream",
                    "User-Agent": USER_AGENT,
                    **({"Range": f"bytes={existing}-"} if existing else {}),
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=25) as response:
                    status = getattr(response, "status", response.getcode())
                    if existing and status == 200:
                        target.unlink(missing_ok=True)
                        existing = 0
                    elif status not in (200, 206):
                        raise UpdateError(f"Pobieranie aktualizacji: HTTP {status}.")

                    mode = "ab" if existing and status == 206 else "wb"
                    received = existing if mode == "ab" else 0
                    expected = info.size or (
                        received + int(response.headers.get("Content-Length") or 0)
                    )
                    with target.open(mode) as stream:
                        while True:
                            chunk = response.read(1024 * 256)
                            if not chunk:
                                break
                            stream.write(chunk)
                            received += len(chunk)
                            if on_progress and expected > 0:
                                on_progress(min(1.0, received / expected))

                final_size = target.stat().st_size if target.exists() else 0
                if final_size <= 0:
                    raise UpdateError("Pobrany plik aktualizacji jest pusty.")
                if info.size > 0 and final_size != info.size:
                    raise UpdateError(
                        f"Niepełny plik: {final_size} z {info.size} bajtów."
                    )
                if on_progress:
                    on_progress(1.0)
                return target
            except Exception as exc:
                last_error = exc if isinstance(exc, Exception) else Exception(str(exc))
                if attempt < attempts:
                    time.sleep(attempt * 2)

        raise UpdateError(
            "Połączenie przerwano podczas pobierania. CIDEX próbował 4 razy "
            "i zachował pobraną część do wznowienia."
        ) from last_error

    @staticmethod
    def launch_replace(downloaded_exe: Path) -> None:
        if not getattr(sys, "frozen", False):
            raise UpdateError(
                "Automatyczna podmiana działa w Cidex.exe. "
                "Przy uruchomieniu z Pythona zbuduj lub pobierz EXE."
            )

        current = Path(sys.executable).resolve()
        if current.suffix.lower() != ".exe":
            raise UpdateError("Nie udało się ustalić pliku Cidex.exe.")
        if not downloaded_exe.is_file():
            raise UpdateError("Brak pobranego pliku aktualizacji.")

        directory = current.parent
        probe = directory / ".cidex_update_write_test"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError as exc:
            raise UpdateError(
                "Brak uprawnień do podmiany Cidex.exe w tym folderze."
            ) from exc

        batch = Path(tempfile.gettempdir()) / "cidex_apply_update.bat"
        batch.write_text(
            "@echo off\r\n"
            "setlocal\r\n"
            "ping 127.0.0.1 -n 3 >nul\r\n"
            f'copy /Y "{downloaded_exe}" "{current}" >nul\r\n'
            "if errorlevel 1 exit /b 1\r\n"
            f'del /Q "{downloaded_exe}" >nul 2>&1\r\n'
            f'start "" "{current}"\r\n'
            'del "%~f0"\r\n',
            encoding="utf-8",
        )
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0
        )
        subprocess.Popen(
            ["cmd.exe", "/c", str(batch)],
            cwd=str(directory),
            creationflags=flags,
            close_fds=True,
        )
