"""CIDEX launcher: Excel auto-monitor + WM read-only check + updater."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections import Counter
from tkinter import filedialog, messagebox, ttk
from typing import Any

from cidex_config import get_saved_root, set_saved_root
from main import ACCENT, BG, MUTED, PANEL, TEXT, CidexExcelApp
from plan_monitor import FIELDS, display_row, setup_logging
from updater import CidexUpdater, ReleaseInfo
from version import APP_VERSION
from wm_compare import enrich_changes_with_wm

GREEN = "#67E58A"
YELLOW = "#FFD166"
RED = "#FF7B72"
BLUE = "#1677FF"


class EnhancedCidexApp(CidexExcelApp):
    """Keep the simple CIDEX UI and add only requested monitoring features."""

    def __init__(self) -> None:
        self.update_results: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._update_checking = False
        super().__init__()
        self.title(f"CIDEX {APP_VERSION} — monitor planu Excel")
        self.after(900, self._check_updates_async)

    def _build_ui(self) -> None:
        super()._build_ui()
        self.table.heading("department", text="WM / dział")
        self.table.tag_configure("wm_missing", foreground=GREEN)
        self.table.tag_configure("wm_exists", foreground=YELLOW)
        self.table.tag_configure("wm_unknown", foreground=MUTED)
        self.table.tag_configure("removed", foreground=RED)

        bar = tk.Frame(
            self,
            bg=PANEL,
            highlightbackground="#263442",
            highlightthickness=1,
            padx=12,
            pady=8,
        )
        bar.pack(fill="x", padx=24, pady=(0, 14))

        self.wm_root_text = tk.StringVar()
        self._refresh_wm_root_text()
        tk.Label(
            bar,
            textvariable=self.wm_root_text,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(side="left")
        tk.Button(
            bar,
            text="WM_ROOT",
            command=self._choose_wm_root,
            bg="#344553",
            fg="white",
            activebackground="#405463",
            activeforeground="white",
            bd=0,
            padx=10,
            pady=5,
        ).pack(side="left", padx=8)

        tk.Label(
            bar,
            text="BRAK W WM = zielony • ISTNIEJE W WM = żółty",
            bg=PANEL,
            fg=ACCENT,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=12)

        self.version_text = tk.StringVar(value=f"CIDEX {APP_VERSION}")
        tk.Button(
            bar,
            textvariable=self.version_text,
            command=self._open_updates,
            bg=BLUE,
            fg="white",
            activebackground=BLUE,
            activeforeground="white",
            bd=0,
            padx=12,
            pady=5,
        ).pack(side="right")

    def _refresh_wm_root_text(self) -> None:
        root = get_saved_root()
        self.wm_root_text.set(
            f"WM_ROOT: {root}"
            if root
            else "WM_ROOT: nie ustawiono — produkty nie będą sprawdzane"
        )

    def _choose_wm_root(self) -> None:
        selected = filedialog.askdirectory(title="Wybierz WM_ROOT do odczytu produktów")
        if not selected:
            return
        set_saved_root(selected)
        self._refresh_wm_root_text()
        if self.last_changes:
            self.last_changes = enrich_changes_with_wm(self.last_changes, selected)
            self._render(self.last_changes)

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

        if result.status == "unchanged":
            self.status_vars["Status"].set("Monitorowanie aktywne — bez zmian")
        else:
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
            changes = enrich_changes_with_wm(result.changes, get_saved_root())
            self.last_changes = changes
            self._render(changes)
            ChangesDialog(self, changes)
            self.bell()
        elif result.status != "unchanged":
            self.summary.set(result.message)

    def _render(self, changes: list[dict[str, Any]]) -> None:
        self.table.delete(*self.table.get_children())
        for change in changes:
            values = list(display_row(change))
            wm_label = change.get("wm_label", "NIE SPRAWDZONO")
            department = values[6] if len(values) > 6 else "NIE"
            values[6] = f"{wm_label} • dział {department}"
            state = change.get("wm_state")
            if change.get("type") == "removed":
                tag = "removed"
            elif state == "missing":
                tag = "wm_missing"
            elif state == "exists":
                tag = "wm_exists"
            else:
                tag = "wm_unknown"
            self.table.insert("", "end", values=values, tags=(tag,))

        counts = Counter(change["type"] for change in changes)
        missing = sum(change.get("wm_state") == "missing" for change in changes)
        exists = sum(change.get("wm_state") == "exists" for change in changes)
        self.summary.set(
            f'Nowe: {counts["new"]} | Ilość: {counts["quantity_changed"]} | '
            f'Terminy: {counts["date_changed"]} | Proces: {counts["process_changed"]} | '
            f'Usunięte: {counts["removed"]} | Brak w WM: {missing} | W WM: {exists}'
        )

    def _poll_results(self) -> None:
        try:
            while True:
                result = self.results.get_nowait()
                self._handle_result(result)
        except queue.Empty:
            pass

        try:
            while True:
                kind, payload = self.update_results.get_nowait()
                self._handle_update_result(kind, payload)
        except queue.Empty:
            pass

        if self.winfo_exists():
            self.after(200, self._poll_results)

    def _check_updates_async(self) -> None:
        if self._update_checking:
            return
        self._update_checking = True
        self.version_text.set(f"CIDEX {APP_VERSION} • sprawdzam…")
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self) -> None:
        try:
            self.update_results.put(("latest", CidexUpdater.latest()))
        except Exception as exc:
            self.update_results.put(("error", exc))

    def _handle_update_result(self, kind: str, payload: Any) -> None:
        self._update_checking = False
        self.version_text.set(f"CIDEX {APP_VERSION}")
        if kind == "error":
            return
        info: ReleaseInfo | None = payload
        if info and CidexUpdater.is_newer(info):
            self.version_text.set(f"CIDEX {APP_VERSION} → {info.version}")
            if messagebox.askyesno(
                "CIDEX — dostępna aktualizacja",
                f"Masz CIDEX {APP_VERSION}.\nDostępna jest wersja {info.version}.\n\n"
                "Pobrać i zainstalować aktualizację?",
            ):
                UpdateDialog(self, info)

    def _open_updates(self) -> None:
        UpdateDialog(self, None)


class ChangesDialog(tk.Toplevel):
    """Popup displayed only after PlanMonitor reports actual differences."""

    def __init__(self, parent: EnhancedCidexApp, changes: list[dict[str, Any]]) -> None:
        super().__init__(parent)
        self.title("CIDEX — wykryto zmiany w Excelu")
        self.geometry("1160x540")
        self.minsize(900, 420)
        self.configure(bg=BG)
        self.transient(parent)
        self.lift()

        tk.Label(
            self,
            text="WYKRYTO ZMIANY W PLANIE EXCEL",
            bg=BG,
            fg=ACCENT,
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w", padx=18, pady=(16, 6))
        tk.Label(
            self,
            text=(
                "Zielony = produktu nie ma w WM. Żółty = produkt istnieje w WM. "
                "Czerwony = pozycję usunięto z Excela."
            ),
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=18, pady=(0, 10))

        columns = ("type", "order", "symbol", "old", "new", "wm")
        table = ttk.Treeview(
            self, columns=columns, show="headings", style="Cidex.Treeview"
        )
        headings = (
            "Typ", "Nr zlecenia", "Produkt / symbol",
            "Stara wartość", "Nowa wartość", "WM",
        )
        widths = (110, 120, 330, 160, 160, 160)
        for column, heading, width in zip(columns, headings, widths):
            table.heading(column, text=heading)
            table.column(column, width=width, anchor="w", stretch=column == "symbol")
        table.tag_configure("wm_missing", foreground=GREEN)
        table.tag_configure("wm_exists", foreground=YELLOW)
        table.tag_configure("wm_unknown", foreground=MUTED)
        table.tag_configure("removed", foreground=RED)

        for change in changes:
            state = change.get("wm_state")
            if change.get("type") == "removed":
                tag = "removed"
            elif state == "missing":
                tag = "wm_missing"
            elif state == "exists":
                tag = "wm_exists"
            else:
                tag = "wm_unknown"
            table.insert(
                "",
                "end",
                values=(
                    change.get("type_label", change.get("type", "")),
                    change.get("order", ""),
                    change.get("symbol", ""),
                    change.get("old", ""),
                    change.get("new", ""),
                    change.get("wm_label", "NIE SPRAWDZONO"),
                ),
                tags=(tag,),
            )
        table.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        tk.Button(
            self,
            text="Zamknij",
            command=self.destroy,
            bg="#344553",
            fg="white",
            bd=0,
            padx=20,
            pady=8,
        ).pack(anchor="e", padx=18, pady=(0, 16))


class UpdateDialog(tk.Toplevel):
    def __init__(self, parent: EnhancedCidexApp, info: ReleaseInfo | None) -> None:
        super().__init__(parent)
        self.parent = parent
        self.info = info
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.title("CIDEX — aktualizacje")
        self.geometry("540x330")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.transient(parent)

        self.status = tk.StringVar(value=f"Aktualna wersja: CIDEX {APP_VERSION}")
        tk.Label(
            self,
            text="AKTUALIZACJE CIDEX",
            bg=BG,
            fg=ACCENT,
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 8))
        tk.Label(
            self,
            textvariable=self.status,
            bg=BG,
            fg=TEXT,
            justify="left",
            anchor="w",
            font=("Segoe UI", 11),
        ).pack(fill="x", padx=20, pady=(0, 14))

        self.progress = ttk.Progressbar(self, maximum=100, mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=8)

        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=20, pady=16)
        self.check_button = tk.Button(
            row,
            text="Sprawdź ponownie",
            command=self._check,
            bg="#344553",
            fg="white",
            bd=0,
            padx=12,
            pady=8,
        )
        self.check_button.pack(side="left")
        self.install_button = tk.Button(
            row,
            text="Pobierz i zainstaluj",
            command=self._install,
            bg="#16A34A",
            fg="white",
            bd=0,
            padx=12,
            pady=8,
            state="disabled",
        )
        self.install_button.pack(side="right")

        self.after(150, self._poll)
        if info is None:
            self._check()
        else:
            self._show_info(info)

    def _check(self) -> None:
        self.check_button.configure(state="disabled")
        self.install_button.configure(state="disabled")
        self.status.set(f"CIDEX {APP_VERSION}\nSprawdzanie GitHub Releases…")
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self) -> None:
        try:
            self.events.put(("info", CidexUpdater.latest()))
        except Exception as exc:
            self.events.put(("error", exc))

    def _show_info(self, info: ReleaseInfo | None) -> None:
        self.info = info
        self.check_button.configure(state="normal")
        if info is None:
            self.status.set(
                f"CIDEX {APP_VERSION}\nBrak opublikowanej wersji aktualizacyjnej."
            )
            self.install_button.configure(state="disabled")
        elif CidexUpdater.is_newer(info):
            self.status.set(
                f"CIDEX {APP_VERSION}\nDostępna aktualizacja: CIDEX {info.version}"
            )
            self.install_button.configure(state="normal")
        else:
            self.status.set(f"CIDEX {APP_VERSION}\nMasz najnowszą wersję.")
            self.install_button.configure(state="disabled")

    def _install(self) -> None:
        if self.info is None:
            return
        self.check_button.configure(state="disabled")
        self.install_button.configure(state="disabled")
        self.status.set(f"Pobieranie CIDEX {self.info.version}…")
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self) -> None:
        assert self.info is not None
        try:
            path = CidexUpdater.download(
                self.info,
                lambda value: self.events.put(("progress", value)),
            )
            CidexUpdater.launch_replace(path)
            self.events.put(("installed", None))
        except Exception as exc:
            self.events.put(("error", exc))

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    self.progress["value"] = float(payload) * 100
                elif kind == "info":
                    self._show_info(payload)
                elif kind == "error":
                    self.check_button.configure(state="normal")
                    self.status.set(f"Błąd aktualizacji:\n{payload}")
                elif kind == "installed":
                    self.status.set("Aktualizacja pobrana. Uruchamiam nową wersję…")
                    self.parent.after(300, self.parent.destroy)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(150, self._poll)


def main() -> None:
    setup_logging()
    EnhancedCidexApp().mainloop()


if __name__ == "__main__":
    main()
