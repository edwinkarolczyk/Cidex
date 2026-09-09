import tkinter as tk
from tkinter import ttk

APP_BG = "#0b1118"
SIDEBAR = "#091016"
PANEL = "#111a23"
PANEL_2 = "#16212c"
BORDER = "#263442"
TEXT = "#f3f6f8"
MUTED = "#9ba9b7"
ORANGE = "#ff7a00"
GREEN = "#16a34a"
BLUE = "#1677ff"
RED = "#ef3e2f"
YELLOW = "#f6b73c"
PURPLE = "#8b5cf6"


class CidexApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CIDEX — Planista")
        self.geometry("1600x900")
        self.minsize(1180, 700)
        self.configure(bg=APP_BG)
        self._style()
        self._layout()

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Cidex.Treeview",
            background=PANEL_2,
            fieldbackground=PANEL_2,
            foreground=TEXT,
            rowheight=38,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.map(
            "Cidex.Treeview",
            background=[("selected", "#22384d")],
            foreground=[("selected", TEXT)],
        )
        style.configure(
            "Cidex.Treeview.Heading",
            background=PANEL,
            foreground=TEXT,
            relief="flat",
            font=("Segoe UI Semibold", 10),
            padding=(8, 10),
        )

    def _layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = tk.Frame(self, bg=SIDEBAR, width=190)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        content = tk.Frame(self, bg=APP_BG)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(4, weight=1)

        self._sidebar(sidebar)
        self._header(content)
        self._root_bar(content)
        self._stats(content)
        self._actions(content)
        self._workspace(content)

    def _panel(self, parent):
        return tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

    def _sidebar(self, parent):
        logo = tk.Frame(parent, bg=SIDEBAR)
        logo.pack(fill="x", padx=18, pady=(22, 28))

        tk.Label(
            logo,
            text="⚙  🔧",
            font=("Segoe UI Emoji", 28),
            fg=ORANGE,
            bg=SIDEBAR,
        ).pack(anchor="w")

        name = tk.Frame(logo, bg=SIDEBAR)
        name.pack(anchor="w")
        tk.Label(name, text="CID", font=("Segoe UI Black", 24), fg=TEXT, bg=SIDEBAR).pack(side="left")
        tk.Label(name, text="EX", font=("Segoe UI Black", 24), fg=ORANGE, bg=SIDEBAR).pack(side="left")

        self._nav(parent, "⌂", "Planista", True)
        self._nav(parent, "⚙", "Ustawienia")
        self._nav(parent, "▣", "Instrukcja")
        self._nav(parent, "ⓘ", "O programie")

        tk.Label(
            parent,
            text="PROSTE\nNARZĘDZIA\nREALNE EFEKTY",
            justify="left",
            font=("Segoe UI Semibold", 12),
            fg="#778592",
            bg=SIDEBAR,
        ).pack(side="bottom", anchor="w", padx=20, pady=28)

    def _nav(self, parent, icon, text, active=False):
        bg = "#4b2b12" if active else SIDEBAR
        fg = ORANGE if active else MUTED
        row = tk.Frame(parent, bg=bg, height=58)
        row.pack(fill="x", padx=(0, 10), pady=3)
        row.pack_propagate(False)
        if active:
            tk.Frame(row, bg=ORANGE, width=5).pack(side="left", fill="y")
        tk.Label(row, text=icon, font=("Segoe UI Symbol", 18), fg=fg, bg=bg, width=3).pack(side="left", padx=(8, 0))
        tk.Label(row, text=text, font=("Segoe UI Semibold", 12), fg=fg, bg=bg).pack(side="left")

    def _header(self, parent):
        header = tk.Frame(parent, bg=APP_BG)
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)

        left = tk.Frame(header, bg=APP_BG)
        left.grid(row=0, column=0, sticky="w")

        brand = tk.Frame(left, bg=APP_BG)
        brand.pack(anchor="w")
        tk.Label(brand, text="CID", font=("Segoe UI Black", 28), fg=TEXT, bg=APP_BG).pack(side="left")
        tk.Label(brand, text="EX", font=("Segoe UI Black", 28), fg=ORANGE, bg=APP_BG).pack(side="left")
        tk.Label(
            left,
            text="Planista — zewnętrzny dodatek do WM",
            font=("Segoe UI", 12),
            fg=MUTED,
            bg=APP_BG,
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Planowanie to większe możliwości",
            font=("Segoe Print", 13, "italic"),
            fg="#c7d0d8",
            bg=APP_BG,
        ).grid(row=0, column=1, padx=20)

        right = tk.Frame(header, bg=APP_BG)
        right.grid(row=0, column=2, sticky="e")
        tk.Label(right, text="v0.1 UI", font=("Segoe UI", 9), fg=MUTED, bg=APP_BG).pack(anchor="e")
        tk.Label(right, text="by Edwin K", font=("Segoe UI", 9), fg=MUTED, bg=APP_BG).pack(anchor="e")

    def _root_bar(self, parent):
        box = self._panel(parent)
        box.grid(row=1, column=0, sticky="ew", padx=22, pady=7)
        box.grid_columnconfigure(1, weight=1)

        tk.Label(
            box,
            text="📁  Ścieżka WM_ROOT",
            font=("Segoe UI Semibold", 11),
            fg=TEXT,
            bg=PANEL,
        ).grid(row=0, column=0, padx=16, pady=16, sticky="w")

        fake_path = tk.Label(
            box,
            text=r"D:\WM_ROOT",
            font=("Consolas", 11),
            fg=TEXT,
            bg=PANEL_2,
            anchor="w",
            padx=12,
            pady=9,
        )
        fake_path.grid(row=0, column=1, padx=8, sticky="ew")

        tk.Label(box, text="●", font=("Segoe UI", 18), fg=GREEN, bg=PANEL).grid(row=0, column=2, padx=(18, 6))
        status = tk.Frame(box, bg=PANEL)
        status.grid(row=0, column=3, padx=(0, 18), sticky="w")
        tk.Label(status, text="Połączono z WM", font=("Segoe UI Semibold", 10), fg=TEXT, bg=PANEL).pack(anchor="w")
        tk.Label(status, text="DEMO graficzne", font=("Segoe UI", 9), fg=MUTED, bg=PANEL).pack(anchor="w")

    def _stats(self, parent):
        row = tk.Frame(parent, bg=APP_BG)
        row.grid(row=2, column=0, sticky="ew", padx=22, pady=7)
        for i in range(4):
            row.grid_columnconfigure(i, weight=1, uniform="stats")

        self._stat(row, 0, "▤", "Aktywne zlecenia", "128", "w systemie WM", YELLOW)
        self._stat(row, 1, "↻", "Ostatnia synchronizacja", "DEMO", "wersja graficzna", BLUE)
        self._stat(row, 2, "▣", "Ostatnio dodane", "7", "zleceń dzisiaj", "#d8e1e8")
        self._stat(row, 3, "ⓘ", "Autor zmian", "Cidex", "jeśli pole istnieje w WM", ORANGE)

    def _stat(self, parent, col, icon, title, value, subtitle, accent):
        card = self._panel(parent)
        card.grid(row=0, column=col, sticky="nsew", padx=5)
        tk.Label(card, text=icon, font=("Segoe UI Symbol", 25), fg=accent, bg=PANEL).pack(side="left", padx=(14, 10), pady=18)
        text = tk.Frame(card, bg=PANEL)
        text.pack(side="left", fill="both", expand=True, pady=14)
        tk.Label(text, text=title, font=("Segoe UI Semibold", 10), fg=TEXT, bg=PANEL).pack(anchor="w")
        tk.Label(text, text=value, font=("Segoe UI Black", 18), fg=TEXT, bg=PANEL).pack(anchor="w", pady=(3, 0))
        tk.Label(text, text=subtitle, font=("Segoe UI", 9), fg=MUTED, bg=PANEL).pack(anchor="w")

    def _actions(self, parent):
        row = tk.Frame(parent, bg=APP_BG)
        row.grid(row=3, column=0, sticky="ew", padx=22, pady=7)
        for i in range(4):
            row.grid_columnconfigure(i, weight=1, uniform="actions")

        actions = [
            ("＋", "Dodaj zlecenie", "Wprowadź nowe zlecenie do WM", GREEN),
            ("X", "Import Excel", "Wczytaj plik z danymi zleceń", BLUE),
            ("⚖", "Porównaj z WM", "Sprawdź różnice w danych", ORANGE),
            ("✓", "Zastosuj zmiany", "Dodaj i zaktualizuj zlecenia", RED),
        ]

        for col, (icon, title, subtitle, color) in enumerate(actions):
            card = tk.Frame(row, bg=color)
            card.grid(row=0, column=col, sticky="nsew", padx=5)
            tk.Label(card, text=icon, font=("Segoe UI Symbol", 30, "bold"), fg="white", bg=color, width=3).pack(side="left", padx=(10, 4), pady=16)
            text = tk.Frame(card, bg=color)
            text.pack(side="left", fill="both", expand=True, pady=15)
            tk.Label(text, text=title, font=("Segoe UI Semibold", 14), fg="white", bg=color).pack(anchor="w")
            tk.Label(text, text=subtitle, font=("Segoe UI", 9), fg="#eef5f8", bg=color, wraplength=210, justify="left").pack(anchor="w", pady=(4, 0))

    def _workspace(self, parent):
        area = tk.Frame(parent, bg=APP_BG)
        area.grid(row=4, column=0, sticky="nsew", padx=22, pady=(7, 18))
        area.grid_rowconfigure(0, weight=1)
        area.grid_columnconfigure(0, weight=0, minsize=420)
        area.grid_columnconfigure(1, weight=1)
        self._order_form(area)
        self._diff(area)

    def _section_header(self, parent, title):
        head = tk.Frame(parent, bg=PANEL)
        head.pack(fill="x")
        tk.Frame(head, bg=ORANGE, width=5, height=38).pack(side="left", fill="y")
        tk.Label(head, text=title, font=("Segoe UI Semibold", 13), fg=TEXT, bg=PANEL).pack(side="left", padx=12, pady=10)

    def _order_form(self, parent):
        panel = self._panel(parent)
        panel.grid(row=0, column=0, sticky="nsew", padx=(5, 8))
        self._section_header(panel, "Dodaj nowe zlecenie")

        body = tk.Frame(panel, bg=PANEL)
        body.pack(fill="both", expand=True, padx=16, pady=(6, 16))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        self._field(body, "Nr zlecenia *", "ZP/2026/001", 0, 0, 2)
        self._field(body, "Produkt *", "Wybierz produkt z listy...", 1, 0, 2)
        self._field(body, "Ilość *", "100", 2, 0, 1)
        self._field(body, "Data wysyłki *", "15.09.2026", 2, 1, 1)

        tk.Label(body, text="Uwagi", font=("Segoe UI", 10), fg=TEXT, bg=PANEL).grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 4))
        notes = tk.Label(
            body,
            text="Wpisz uwagi do zlecenia...",
            font=("Segoe UI", 10),
            fg=MUTED,
            bg=PANEL_2,
            anchor="nw",
            justify="left",
            padx=10,
            pady=10,
            height=5,
        )
        notes.grid(row=4, column=0, columnspan=2, sticky="nsew")

        tk.Label(
            body,
            text="➤  Dodaj zlecenie do WM",
            font=("Segoe UI Semibold", 12),
            fg="white",
            bg=ORANGE,
            pady=14,
        ).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(16, 0))

    def _field(self, parent, label, value, row, col, colspan):
        block = tk.Frame(parent, bg=PANEL)
        block.grid(row=row, column=col, columnspan=colspan, sticky="ew", padx=(0, 8 if col == 0 and colspan == 1 else 0), pady=(8, 2))
        block.grid_columnconfigure(0, weight=1)
        tk.Label(block, text=label, font=("Segoe UI", 10), fg=TEXT, bg=PANEL).grid(row=0, column=0, sticky="w", pady=(0, 4))
        tk.Label(
            block,
            text=value,
            font=("Segoe UI", 10),
            fg=MUTED if "Wybierz" in value else TEXT,
            bg=PANEL_2,
            anchor="w",
            padx=10,
            pady=9,
        ).grid(row=1, column=0, sticky="ew")

    def _diff(self, parent):
        panel = self._panel(parent)
        panel.grid(row=0, column=1, sticky="nsew", padx=(8, 5))
        self._section_header(panel, "Podgląd zmian z pliku Excel")

        wrap = tk.Frame(panel, bg=PANEL)
        wrap.pack(fill="both", expand=True, padx=12, pady=(6, 8))
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        columns = ("lp", "nr", "produkt", "excel", "wm", "status", "uwagi")
        tree = ttk.Treeview(wrap, columns=columns, show="headings", style="Cidex.Treeview")
        tree.grid(row=0, column=0, sticky="nsew")

        headings = {
            "lp": "Lp.",
            "nr": "Nr zlecenia",
            "produkt": "Produkt",
            "excel": "Ilość (Excel)",
            "wm": "Ilość (WM)",
            "status": "Status",
            "uwagi": "Uwagi",
        }
        widths = {"lp": 45, "nr": 120, "produkt": 180, "excel": 100, "wm": 90, "status": 150, "uwagi": 210}

        for key in columns:
            tree.heading(key, text=headings[key])
            tree.column(key, width=widths[key], anchor="w", stretch=key in {"produkt", "uwagi"})

        rows = [
            (("1", "ZP/2026/001", "Stół warsztatowy", "100", "—", "Nowe", "Nowe zlecenie z Excel"), "new"),
            (("2", "ZP/2026/002", "Szafka narzędziowa", "50", "40", "Zmiana ilości", "40 → 50"), "changed"),
            (("3", "ZP/2026/003", "Regał metalowy", "20", "20", "Bez zmian", "Brak różnic"), "same"),
            (("4", "ZP/2026/004", "Wózek transportowy", "—", "15", "Usunięte w Excelu", "Tylko informacja"), "removed"),
            (("5", "ZP/2026/005", "Kompresor 50L", "30", "—", "Brak produktu w WM", "Brak dopasowania"), "missing"),
        ]

        for values, tag in rows:
            tree.insert("", "end", values=values, tags=(tag,))

        tree.tag_configure("new", foreground="#67e58a")
        tree.tag_configure("changed", foreground="#ffd166")
        tree.tag_configure("same", foreground="#69b3ff")
        tree.tag_configure("removed", foreground="#ff7b72")
        tree.tag_configure("missing", foreground="#c899ff")

        note = tk.Frame(panel, bg=PANEL_2)
        note.pack(fill="x", padx=12, pady=(2, 12))
        tk.Label(note, text="💡", font=("Segoe UI Emoji", 20), fg=YELLOW, bg=PANEL_2).pack(side="left", padx=(12, 8), pady=10)
        text = tk.Frame(note, bg=PANEL_2)
        text.pack(side="left", fill="both", expand=True, pady=8)
        tk.Label(text, text="Wskazówka", font=("Segoe UI Semibold", 11), fg=YELLOW, bg=PANEL_2).pack(anchor="w")
        tk.Label(
            text,
            text="Na tym etapie to wyłącznie zarys graficzny. Nic nie czyta i nic nie zapisuje w WM.",
            font=("Segoe UI", 9),
            fg=MUTED,
            bg=PANEL_2,
        ).pack(anchor="w")


if __name__ == "__main__":
    CidexApp().mainloop()
