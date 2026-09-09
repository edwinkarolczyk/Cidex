from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from cidex_config import get_saved_root, set_saved_root
from excel_diff import ACTION_CREATE, ACTION_UPDATE, build_diff
from excel_reader import ExcelReadError, read_excel
from sync_service import apply_selected
from wm_store import AUTHOR, add_order, inspect_root, list_orders, list_products

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG = "#0B1118"
SIDE = "#091016"
PANEL = "#111A23"
PANEL2 = "#16212C"
BORDER = "#263442"
TEXT = "#F3F6F8"
MUTED = "#9BA9B7"
ORANGE = "#FF7A00"
GREEN = "#16A34A"
BLUE = "#1677FF"
RED = "#EF3E2F"
YELLOW = "#F6B73C"


class CidexApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CIDEX — Planista")
        self.geometry("1600x900")
        self.minsize(1280, 760)
        self.configure(fg_color=BG)

        self.root_path = tk.StringVar(value=get_saved_root())
        self.status_text = tk.StringVar(value="Wybierz WM_ROOT.")
        self.active_count = tk.StringVar(value="—")
        self.last_refresh = tk.StringVar(value="—")
        self.session_added = tk.StringVar(value="0")
        self.products = []
        self.orders = []
        self.product_lookup = {}
        self.excel_payload = None
        self.diff_plan = None
        self.item_by_iid = {}
        self.selected_ids = set()

        self._style_tree()
        self._build()
        if self.root_path.get():
            self._connect_root(silent=True)

    def _style_tree(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Cidex.Treeview",
            background=PANEL2,
            fieldbackground=PANEL2,
            foreground=TEXT,
            rowheight=38,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.map(
            "Cidex.Treeview",
            background=[("selected", "#22384D")],
            foreground=[("selected", TEXT)],
        )
        style.configure(
            "Cidex.Treeview.Heading",
            background="#1B2733",
            foreground=TEXT,
            relief="flat",
            font=("Segoe UI Semibold", 10),
            padding=(8, 10),
        )

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        side = ctk.CTkFrame(self, width=205, fg_color=SIDE, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(4, weight=1)
        self._sidebar(side)
        self._header(main)
        self._root_bar(main)
        self._stats(main)
        self._actions(main)
        self._workspace(main)
        self._status(main)

    def _sidebar(self, parent):
        ctk.CTkLabel(parent, text="⚙  🔧", text_color=ORANGE, font=("Segoe UI Emoji", 30)).pack(anchor="w", padx=20, pady=(22, 0))
        brand = ctk.CTkFrame(parent, fg_color="transparent")
        brand.pack(anchor="w", padx=20, pady=(0, 26))
        ctk.CTkLabel(brand, text="CID", text_color=TEXT, font=("Segoe UI Black", 25)).pack(side="left")
        ctk.CTkLabel(brand, text="EX", text_color=ORANGE, font=("Segoe UI Black", 25)).pack(side="left")
        for icon, name in [("⌂", "Planista"), ("⚙", "Ustawienia"), ("▣", "Instrukcja"), ("ⓘ", "O programie")]:
            ctk.CTkButton(
                parent,
                text=f"{icon}   {name}",
                height=52,
                corner_radius=16,
                anchor="w",
                fg_color="#4A2B12" if name == "Planista" else "transparent",
                hover_color="#1A2631",
                text_color=ORANGE if name == "Planista" else MUTED,
                border_width=1 if name == "Planista" else 0,
                border_color=ORANGE,
                font=("Segoe UI Semibold", 12),
                command=lambda n=name: self._side_action(n),
            ).pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(parent, text="PROSTE\nNARZĘDZIA\nREALNE EFEKTY", justify="left", text_color="#778592", font=("Segoe UI Semibold", 13)).pack(side="bottom", anchor="w", padx=22, pady=30)

    def _side_action(self, name):
        if name == "Planista":
            self._say("Planista — aktywny moduł Cidex.")
        elif name == "Ustawienia":
            self._choose_root()
        elif name == "Instrukcja":
            messagebox.showinfo(
                "CIDEX — instrukcja",
                "1. Wybierz WM_ROOT.\n2. Dodaj zlecenie ręcznie lub wczytaj Excel.\n"
                "3. Porównaj Excel z WM.\n4. Zaznacz bezpieczne pozycje.\n"
                "5. Zastosuj wybrane.\n\nCidex nie usuwa zleceń automatycznie.",
            )
        else:
            messagebox.showinfo("O programie", "CIDEX\nPlanista — zewnętrzny dodatek do Warsztat Menager\nAutor zapisów: Cidex")

    def _header(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 8))
        row.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        brand = ctk.CTkFrame(left, fg_color="transparent")
        brand.pack(anchor="w")
        ctk.CTkLabel(brand, text="CID", text_color=TEXT, font=("Segoe UI Black", 30)).pack(side="left")
        ctk.CTkLabel(brand, text="EX", text_color=ORANGE, font=("Segoe UI Black", 30)).pack(side="left")
        ctk.CTkLabel(left, text="Planista — zewnętrzny dodatek do WM", text_color=MUTED, font=("Segoe UI", 12)).pack(anchor="w")
        ctk.CTkLabel(row, text="Planowanie to większe możliwości", text_color="#C7D0D8", font=("Segoe Print", 14)).grid(row=0, column=1, padx=20)
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e")
        ctk.CTkLabel(right, text="v1.0 Planista", text_color=MUTED, font=("Segoe UI", 9)).pack(anchor="e")
        ctk.CTkLabel(right, text="by Edwin K", text_color=MUTED, font=("Segoe UI", 9)).pack(anchor="e")

    def _root_bar(self, parent):
        box = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=20, border_width=1, border_color=BORDER, height=76)
        box.grid(row=1, column=0, sticky="ew", padx=24, pady=7)
        box.grid_columnconfigure(1, weight=1)
        box.grid_propagate(False)
        ctk.CTkLabel(box, text="📁  Ścieżka WM_ROOT", text_color=TEXT, font=("Segoe UI Semibold", 11)).grid(row=0, column=0, padx=18)
        entry = ctk.CTkEntry(box, textvariable=self.root_path, height=42, corner_radius=13, fg_color=PANEL2, border_color="#314250", text_color=TEXT, font=("Consolas", 10))
        entry.grid(row=0, column=1, sticky="ew", padx=8)
        entry.bind("<Return>", lambda _event: self._connect_root())
        ctk.CTkButton(box, text="📂  Wybierz", width=115, height=42, corner_radius=13, fg_color="#344553", hover_color="#405463", command=self._choose_root).grid(row=0, column=2, padx=8)
        self.root_state = ctk.CTkLabel(box, text="●  Brak połączenia", justify="left", text_color=RED, font=("Segoe UI Semibold", 9))
        self.root_state.grid(row=0, column=3, padx=(10, 18))

    def _stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=24, pady=7)
        for index in range(4):
            row.grid_columnconfigure(index, weight=1, uniform="stats")
        data = [
            ("▤", "Aktywne zlecenia", self.active_count, "w systemie WM", YELLOW),
            ("↻", "Ostatnie odświeżenie", self.last_refresh, "odczyt z WM_ROOT", BLUE),
            ("▣", "Dodane w sesji", self.session_added, "przez Cidex", TEXT),
            ("ⓘ", "Autor zmian", tk.StringVar(value=AUTHOR), "w historii WM", ORANGE),
        ]
        for col, (icon, title, variable, subtitle, color) in enumerate(data):
            card = ctk.CTkFrame(row, fg_color=PANEL, corner_radius=20, border_width=1, border_color=BORDER, height=98)
            card.grid(row=0, column=col, sticky="nsew", padx=5)
            card.grid_propagate(False)
            ctk.CTkLabel(card, text=icon, text_color=color, font=("Segoe UI Symbol", 27)).pack(side="left", padx=(16, 10))
            text = ctk.CTkFrame(card, fg_color="transparent")
            text.pack(side="left", fill="both", expand=True, pady=10)
            ctk.CTkLabel(text, text=title, text_color=TEXT, font=("Segoe UI Semibold", 10)).pack(anchor="w")
            ctk.CTkLabel(text, textvariable=variable, text_color=TEXT, font=("Segoe UI Black", 18)).pack(anchor="w")
            ctk.CTkLabel(text, text=subtitle, text_color=MUTED, font=("Segoe UI", 8)).pack(anchor="w")

    def _actions(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=3, column=0, sticky="ew", padx=24, pady=7)
        for index in range(4):
            row.grid_columnconfigure(index, weight=1, uniform="actions")
        actions = [
            ("＋", "Dodaj zlecenie", "Przejdź do formularza", GREEN, self._focus_form),
            ("X", "Import Excel", "Wczytaj plik .xlsx", BLUE, self._import_excel),
            ("⚖", "Porównaj z WM", "Sprawdź różnice", ORANGE, self._compare_excel),
            ("✓", "Zastosuj zmiany", "Tylko zaznaczone", RED, self._apply_changes),
        ]
        for col, (icon, title, subtitle, color, command) in enumerate(actions):
            ctk.CTkButton(row, text=f"{icon}   {title}\n      {subtitle}", height=102, corner_radius=22, fg_color=color, hover_color=self._light(color), text_color="white", anchor="w", font=("Segoe UI Semibold", 14), command=command).grid(row=0, column=col, sticky="nsew", padx=5)

    def _workspace(self, parent):
        area = ctk.CTkFrame(parent, fg_color="transparent")
        area.grid(row=4, column=0, sticky="nsew", padx=24, pady=7)
        area.grid_rowconfigure(0, weight=1)
        area.grid_columnconfigure(0, minsize=430)
        area.grid_columnconfigure(1, weight=1)
        self._form(area)
        self._table(area)

    def _title(self, parent, text):
        head = ctk.CTkFrame(parent, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkFrame(head, width=5, height=28, fg_color=ORANGE, corner_radius=3).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(head, text=text, text_color=TEXT, font=("Segoe UI Semibold", 13)).pack(side="left")

    def _form(self, parent):
        card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=22, border_width=1, border_color=BORDER)
        card.grid(row=0, column=0, sticky="nsew", padx=(5, 8))
        self._title(card, "Dodaj nowe zlecenie")
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        self.external_entry = self._entry(body, "Zlecenie wew *", "", 0, 0, 2)
        ctk.CTkLabel(body, text="Produkt *", text_color=TEXT, font=("Segoe UI", 10)).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 4))
        self.product_combo = ctk.CTkComboBox(body, values=[], height=40, corner_radius=12, fg_color=PANEL2, border_color="#314250", button_color="#314250", button_hover_color="#405463", text_color=TEXT, dropdown_fg_color=PANEL2, dropdown_text_color=TEXT)
        self.product_combo.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.product_combo.set("Najpierw wybierz WM_ROOT")
        self.qty_entry = self._entry(body, "Ilość *", "1", 3, 0, 1)
        self.date_entry = self._entry(body, "Data wysyłki", "", 3, 1, 1)
        ctk.CTkLabel(body, text="Uwagi", text_color=TEXT, font=("Segoe UI", 10)).grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 4))
        self.notes = ctk.CTkTextbox(body, height=96, corner_radius=13, fg_color=PANEL2, border_width=1, border_color="#314250", text_color=TEXT)
        self.notes.grid(row=5, column=0, columnspan=2, sticky="nsew")
        ctk.CTkButton(body, text="➤   Dodaj zlecenie do WM", height=58, corner_radius=18, fg_color=ORANGE, hover_color="#FF902A", anchor="w", font=("Segoe UI Semibold", 12), command=self._manual_add).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ctk.CTkLabel(body, text="Nowe zlecenie powstaje bez rezerwacji materiałowych. Cidex nie ingeruje w magazyn WM.", wraplength=390, justify="left", text_color=MUTED, font=("Segoe UI", 8)).grid(row=7, column=0, columnspan=2, sticky="w", pady=(9, 0))

    def _entry(self, parent, label, value, row, col, span):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, columnspan=span, sticky="ew", padx=(0, 8 if span == 1 and col == 0 else 0), pady=(6, 2))
        ctk.CTkLabel(frame, text=label, text_color=TEXT, font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 4))
        entry = ctk.CTkEntry(frame, height=40, corner_radius=12, fg_color=PANEL2, border_width=1, border_color="#314250", text_color=TEXT)
        if value:
            entry.insert(0, value)
        entry.pack(fill="x")
        return entry

    def _table(self, parent):
        card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=22, border_width=1, border_color=BORDER)
        card.grid(row=0, column=1, sticky="nsew", padx=(8, 5))
        self._title(card, "Podgląd Excel ↔ WM")
        toolbar = ctk.CTkFrame(card, fg_color="transparent")
        toolbar.pack(fill="x", padx=12, pady=(2, 6))
        ctk.CTkButton(toolbar, text="✓ Zaznacz bezpieczne", width=150, height=32, corner_radius=11, fg_color=GREEN, hover_color="#20B857", command=self._select_safe).pack(side="left")
        ctk.CTkButton(toolbar, text="× Wyczyść wybór", width=130, height=32, corner_radius=11, fg_color="#344553", hover_color="#405463", command=self._clear_selection).pack(side="left", padx=6)
        self.file_label = ctk.CTkLabel(toolbar, text="Nie wczytano Excela", text_color=MUTED, font=("Segoe UI", 9))
        self.file_label.pack(side="right")
        wrap = ctk.CTkFrame(card, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)
        columns = ("sel", "nr", "produkt", "excel", "wm", "status", "action", "uwagi")
        self.tree = ttk.Treeview(wrap, columns=columns, show="headings", style="Cidex.Treeview")
        self.tree.grid(row=0, column=0, sticky="nsew")
        headings = {"sel": "✓", "nr": "Zlecenie wew", "produkt": "Produkt WM", "excel": "Ilość Excel", "wm": "Ilość WM", "status": "Status", "action": "Akcja", "uwagi": "Uwagi"}
        widths = {"sel": 38, "nr": 110, "produkt": 175, "excel": 85, "wm": 75, "status": 145, "action": 105, "uwagi": 250}
        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], anchor="w", stretch=key in {"produkt", "uwagi"})
        self.tree.bind("<ButtonRelease-1>", self._toggle_row)
        for tag, color in {"new": "#67E58A", "changed": "#FFD166", "same": "#69B3FF", "removed": "#FF7B72", "missing": "#C899FF", "blocked": "#FF9F68"}.items():
            self.tree.tag_configure(tag, foreground=color)
        tip = ctk.CTkFrame(card, fg_color=PANEL2, corner_radius=15, border_width=1, border_color="#314250")
        tip.pack(fill="x", padx=12, pady=(2, 12))
        ctk.CTkLabel(tip, text="💡  Zapis tylko dla zaznaczonych Utwórz/Aktualizuj. „Usunięte w Excelu” nigdy nie kasuje danych.", text_color=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=10)

    def _status(self, parent):
        bar = ctk.CTkFrame(parent, fg_color="#101923", corner_radius=16, border_width=1, border_color="#283746", height=48)
        bar.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 14))
        bar.grid_propagate(False)
        ctk.CTkLabel(bar, text="●", text_color="#34C6F4", font=("Segoe UI", 14)).pack(side="left", padx=(14, 8))
        ctk.CTkLabel(bar, textvariable=self.status_text, text_color="#DBE5EC", font=("Segoe UI", 9)).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(bar, text="AUTOR: CIDEX", text_color=ORANGE, font=("Segoe UI Semibold", 9)).pack(side="right", padx=14)

    def _choose_root(self):
        selected = filedialog.askdirectory(title="Wybierz folder WM_ROOT")
        if selected:
            self.root_path.set(selected)
            self._connect_root()

    def _connect_root(self, silent=False):
        path = self.root_path.get().strip()
        if not path:
            return False
        try:
            inspect_root(path)
            self.products = list_products(path)
            self.orders = list_orders(path)
        except Exception as exc:
            self.root_state.configure(text="●  Błąd ROOT", text_color=RED)
            self._say(str(exc))
            if not silent:
                messagebox.showerror("CIDEX — WM_ROOT", str(exc))
            return False
        set_saved_root(path)
        self.root_state.configure(text="●  Połączono z WM", text_color=GREEN)
        self._refresh_product_combo()
        self._update_stats()
        self._say("WM_ROOT zweryfikowany. Dane odczytane.")
        return True

    def _refresh_data(self):
        if not self._ensure_root():
            return False
        self.products = list_products(self.root_path.get())
        self.orders = list_orders(self.root_path.get())
        self._refresh_product_combo()
        self._update_stats()
        return True

    def _refresh_product_combo(self):
        values = []
        self.product_lookup = {}
        for product in self.products:
            label = f"{product['kod']} — {product['nazwa']}"
            values.append(label)
            self.product_lookup[label] = product["kod"]
        self.product_combo.configure(values=values)
        if values:
            if self.product_combo.get() not in values:
                self.product_combo.set(values[0])
        else:
            self.product_combo.set("Brak produktów WM")

    def _update_stats(self):
        active = [order for order in self.orders if str(order.get("status") or "").casefold() not in {"zakończone", "anulowane", "archiwum"}]
        self.active_count.set(str(len(active)))
        self.last_refresh.set(datetime.now().strftime("%H:%M:%S"))

    def _ensure_root(self):
        if not self.root_path.get().strip():
            messagebox.showwarning("CIDEX", "Najpierw wybierz WM_ROOT.")
            return False
        return self._connect_root(silent=True)

    def _focus_form(self):
        self.external_entry.focus_set()
        self._say("Formularz ręcznego dodawania jest aktywny.")

    def _manual_add(self):
        if not self._ensure_root():
            return
        product_code = self.product_lookup.get(self.product_combo.get())
        if not product_code:
            messagebox.showwarning("CIDEX", "Wybierz produkt WM.")
            return
        try:
            order = add_order(
                self.root_path.get(),
                product_code=product_code,
                quantity=self.qty_entry.get(),
                external_no=self.external_entry.get(),
                due_date=self.date_entry.get(),
                notes=self.notes.get("1.0", "end-1c"),
            )
        except Exception as exc:
            messagebox.showerror("CIDEX — dodawanie", str(exc))
            self._say(str(exc))
            return
        self.session_added.set(str(int(self.session_added.get()) + 1))
        self._refresh_data()
        self._say(f"Dodano zlecenie {order['id']} do WM_ROOT jako autor Cidex.")
        messagebox.showinfo("CIDEX", f"Dodano zlecenie warsztatowe {order['id']}.\nZlecenie wew: {order.get('zlec_wew', '')}\nProdukt: {order.get('produkt')}")

    def _import_excel(self):
        path = filedialog.askopenfilename(title="Wybierz plik Excel", filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        try:
            self.excel_payload = read_excel(path)
        except ExcelReadError as exc:
            messagebox.showerror("CIDEX — Excel", str(exc))
            return
        self.diff_plan = None
        self.selected_ids.clear()
        self.file_label.configure(text=f"{Path(path).name} • {len(self.excel_payload['rows'])} wierszy")
        self._show_raw_excel()
        self._say(f"Wczytano Excel: {len(self.excel_payload['rows'])} pozycji. Kliknij „Porównaj z WM”.")

    def _show_raw_excel(self):
        self._clear_tree()
        self.item_by_iid = {}
        if not self.excel_payload:
            return
        for row in self.excel_payload.get("rows") or []:
            values = ("", row.get("nr_zlec", ""), row.get("produkt_input", ""), row.get("ilosc", ""), "—", "Wczytane", "—", f"Wiersz {row.get('source_row', '')}")
            self.tree.insert("", "end", values=values, tags=("same",))

    def _compare_excel(self):
        if not self.excel_payload:
            messagebox.showwarning("CIDEX", "Najpierw wczytaj plik Excel.")
            return
        if not self._refresh_data():
            return
        self.diff_plan = build_diff(self.excel_payload, self.products, self.orders)
        self.selected_ids = {item["identity"] for item in self.diff_plan["items"] if item.get("selected") and item.get("action") in {ACTION_CREATE, ACTION_UPDATE}}
        self._render_plan()
        self._say(f"Porównanie gotowe: {len(self.diff_plan['items'])} pozycji. Zaznaczono bezpieczne: {len(self.selected_ids)}.")

    def _render_plan(self):
        self._clear_tree()
        self.item_by_iid = {}
        if not self.diff_plan:
            return
        for item in self.diff_plan["items"]:
            identity = item.get("identity") or ""
            selected = identity in self.selected_ids
            qty_excel = item.get("ilosc_excel")
            qty_wm = item.get("ilosc_wm")
            product = item.get("wm_symbol") or item.get("produkt_input")
            if item.get("wm_name"):
                product = f"{product} — {item.get('wm_name')}"
            values = (
                "☑" if selected else "☐",
                item.get("nr_zlec", ""),
                product,
                "—" if qty_excel is None else f"{qty_excel:g}",
                "—" if qty_wm is None else f"{qty_wm:g}",
                item.get("status", ""),
                item.get("action", ""),
                item.get("reason", ""),
            )
            iid = self.tree.insert("", "end", values=values, tags=(self._tag_for(item.get("status", "")),))
            self.item_by_iid[iid] = item

    def _toggle_row(self, event):
        if not self.diff_plan:
            return
        iid = self.tree.identify_row(event.y)
        item = self.item_by_iid.get(iid)
        if not item:
            return
        if item.get("action") not in {ACTION_CREATE, ACTION_UPDATE}:
            self._say("Ta pozycja nie jest bezpieczną automatyczną operacją zapisu.")
            return
        identity = item.get("identity")
        if identity in self.selected_ids:
            self.selected_ids.remove(identity)
        else:
            self.selected_ids.add(identity)
        self._render_plan()

    def _select_safe(self):
        if not self.diff_plan:
            return
        self.selected_ids = {item.get("identity") for item in self.diff_plan["items"] if item.get("identity") and item.get("action") in {ACTION_CREATE, ACTION_UPDATE}}
        self._render_plan()

    def _clear_selection(self):
        self.selected_ids.clear()
        self._render_plan()

    def _apply_changes(self):
        if not self.diff_plan or not self.excel_payload:
            messagebox.showwarning("CIDEX", "Najpierw wykonaj porównanie Excel ↔ WM.")
            return
        if not self.selected_ids:
            messagebox.showwarning("CIDEX", "Nie zaznaczono żadnych zmian.")
            return
        if not self._ensure_root():
            return
        create_count = sum(1 for item in self.diff_plan["items"] if item.get("identity") in self.selected_ids and item.get("action") == ACTION_CREATE)
        update_count = sum(1 for item in self.diff_plan["items"] if item.get("identity") in self.selected_ids and item.get("action") == ACTION_UPDATE)
        if not messagebox.askyesno("CIDEX — potwierdzenie", f"Zastosować zaznaczone zmiany?\n\nUtwórz: {create_count}\nAktualizuj: {update_count}\nUsuń: 0\n\nAutor zapisu: Cidex"):
            return
        results = apply_selected(self.root_path.get(), self.excel_payload, self.diff_plan, self.selected_ids)
        errors = [row for row in results if row.get("status") != "OK"]
        success = [row for row in results if row.get("status") == "OK"]
        self.session_added.set(str(int(self.session_added.get()) + sum(1 for row in success if row.get("action") == ACTION_CREATE)))
        self._refresh_data()
        self._compare_excel()
        if errors:
            details = "\n".join(f"{row.get('identity')}: {row.get('error')}" for row in errors[:8])
            messagebox.showwarning("CIDEX — wynik", f"Zapisano: {len(success)}\nBłędy: {len(errors)}\n\n{details}")
        else:
            messagebox.showinfo("CIDEX — wynik", f"Zapisano poprawnie {len(success)} pozycji.\nNie usunięto żadnych danych.")
        self._say(f"Zastosowano: {len(success)}. Błędy: {len(errors)}. Automatyczne usuwanie: 0.")

    def _clear_tree(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

    def _say(self, text):
        self.status_text.set(str(text))

    @staticmethod
    def _tag_for(status):
        value = str(status or "").casefold()
        if "nowe" in value:
            return "new"
        if "zmiana" in value:
            return "changed"
        if "bez zmian" in value:
            return "same"
        if "usunięte" in value:
            return "removed"
        if "brak produktu" in value or "niejednoznaczny" in value:
            return "missing"
        if "chronione" in value or "rezerwacje" in value or "duplikat" in value:
            return "blocked"
        return "same"

    @staticmethod
    def _light(color):
        value = color.lstrip("#")
        rgb = [int(value[index:index + 2], 16) for index in (0, 2, 4)]
        out = [min(255, int(channel + (255 - channel) * 0.13)) for channel in rgb]
        return "#" + "".join(f"{channel:02X}" for channel in out)


def main():
    CidexApp().mainloop()


if __name__ == "__main__":
    main()
