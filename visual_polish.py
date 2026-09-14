"""Small visual polish for the CIDEX desktop shell."""

from __future__ import annotations

import tkinter as tk
from typing import Any

from main import BG, BORDER, MUTED, PANEL, TEXT
from version import APP_VERSION

ACTIVE = "#2DD4BF"
CHECKING = "#FFD166"
ERROR = "#FF5C5C"
IDLE = "#9BA9B7"
BADGE_BG = "#10202A"


def monitoring_badge_style(state: str) -> tuple[str, str]:
    """Return label and colour for the monitoring state badge."""
    states = {
        "active": ("Monitoring aktywny", ACTIVE),
        "checking": ("Sprawdzanie…", CHECKING),
        "error": ("Błąd monitoringu", ERROR),
        "idle": ("Oczekiwanie", IDLE),
    }
    return states.get(state, states["idle"])


def install_visual_polish(app_class: type[Any]) -> None:
    """Add a compact monitoring badge, refreshed title and author credit."""
    if getattr(app_class, "_cidex_visual_polish_installed", False):
        return

    original_init = app_class.__init__
    original_build_ui = app_class._build_ui
    original_check_async = app_class._check_async
    original_handle_result = app_class._handle_result

    def set_monitoring_state(self: Any, state: str) -> None:
        label, colour = monitoring_badge_style(state)
        text_var = getattr(self, "_cidex_monitor_text", None)
        dot = getattr(self, "_cidex_monitor_dot", None)
        text_label = getattr(self, "_cidex_monitor_label", None)
        if text_var is not None:
            text_var.set(label)
        if dot is not None:
            dot.configure(fg=colour)
        if text_label is not None:
            text_label.configure(fg=colour)

    def build_ui(self: Any) -> None:
        original_build_ui(self)

        header = None
        status_panel = None
        for child in self.winfo_children():
            if not isinstance(child, tk.Frame):
                continue
            labels = [
                widget
                for widget in child.winfo_children()
                if isinstance(widget, tk.Label)
            ]
            texts = {str(widget.cget("text")) for widget in labels}
            if "CIDEX" in texts:
                header = child
            if "Plik:" in texts and "Status:" in texts:
                status_panel = child

        if header is not None:
            for widget in list(header.winfo_children()):
                if not isinstance(widget, tk.Label):
                    continue
                text = str(widget.cget("text"))
                if text.strip() == "PORÓWNANIE PLANU EXCEL":
                    widget.configure(text="  PORÓWNYWANIE PLANU")
                elif text == "mechanizm porównania jak w WM":
                    widget.destroy()

            badge = tk.Frame(
                header,
                bg=BADGE_BG,
                highlightbackground=BORDER,
                highlightthickness=1,
                padx=12,
                pady=7,
            )
            badge.pack(side="right")
            self._cidex_monitor_text = tk.StringVar(value="Oczekiwanie")
            self._cidex_monitor_dot = tk.Label(
                badge,
                text="●",
                bg=BADGE_BG,
                fg=IDLE,
                font=("Segoe UI", 13, "bold"),
            )
            self._cidex_monitor_dot.pack(side="left", padx=(0, 7))
            self._cidex_monitor_label = tk.Label(
                badge,
                textvariable=self._cidex_monitor_text,
                bg=BADGE_BG,
                fg=IDLE,
                font=("Segoe UI", 10, "bold"),
            )
            self._cidex_monitor_label.pack(side="left")

        if status_panel is not None:
            subtitle = tk.Frame(self, bg=BG)
            subtitle.pack(
                fill="x",
                padx=24,
                pady=(0, 10),
                before=status_panel,
            )
            tk.Label(
                subtitle,
                text="Automatyczne porównywanie pliku Excel z danymi Warsztat Menager",
                bg=BG,
                fg=MUTED,
                font=("Segoe UI", 9),
            ).pack(side="left")
            tk.Label(
                subtitle,
                text="Stworzone przez Edwin Karolczyk dla Metalbox sp. z o.o.",
                bg=BG,
                fg=TEXT,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="right")

        set_monitoring_state(self, "idle")

    def init(self: Any, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        self.title(f"CIDEX {APP_VERSION} — porównywanie planu Excel")

    def check_async(self: Any, force: bool) -> Any:
        result = original_check_async(self, force)
        if getattr(self, "_checking", False):
            set_monitoring_state(self, "checking")
        return result

    def handle_result(self: Any, result: Any) -> Any:
        if getattr(result, "status", "") == "error":
            set_monitoring_state(self, "error")
        else:
            set_monitoring_state(self, "active")
        return original_handle_result(self, result)

    app_class.__init__ = init
    app_class._build_ui = build_ui
    app_class._check_async = check_async
    app_class._handle_result = handle_result
    app_class._cidex_set_monitoring_state = set_monitoring_state
    app_class._cidex_visual_polish_installed = True
