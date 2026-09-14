"""UI patch adding live search and quick filters to CIDEX."""

from __future__ import annotations

import tkinter as tk
from typing import Any

from search_filter import FILTERS, filter_changes


def install_search_ui(app_class: type[Any]) -> None:
    if getattr(app_class, "_cidex_search_ui_installed", False):
        return

    original_build_ui = app_class._build_ui
    original_render = app_class._render

    def build_ui(self: Any) -> None:
        original_build_ui(self)

        from main import BG, MUTED, PANEL, TEXT

        self._cidex_search_var = tk.StringVar(value="")
        self._cidex_filter_var = tk.StringVar(value="Wszystkie")
        self._cidex_filter_buttons: dict[str, tk.Button] = {}

        frame = tk.Frame(
            self,
            bg=PANEL,
            highlightbackground="#263442",
            highlightthickness=1,
            padx=12,
            pady=9,
        )
        frame.pack(fill="x", padx=24, pady=(0, 8), before=self.table.master)

        tk.Label(
            frame,
            text="Szukaj:",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 7))

        entry = tk.Entry(
            frame,
            textvariable=self._cidex_search_var,
            bg="#0F1821",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            width=28,
            font=("Segoe UI", 10),
        )
        entry.pack(side="left", padx=(0, 12), ipady=5)

        tk.Label(
            frame,
            text="Filtr:",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 6))

        for name in FILTERS:
            button = tk.Button(
                frame,
                text=name,
                command=lambda value=name: self._cidex_set_quick_filter(value),
                bg="#344553",
                fg="white",
                activebackground="#405463",
                activeforeground="white",
                bd=0,
                padx=8,
                pady=5,
                font=("Segoe UI", 8, "bold"),
                cursor="hand2",
            )
            button.pack(side="left", padx=(0, 5))
            self._cidex_filter_buttons[name] = button

        self._cidex_search_count = tk.StringVar(value="")
        tk.Label(
            frame,
            textvariable=self._cidex_search_count,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(side="right")

        self._cidex_search_var.trace_add("write", lambda *_args: self._cidex_apply_search())
        self._cidex_update_filter_buttons()

    def update_filter_buttons(self: Any) -> None:
        selected = self._cidex_filter_var.get()
        for name, button in self._cidex_filter_buttons.items():
            button.configure(bg="#1677FF" if name == selected else "#344553")

    def set_quick_filter(self: Any, value: str) -> None:
        self._cidex_filter_var.set(value)
        self._cidex_update_filter_buttons()
        self._cidex_apply_search()

    def apply_search(self: Any) -> None:
        source = list(getattr(self, "last_changes", []) or [])
        visible = filter_changes(
            source,
            self._cidex_search_var.get(),
            self._cidex_filter_var.get(),
        )
        original_render(self, visible)
        self._cidex_search_count.set(f"Widoczne: {len(visible)} / {len(source)}")

    def render(self: Any, changes: list[dict[str, Any]]) -> None:
        if not hasattr(self, "_cidex_search_var"):
            original_render(self, changes)
            return
        visible = filter_changes(
            changes,
            self._cidex_search_var.get(),
            self._cidex_filter_var.get(),
        )
        original_render(self, visible)
        self._cidex_search_count.set(f"Widoczne: {len(visible)} / {len(changes)}")

    app_class._build_ui = build_ui
    app_class._render = render
    app_class._cidex_update_filter_buttons = update_filter_buttons
    app_class._cidex_set_quick_filter = set_quick_filter
    app_class._cidex_apply_search = apply_search
    app_class._cidex_search_ui_installed = True
