"""Small runtime fixes for CIDEX without changing the PlanMonitor data model."""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import plan_monitor


def display_change_value(value: Any) -> Any:
    """Return a compact value for UI cells instead of rendering a whole row dict."""
    if isinstance(value, dict):
        quantity = value.get("quantity")
        return "" if quantity is None else quantity
    return "" if value is None else value


def _source_key(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return os.path.normcase(os.path.abspath(text)).casefold()
    except (OSError, ValueError):
        return text.casefold()


def same_snapshot_source(snapshot: dict[str, Any] | None, plan_file: str) -> bool:
    if not snapshot:
        return True
    return _source_key(snapshot.get("source_file")) == _source_key(plan_file)


def _install_display_fix(launcher_module: Any) -> None:
    original = launcher_module.enrich_changes_with_wm
    if getattr(original, "_cidex_display_fix", False):
        return

    def enrich_for_display(changes: list[dict[str, Any]], root: str) -> list[dict[str, Any]]:
        enriched = original(changes, root)
        for item in enriched:
            item["old"] = display_change_value(item.get("old", ""))
            item["new"] = display_change_value(item.get("new", ""))
        return enriched

    enrich_for_display._cidex_display_fix = True  # type: ignore[attr-defined]
    launcher_module.enrich_changes_with_wm = enrich_for_display


def _install_snapshot_source_fix() -> None:
    original = plan_monitor.PlanMonitor.check
    if getattr(original, "_cidex_snapshot_source_fix", False):
        return

    def check(self: Any, force: bool = False) -> Any:
        plan_file = str(self.config.get("plan_file", "") or "").strip()
        snapshot = plan_monitor.load_snapshot(self.snapshot_path)
        if plan_file and snapshot and not same_snapshot_source(snapshot, plan_file):
            checked_at = datetime.now().strftime("%H:%M:%S")
            try:
                stat = os.stat(plan_file)
                signature = (stat.st_mtime, stat.st_size)
                modified_at = datetime.fromtimestamp(stat.st_mtime).strftime("%H:%M:%S")
                parsed = self._read(plan_file)
                rows = parsed.rows
                parser = asdict(parsed.diagnostics)
                metadata = {
                    "plan_file": plan_file,
                    "read_at": datetime.now().isoformat(timespec="seconds"),
                    "sheet": parsed.diagnostics.sheet,
                    "parser": parser,
                }
                plan_monitor.save_snapshot(rows, metadata, self.snapshot_path)
                self.last_signature = signature
                self.last_parser = parser
                self.last_rows = rows
                return plan_monitor.CheckResult(
                    "unchanged",
                    checked_at,
                    modified_at,
                    [],
                    "Wybrano inny plik Excel — zapisano nowy punkt bazowy bez porównania z poprzednim plikiem.",
                    parser,
                    rows,
                )
            except Exception as error:
                message = f"Błąd odczytu pliku: {error}"
                return plan_monitor.CheckResult(
                    "error",
                    checked_at,
                    message=message,
                    error=message,
                )
        return original(self, force=force)

    check._cidex_snapshot_source_fix = True  # type: ignore[attr-defined]
    plan_monitor.PlanMonitor.check = check


def install_runtime_fixes(launcher_module: Any) -> None:
    _install_display_fix(launcher_module)
    _install_snapshot_source_fix()
