"""Clearer CIDEX settings without changing monitor comparison semantics."""

from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from background_mode import (
    get_minimize_to_tray,
    is_windows_autostart_enabled,
    set_minimize_to_tray,
    set_windows_autostart,
)
from cidex_config import get_saved_root, set_saved_root
from main import ACCENT, BG, BORDER, MUTED, PANEL, SUCCESS, TEXT
from plan_monitor import DEFAULT_COLUMN_MAPPING, FIELDS, SUPPORTED_EXTENSIONS, save_config

INTERVAL_CHOICES = (15, 30, 60, 120, 300)


def build_plan_config(current: dict[str, Any], values: dict[str, str]) -> dict[str, Any]:
    """Validate editable strings and preserve unrelated existing config keys."""
    interval = max(1, int(values["check_interval_seconds"].strip() or "60"))
    header_scan_rows = max(1, int(values["header_scan_rows"].strip() or "15"))

    def optional_int(key: str) -> int | None:
        text = values[key].strip()
        return max(1, int(text)) if text else None

    data_start_row = optional_int("data_start_row")
    data_end_row = optional_int("data_end_row")
    if data_start_row and data_end_row and data_end_row < data_start_row:
        raise ValueError("Ostatni wiersz danych nie może być mniejszy od pierwszego.")

    plan_file = values["plan_file"].strip()
    if plan_file and Path(plan_file).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Plik planu musi mieć format XLS, XLSX albo XLSM.")

    result = dict(current)
    result.update(
        {
            "plan_file": plan_file,
            "check_interval_seconds": interval,
            "sheet_name": values["sheet_name"].strip() or None,
            "header_scan_rows": header_scan_rows,
            "data_start_row": data_start_row,
            "data_end_row": data_end_row,
            "department_keywords": [
                item.strip()
                for item in values["department_keywords"].split(",")
                if item.strip()
            ],
            "column_mapping": {
                field: values[field].strip()
                for field in FIELDS
            },
        }
    )
    return result


