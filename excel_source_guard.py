"""Read monitored Excel through a short-lived detached copy.

CIDEX must never keep the production Excel workbook open between checks.  The
source is opened only long enough to copy its bytes to a temporary local file;
all parsing then happens against that copy.  This keeps the comparison logic
unchanged while making the lifetime of the source handle explicit and short.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable


def parse_from_detached_copy(
    source: str | Path,
    parser: Callable[[str | Path, dict[str, Any] | None], Any],
    config: dict[str, Any] | None = None,
) -> Any:
    """Copy *source*, close it, parse the copy, and always delete the copy."""
    source_path = Path(source)
    if not source_path.is_file():
        return parser(source_path, config)

    fd, temp_name = tempfile.mkstemp(
        prefix="CIDEX_excel_",
        suffix=source_path.suffix,
    )
    os.close(fd)
    temp_path = Path(temp_name)

    try:
        # Explicit with-blocks make the source-handle lifetime unambiguous.
        with source_path.open("rb") as source_file, temp_path.open("wb") as temp_file:
            shutil.copyfileobj(source_file, temp_file, length=1024 * 1024)
            temp_file.flush()

        logging.debug(
            "[PLAN][SOURCE] released source handle before parsing: %s",
            source_path,
        )
        return parser(temp_path, config)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            logging.warning(
                "[PLAN][SOURCE] temporary Excel copy could not be removed: %s",
                temp_path,
            )


def install_excel_source_guard() -> None:
    """Patch PlanMonitor parsing so the original Excel is never parsed directly."""
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
