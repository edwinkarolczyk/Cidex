"""CIDEX — porównywanie planu Excel.

W głównym interfejsie celowo dostępny jest wyłącznie mechanizm PlanMonitor
przeniesiony z Warsztat-Menager. Pozostałe moduły CIDEX pozostają w repozytorium,
ale są ukryte z aplikacji głównej.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections import Counter
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from plan_monitor import (
    FIELDS,
    SUPPORTED_EXTENSIONS,
    PlanMonitor,
    display_row,
    export_changes,
    load_history,
    save_config,
    setup_logging,
)

BG = "#0B1118"
PANEL = "#111A23"
PANEL_2 = "#16212C"
TEXT = "#F3F6F8"
MUTED = "#9BA9B7"
ACCENT = "#FF7A00"
SUCCESS = "#16A34A"
BORDER = "#263442"


class CidexExcelApp(tk.Tk):
    """CIDEX shell exposing only the WM-style Excel comparison workflow."""

    def __init__(self) -> None:
        super().__init__()
        self.title("CIDEX — porównanie planu Excel")
        self.geometry("1280x760")
        self.minsize(980, 640)
        self.configure(bg=BG)

        self.monitor = PlanMonitor()
        self.results: queue.Queue[Any] = queue.Queue()
        self.last_changes: list[dict[str, Any]] = []
        self._checking = False
        self._timer: str | None = None

        self._build_styles()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._first_run)
        self.after(200, self._poll_results)

    def _build_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Cidex.Treeview",
            background=PANEL_2,
            foreground=TEXT,
            fieldbackground=PANEL_2,
            rowheight=30,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Cidex.Treeview.Heading",
            background="#1B2733",
            foreground=TEXT,
            relief="flat",
            font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Cidex.Treeview",
            background=[("selected", "#314250")],
            foreground=[("selected", TEXT)],
        )

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=24, pady=(18, 10))
        tk.Label(
            header,
            text="CIDEX",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 24, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="  PORÓWNANIE PLANU EXCEL",
            bg=BG,
            fg=ACCENT,
            font=("Segoe UI", 18, "bold"),
        ).pack(side="left", padx=(8, 0))
        tk.Label(
            header,
            text="mechanizm porównania jak w WM",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(side="right")

        status = tk.Frame(
            self,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        status.pack(fill="x", padx=24)
        status.grid_columnconfigure(1, weight=1)
        self.status_vars = {
            "Plik": tk.StringVar(value="—"),
            "Status": tk.StringVar(value="Oczekiwanie na konfigurację"),
            "Ostatnie sprawdzenie": tk.StringVar(value="—"),
            "Ostatnia zmiana pliku": tk.StringVar(value="—"),
            "Odczytano pozycji": tk.StringVar(value="0"),
            "Przeskanowano wierszy": tk.StringVar(value="0"),
            "Kolumny": tk.StringVar(value="—"),
            "Ostatni błąd": tk.StringVar(value="—"),
        }
        for row, (label, variable) in enumerate(self.status_vars.items()):
            tk.Label(
                status,
                text=f"{label}:",
                width=23,
                anchor="w",
                bg=PANEL,
                fg=MUTED,
                font=("Segoe UI", 10),
            ).grid(row=row, column=0, sticky="w", pady=2)
            tk.Label(
                status,
                textvariable=variable,
                anchor="w",
                bg=PANEL,
                fg=TEXT,
                font=("Segoe UI", 10, "bold"),
            ).grid(row=row, column=1, sticky="ew", pady=2)

        buttons = tk.Frame(self, bg=BG)
        buttons.pack(fill="x", padx=24, pady=12)
        for text, command, color in (
            ("Wybierz Excel", self._choose_plan_file, ACCENT),
            ("Sprawdź teraz", lambda: self._check_async(force=True), ACCENT),
            ("Pokaż zmiany", self._show_latest, "#344553"),
            ("Podgląd pozycji", self._show_preview, "#344553"),
            ("Historia zmian", self._show_history, "#344553"),
            ("Ustawienia", self._open_settings, "#344553"),
            ("Eksportuj raport", self._export, SUCCESS),
        ):
            tk.Button(
                buttons,
                text=text,
                command=command,
                bg=color,
                fg="white",
                activebackground=color,
                activeforeground="white",
                bd=0,
                padx=12,
                pady=8,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
            ).pack(side="left", padx=(0, 7))

        self.summary = tk.StringVar(value="Brak odczytanego raportu")
        tk.Label(
            self,
            textvariable=self.summary,
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 8))

        table_frame = tk.Frame(self, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 18))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = (
            "date",
            "type",
            "order",
            "symbol",
            "old",
            "new",
            "department",
        )
        self.table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Cidex.Treeview",
        )
        headings = (
            "Data",
            "Typ zmiany",
            "Nr zlecenia",
            "Symbol",
            "Stara wartość",
            "Nowa wartość",
            "Dotyczy działu",
        )
        widths = (160, 110, 120, 260, 130, 130, 150)
        for column, heading, width in zip(columns, headings, widths):
            self.table.heading(column, text=heading)
            self.table.column(
                column,
                width=width,
                anchor="w",
                stretch=column == "symbol",
            )
        self.table.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.table.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)

        footer = tk.Frame(self, bg="#101923", padx=12, pady=8)
        footer.pack(fill="x", padx=24, pady=(0, 14))
        tk.Label(
            footer,
            text=(
                "CIDEX pokazuje tylko porównanie planu Excel. "
                "Pozostałe funkcje są ukryte z tego interfejsu."
            ),
            bg="#101923",
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(side="left")
        tk.Label(
            footer,
            text="NOWE • ILOŚĆ • TERMIN • PROCES • USUNIĘTE",
            bg="#101923",
            fg=ACCENT,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right")

    def _first_run(self) -> None:
        plan_file = self.monitor.config.get("plan_file", "")
        if not plan_file:
            self._choose_plan_file(run_check=False)
            plan_file = self.monitor.config.get("plan_file", "")
        if not plan_file:
            self.status_vars["Status"].set("Wybierz plik Excel")
            return
        self.status_vars["Plik"].set(plan_file)
        self.status_vars["Status"].set("Monitorowanie aktywne")
        self._check_async(force=True)
        self._schedule_next()

    def _choose_plan_file(self, run_check: bool = True) -> None:
        plan_file = filedialog.askopenfilename(
            title="Wybierz plik planu produkcji",
            filetypes=[
                ("Pliki Excel", "*.xls *.xlsx *.xlsm"),
                ("Excel XLSX", "*.xlsx"),
                ("Excel XLSM", "*.xlsm"),
                ("Excel XLS", "*.xls"),
            ],
        )
        if not plan_file:
            return
        if Path(plan_file).suffix.lower() not in SUPPORTED_EXTENSIONS:
            messagebox.showerror(
                "CIDEX",
                "Obsługiwane formaty planu: xls, xlsx, xlsm.",
            )
            return
        self.monitor.config["plan_file"] = plan_file
        save_config(self.monitor.config, self.monitor.config_path)
        self.monitor.reload_config()
        self.status_vars["Plik"].set(plan_file)
        self.status_vars["Status"].set("Monitorowanie aktywne")
        self._schedule_next()
        if run_check:
            self._check_async(force=True)

    def _schedule_next(self) -> None:
        if self._timer:
            self.after_cancel(self._timer)
        seconds = max(
            1,
            int(self.monitor.config.get("check_interval_seconds", 60)),
        )
        self._timer = self.after(seconds * 1000, self._scheduled_check)

    def _scheduled_check(self) -> None:
        self._check_async(force=False)
        self._schedule_next()

    def _check_async(self, force: bool) -> None:
        if not self.monitor.config.get("plan_file"):
            self._choose_plan_file(run_check=False)
            if not self.monitor.config.get("plan_file"):
                return
        if self._checking:
            return
        self._checking = True
        self.status_vars["Status"].set("Sprawdzanie planu…")
        threading.Thread(target=self._worker, args=(force,), daemon=True).start()

    def _worker(self, force: bool) -> None:
        self.results.put(self.monitor.check(force=force))

    def _poll_results(self) -> None:
        try:
            while True:
                result = self.results.get_nowait()
                self._handle_result(result)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(200, self._poll_results)

    def _handle_result(self, result: Any) -> None:
        self._checking = False
        self.status_vars["Ostatnie sprawdzenie"].set(result.checked_at)
        if result.file_modified_at:
            self.status_vars["Ostatnia zmiana pliku"].set(result.file_modified_at)
        if result.status == "error":
            self.status_vars["Status"].set("Błąd odczytu pliku")
            self.status_vars["Ostatni błąd"].set(result.error or result.message)
            messagebox.showwarning("CIDEX — Excel", result.message)
            return

        self.status_vars["Status"].set("Monitorowanie aktywne")
        self.status_vars["Ostatni błąd"].set("—")
        parser = result.parser or {}
        mapping = parser.get("column_mapping", {})
        self.status_vars["Odczytano pozycji"].set(
            str(parser.get("records_count", len(result.rows)))
        )
        self.status_vars["Przeskanowano wierszy"].set(
            str(parser.get("rows_scanned", 0))
        )
        self.status_vars["Kolumny"].set(
            "/".join(mapping.get(field, "-") for field in FIELDS)
        )

        if result.changes:
            self.last_changes = result.changes
            self._render(self.last_changes)
        else:
            self.summary.set(result.message)

    def _render(self, changes: list[dict[str, Any]]) -> None:
        self.table.delete(*self.table.get_children())
        for change in changes:
            self.table.insert("", "end", values=display_row(change))
        counts = Counter(change["type"] for change in changes)
        self.summary.set(
            f'Nowe: {counts["new"]}  |  '
            f'Ilość: {counts["quantity_changed"]}  |  '
            f'Terminy: {counts["date_changed"]}  |  '
            f'Proces: {counts["process_changed"]}  |  '
            f'Usunięte: {counts["removed"]}'
        )

    def _show_latest(self) -> None:
        self._render(self.last_changes)

    def _show_history(self) -> None:
        history = load_history(self.monitor.history_path)
        self._render(history)
        if not history:
            self.summary.set("Historia zmian jest pusta.")

    def _show_preview(self) -> None:
        PreviewDialog(
            self,
            self.monitor.last_rows,
            self.monitor.config.get("department_keywords", []),
        )

    def _open_settings(self) -> None:
        SettingsDialog(self, self.monitor)

    def _export(self) -> None:
        if not self.last_changes:
            messagebox.showinfo("CIDEX", "Brak zmian do eksportu.")
            return
        path = filedialog.asksaveasfilename(
            title="Eksportuj raport zmian",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("TXT", "*.txt")],
        )
        if not path:
            return
        try:
            export_changes(self.last_changes, path, self.monitor.last_parser)
        except Exception as exc:
            messagebox.showerror("CIDEX — eksport", str(exc))
            return
        messagebox.showinfo("CIDEX", "Raport został zapisany.")

    def _on_close(self) -> None:
        if self._timer:
            try:
                self.after_cancel(self._timer)
            except tk.TclError:
                pass
        self.destroy()


class PreviewDialog(tk.Toplevel):
    def __init__(
        self,
        parent: CidexExcelApp,
        rows: list[dict[str, Any]],
        keywords: list[str],
    ) -> None:
        super().__init__(parent)
        self.title("CIDEX — podgląd odczytanych pozycji")
        self.geometry("1120x540")
        self.configure(bg=BG)

        columns = (
            "order",
            "symbol",
            "quantity",
            "date",
            "process",
            "department",
        )
        table = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            style="Cidex.Treeview",
        )
        headings = (
            "Nr zlecenia",
            "Symbol / opis",
            "Ilość",
            "Termin",
            "Proces",
            "Dotyczy działu",
        )
        widths = (120, 350, 90, 130, 200, 140)
        for column, heading, width in zip(columns, headings, widths):
            table.heading(column, text=heading)
            table.column(column, width=width, anchor="w")

        for row in rows[:100]:
            haystack = f'{row.get("symbol", "")} {row.get("order", "")}'.upper()
            related = any(
                word.strip().upper() in haystack
                for word in keywords
                if word.strip()
            )
            table.insert(
                "",
                "end",
                values=(
                    row.get("order", ""),
                    row.get("symbol", ""),
                    row.get("quantity"),
                    row.get("date", ""),
                    row.get("process", ""),
                    "TAK" if related else "NIE",
                ),
            )
        table.pack(fill="both", expand=True, padx=12, pady=12)


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: CidexExcelApp, monitor: PlanMonitor) -> None:
        super().__init__(parent)
        self.parent = parent
        self.monitor = monitor
        self.title("CIDEX — ustawienia porównania Excel")
        self.geometry("720x700")
        self.configure(bg=BG)

        config = monitor.config
        mapping = config["column_mapping"]
        self.values = {
            "plan_file": tk.StringVar(value=config.get("plan_file", "")),
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
            "data_start_row": tk.StringVar(
                value=str(config.get("data_start_row") or "")
            ),
            "data_end_row": tk.StringVar(
                value=str(config.get("data_end_row") or "")
            ),
            "order": tk.StringVar(value=mapping.get("order", "")),
            "symbol": tk.StringVar(value=mapping.get("symbol", "")),
            "quantity": tk.StringVar(value=mapping.get("quantity", "")),
            "date": tk.StringVar(value=mapping.get("date", "")),
            "process": tk.StringVar(value=mapping.get("process", "")),
        }

        labels = (
            ("Plik planu", "plan_file"),
            ("Interwał sprawdzania (sekundy)", "check_interval_seconds"),
            ("Słowa kluczowe działu (po przecinku)", "department_keywords"),
            ("Nazwa arkusza (puste = aktywny)", "sheet_name"),
            ("Liczba skanowanych wierszy nagłówka", "header_scan_rows"),
            ("Pierwszy wiersz danych (opcjonalnie)", "data_start_row"),
            ("Ostatni wiersz danych (opcjonalnie)", "data_end_row"),
            ("Kolumna: nr zlecenia", "order"),
            ("Kolumna: symbol / opis", "symbol"),
            ("Kolumna: ilość", "quantity"),
            ("Kolumna: data / termin", "date"),
            ("Kolumna: proces", "process"),
        )

        for row, (label, key) in enumerate(labels):
            tk.Label(self, text=label, bg=BG, fg=TEXT, anchor="w").grid(
                row=row, column=0, sticky="w", padx=16, pady=8
            )
            tk.Entry(
                self,
                textvariable=self.values[key],
                width=44,
                bg=PANEL,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
            ).grid(row=row, column=1, sticky="ew", padx=8, pady=8)

        tk.Button(
            self,
            text="Wybierz plik",
            command=self._select_file,
            bg=ACCENT,
            fg="white",
            bd=0,
            padx=10,
            pady=5,
        ).grid(row=0, column=2, padx=8)

        tk.Button(
            self,
            text="Zapisz",
            command=self._save,
            bg=SUCCESS,
            fg="white",
            bd=0,
            padx=18,
            pady=8,
        ).grid(row=len(labels), column=1, sticky="e", pady=16)

    def _select_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Wybierz plik planu produkcji",
            filetypes=[("Pliki Excel", "*.xls *.xlsx *.xlsm")],
        )
        if path and Path(path).suffix.lower() in SUPPORTED_EXTENSIONS:
            self.values["plan_file"].set(path)

    def _optional_int(self, key: str) -> int | None:
        value = self.values[key].get().strip()
        return max(1, int(value)) if value else None

    def _save(self) -> None:
        try:
            interval = max(1, int(self.values["check_interval_seconds"].get()))
            header_scan_rows = max(1, int(self.values["header_scan_rows"].get()))
            data_start_row = self._optional_int("data_start_row")
            data_end_row = self._optional_int("data_end_row")
        except ValueError:
            messagebox.showerror(
                "CIDEX",
                "Interwał i numery wierszy muszą być liczbami.",
            )
            return

        config = {
            "plan_file": self.values["plan_file"].get().strip(),
            "check_interval_seconds": interval,
            "sheet_name": self.values["sheet_name"].get().strip() or None,
            "header_scan_rows": header_scan_rows,
            "data_start_row": data_start_row,
            "data_end_row": data_end_row,
            "department_keywords": [
                item.strip()
                for item in self.values["department_keywords"].get().split(",")
                if item.strip()
            ],
            "column_mapping": {
                key: self.values[key].get().strip()
                for key in FIELDS
            },
        }
        save_config(config, self.monitor.config_path)
        self.monitor.reload_config()
        self.parent.status_vars["Plik"].set(config["plan_file"] or "—")
        self.parent._schedule_next()
        self.destroy()


def main() -> None:
    setup_logging()
    CidexExcelApp().mainloop()


if __name__ == "__main__":
    main()