class EnhancedSettingsDialog(tk.Toplevel):
    """Settings with defaults, examples and background controls in one place."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.parent = parent
        self.monitor = parent.monitor
        self.title("CIDEX — ustawienia")
        self.geometry("900x790")
        self.minsize(820, 700)
        self.configure(bg=BG)
        self.transient(parent)

        config = self.monitor.config
        mapping = config.get("column_mapping", {})
        self.values: dict[str, tk.StringVar] = {
            "plan_file": tk.StringVar(value=config.get("plan_file", "")),
            "wm_root": tk.StringVar(value=get_saved_root()),
            "check_interval_seconds": tk.StringVar(
                value=str(config.get("check_interval_seconds", 60))
            ),
            "department_keywords": tk.StringVar(
                value=", ".join(config.get("department_keywords", []))
            ),
            "sheet_name": tk.StringVar(value=config.get("sheet_name") or ""),
            "header_scan_rows": tk.StringVar(
                value=str(config.get("header_scan_rows", 15))
            ),
            "data_start_row": tk.StringVar(value=str(config.get("data_start_row") or "")),
            "data_end_row": tk.StringVar(value=str(config.get("data_end_row") or "")),
        }
        for field in FIELDS:
            self.values[field] = tk.StringVar(value=mapping.get(field, ""))

        self.tray_var = tk.BooleanVar(value=get_minimize_to_tray())
        self.autostart_var = tk.BooleanVar(value=is_windows_autostart_enabled())

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=BG)
        body.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        window = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window, width=event.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._section_sources(body)
        self._section_monitoring(body)
        self._section_excel(body)
        self._section_columns(body)

        buttons = tk.Frame(body, bg=BG)
        buttons.pack(fill="x", padx=18, pady=(10, 22))
        tk.Button(
            buttons,
            text="Anuluj",
            command=self.destroy,
            bg="#344553",
            fg="white",
            activebackground="#405463",
            activeforeground="white",
            bd=0,
            padx=16,
            pady=8,
        ).pack(side="right", padx=(8, 0))
        tk.Button(
            buttons,
            text="Zapisz ustawienia",
            command=self._save,
            bg=SUCCESS,
            fg="white",
            activebackground=SUCCESS,
            activeforeground="white",
            bd=0,
            padx=18,
            pady=8,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right")

    def _section(self, parent: tk.Widget, title: str, hint: str = "") -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        frame.pack(fill="x", padx=18, pady=(14, 0))
        tk.Label(
            frame,
            text=title,
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        if hint:
            tk.Label(
                frame,
                text=hint,
                bg=PANEL,
                fg=MUTED,
                font=("Segoe UI", 9),
                justify="left",
                wraplength=800,
            ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 8))
        frame.columnconfigure(1, weight=1)
        return frame

    def _entry_row(
        self,
        frame: tk.Frame,
        row: int,
        label: str,
        key: str,
        hint: str = "",
        browse: Any | None = None,
    ) -> None:
        tk.Label(frame, text=label, bg=PANEL, fg=TEXT, anchor="w").grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=5
        )
        entry = tk.Entry(
            frame,
            textvariable=self.values[key],
            bg="#0E171F",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
        )
        entry.grid(row=row, column=1, sticky="ew", pady=5)
        if browse:
            tk.Button(
                frame,
                text="Wybierz…",
                command=browse,
                bg="#344553",
                fg="white",
                activebackground="#405463",
                activeforeground="white",
                bd=0,
                padx=10,
                pady=4,
            ).grid(row=row, column=2, padx=(8, 0), pady=5)
        elif hint:
            tk.Label(
                frame,
                text=hint,
                bg=PANEL,
                fg=MUTED,
                font=("Segoe UI", 8),
            ).grid(row=row, column=2, sticky="w", padx=(8, 0))

    def _section_sources(self, parent: tk.Widget) -> None:
        frame = self._section(
            parent,
            "ŹRÓDŁA DANYCH",
            "Plik Excel i WM_ROOT to dwa niezależne miejsca. CIDEX nie przenosi ani nie łączy tych folderów.",
        )
        self._entry_row(frame, 2, "Plik Excel", "plan_file", browse=self._choose_excel)
        self._entry_row(frame, 3, "WM_ROOT (opcjonalnie)", "wm_root", browse=self._choose_root)
        tk.Label(
            frame,
            text="Excel = monitorowany plan.  WM_ROOT = tylko opcjonalne sprawdzanie, czy produkt istnieje w Warsztat Menager.",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
            justify="left",
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def _section_monitoring(self, parent: tk.Widget) -> None:
        frame = self._section(
            parent,
            "MONITOROWANIE I PRACA W TLE",
            "Domyślny interwał to 60 sekund. X może chować CIDEX do zasobnika zamiast go zamykać.",
        )
        tk.Label(frame, text="Interwał sprawdzania", bg=PANEL, fg=TEXT).grid(
            row=2, column=0, sticky="w", padx=(0, 12), pady=5
        )
        combo = ttk.Combobox(
            frame,
            textvariable=self.values["check_interval_seconds"],
            values=[str(value) for value in INTERVAL_CHOICES],
            state="normal",
            width=14,
        )
        combo.grid(row=2, column=1, sticky="w", pady=5)
        tk.Label(frame, text="sekundy (np. 30, 60, 120, 300)", bg=PANEL, fg=MUTED).grid(
            row=2, column=2, sticky="w", padx=(8, 0)
        )

        tk.Checkbutton(
            frame,
            text="X = schowaj CIDEX do zasobnika zamiast zamykać",
            variable=self.tray_var,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL,
            activeforeground=TEXT,
            selectcolor=BG,
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(7, 2))
        autostart = tk.Checkbutton(
            frame,
            text="Uruchamiaj CIDEX razem z Windows",
            variable=self.autostart_var,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL,
            activeforeground=TEXT,
            selectcolor=BG,
        )
        autostart.grid(row=4, column=0, columnspan=3, sticky="w", pady=2)
        if os.name != "nt":
            autostart.configure(state="disabled")
        tk.Label(
            frame,
            text="Przy autostarcie CIDEX uruchamia się ukryty i pokazuje okno dopiero po wykryciu zmian.",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(3, 0))

    def _section_excel(self, parent: tk.Widget) -> None:
        frame = self._section(
            parent,
            "ODCZYT EXCEL",
            "Większość pól można zostawić z wartościami domyślnymi. Puste pola opcjonalne oznaczają tryb automatyczny.",
        )
        self._entry_row(frame, 2, "Nazwa arkusza", "sheet_name", "puste = aktywny arkusz")
        self._entry_row(frame, 3, "Skan nagłówka", "header_scan_rows", "domyślnie 15 wierszy")
        self._entry_row(frame, 4, "Pierwszy wiersz danych", "data_start_row", "puste = automatycznie")
        self._entry_row(frame, 5, "Ostatni wiersz danych", "data_end_row", "puste = do końca")
        self._entry_row(
            frame,
            6,
            "Słowa kluczowe działu",
            "department_keywords",
            "po przecinku, np. CIĘCIE, MONTAŻ",
        )

    def _section_columns(self, parent: tk.Widget) -> None:
        frame = self._section(
            parent,
            "KOLUMNY PLANU",
            "Zostaw puste, aby CIDEX wykrywał nagłówki automatycznie. Po prawej pokazano domyślne kolumny używane awaryjnie.",
        )
        labels = {
            "order": "Nr zlecenia",
            "symbol": "Symbol / opis",
            "quantity": "Ilość",
            "date": "Data / termin",
            "process": "Proces",
        }
        for index, field in enumerate(FIELDS, start=2):
            self._entry_row(
                frame,
                index,
                labels[field],
                field,
                f"auto / domyślnie {DEFAULT_COLUMN_MAPPING[field]}",
            )

    def _choose_excel(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Wybierz plik planu produkcji",
            filetypes=[
                ("Pliki Excel", "*.xls *.xlsx *.xlsm"),
                ("Excel XLSX", "*.xlsx"),
                ("Excel XLSM", "*.xlsm"),
                ("Excel XLS", "*.xls"),
            ],
        )
        if path:
            self.values["plan_file"].set(path)

    def _choose_root(self) -> None:
        path = filedialog.askdirectory(parent=self, title="Wybierz osobny folder WM_ROOT")
        if path:
            self.values["wm_root"].set(path)

    def _save(self) -> None:
        raw = {key: value.get() for key, value in self.values.items() if key != "wm_root"}
        try:
            config = build_plan_config(self.monitor.config, raw)
            save_config(config, self.monitor.config_path)
            set_saved_root(self.values["wm_root"].get().strip())
            set_minimize_to_tray(bool(self.tray_var.get()))
            if os.name == "nt":
                set_windows_autostart(bool(self.autostart_var.get()))
        except (OSError, ValueError) as exc:
            messagebox.showerror("CIDEX — ustawienia", str(exc), parent=self)
            return

        self.monitor.reload_config()
        self.parent.status_vars["Plik"].set(config["plan_file"] or "—")
        if hasattr(self.parent, "_refresh_wm_root_text"):
            self.parent._refresh_wm_root_text()
        if hasattr(self.parent, "_cidex_tray_var"):
            self.parent._cidex_tray_var.set(bool(self.tray_var.get()))
        if hasattr(self.parent, "_cidex_autostart_var"):
            self.parent._cidex_autostart_var.set(bool(self.autostart_var.get()))
        self.parent._schedule_next()
        self.destroy()


def install_settings_enhancements(app_class: type[Any]) -> None:
    """Replace only the settings dialog entry point."""
    if getattr(app_class, "_cidex_settings_enhancements_installed", False):
        return

    def open_settings(self: Any) -> None:
        EnhancedSettingsDialog(self)

    app_class._open_settings = open_settings
    app_class._cidex_settings_enhancements_installed = True
