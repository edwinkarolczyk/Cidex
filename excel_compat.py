"""Compatibility helpers for Excel files without worksheet dimensions."""

from __future__ import annotations

from typing import Any

import plan_monitor


def ensure_readonly_dimensions(workbook: Any) -> Any:
    """Calculate dimensions when a read-only worksheet has no max_row metadata."""
    for worksheet in getattr(workbook, "worksheets", []):
        if getattr(worksheet, "max_row", None) is not None:
            continue
        try:
            worksheet.calculate_dimension(force=True)
        except (AttributeError, TypeError, ValueError, UnboundLocalError):
            # An entirely empty worksheet can also be unsized. Treat it as empty
            # instead of letting PlanMonitor compare None with an integer.
            if hasattr(worksheet, "_max_row"):
                worksheet._max_row = 0
            if hasattr(worksheet, "_max_column"):
                worksheet._max_column = 0
    return workbook


def install_plan_monitor_excel_fix() -> None:
    """Wrap PlanMonitor's loader so unsized workbooks are made safe before parsing."""
    original = plan_monitor.load_workbook
    if getattr(original, "_cidex_unsized_excel_fix", False):
        return

    def load_workbook_sized(*args: Any, **kwargs: Any) -> Any:
        workbook = original(*args, **kwargs)
        return ensure_readonly_dimensions(workbook)

    load_workbook_sized._cidex_unsized_excel_fix = True  # type: ignore[attr-defined]
    plan_monitor.load_workbook = load_workbook_sized
