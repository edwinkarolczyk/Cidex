"""Small table-width adjustments for CIDEX."""

from __future__ import annotations

from typing import Any

SYMBOL_WIDTH = 173
SYMBOL_MIN_WIDTH = 120


def install_column_widths(app_class: type[Any]) -> None:
    """Narrow Symbol by one third and let the WM/department column fill space."""
    if getattr(app_class, "_cidex_column_widths_installed", False):
        return

    original_build_ui = app_class._build_ui

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self.table.column(
            "symbol",
            width=SYMBOL_WIDTH,
            minwidth=SYMBOL_MIN_WIDTH,
            stretch=False,
        )
        self.table.column("department", stretch=True)

    app_class._build_ui = build_ui
    app_class._cidex_column_widths_installed = True
