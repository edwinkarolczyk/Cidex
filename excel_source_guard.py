"""Read monitored Excel through a short-lived detached copy.

Hard CIDEX rule: no production Excel file (original or any user copy) may stay
open while CIDEX analyses it. A source handle exists only while bytes are
copied to a temporary local file. The handle is closed before the parser is
called, and the temporary file is always removed afterwards.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Callable


class UnstableExcelSourceError(RuntimeError):
    """The source changed while CIDEX was creating its detached copy."""


def _stat_signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return int(stat.st_mtime_ns), int(stat.st_size)


def parse_from_detached_copy(
    source: str | Path,
    parser: Callable[[str | Path, dict[str, Any] | None], Any],
    config: dict[str, Any] | None = None,
    *,
    copy_attempts: int = 3,
) -> Any:
    """Copy source, close it, parse only the copy, and always delete the copy."""
    source_path = Path(source)
    if not source_path.is_file():
        raise FileNotFoundError(f"Nie znaleziono pliku planu: {source_path}")

    attempts = max(1, int(copy_attempts))
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        fd, temp_name = tempfile.mkstemp(
            prefix="CIDEX_excel_",
            suffix=source_path.suffix,
        )
        os.close(fd)
        temp_path = Path(temp_name)

        try:
            before = _stat_signature(source_path)

            # To jedyne miejsce, w którym CIDEX otwiera plik produkcyjny.
            # Oba uchwyty są zamknięte przed uruchomieniem parsera Excela.
            with source_path.open("rb") as source_file, temp_path.open("wb") as temp_file:
                shutil.copyfileobj(source_file, temp_file, length=1024 * 1024)
                temp_file.flush()

            after = _stat_signature(source_path)
            copied_size = temp_path.stat().st_size
            if before != after or copied_size != after[1]:
                raise UnstableExcelSourceError(
                    "Plik Excel zmienił się podczas wykonywania kopii roboczej."
                )

            logging.debug(
                "[PLAN][SOURCE] source handle released before parsing: %s",
                source_path,
            )
            return parser(temp_path, config)
        except (PermissionError, OSError, UnstableExcelSourceError) as exc:
            last_error = exc
            if attempt >= attempts:
                break
            time.sleep(0.08 * attempt)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                logging.warning(
                    "[PLAN][SOURCE] temporary Excel copy could not be removed: %s",
                    temp_path,
                )

    raise UnstableExcelSourceError(
        "Nie udało się wykonać stabilnej kopii roboczej Excela po "
        f"{attempts} próbach. Plik źródłowy nie pozostał otwarty."
    ) from last_error


def install_excel_source_guard() -> None:
    """Patch PlanMonitor parsing so production Excel is never parsed directly."""
    import plan_monitor

    if getattr(plan_monitor, "_cidex_source_guard_installed", False):
        return

    original_parse = plan_monitor.parse_plan

    def guarded_parse_plan(
        path: str | Path,
        config: dict[str, Any] | None = None,
    ) -> Any:
        return parse_from_detached_copy(path, original_parse, config)

    plan_monitor.parse_plan = guarded_parse_plan
    plan_monitor._cidex_source_guard_installed = True
