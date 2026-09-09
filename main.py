import tkinter as tk
from tkinter import ttk
from datetime import datetime
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG = "#0B1118"; SIDE = "#091016"; PANEL = "#111A23"; PANEL2 = "#16212C"
BORDER = "#263442"; TEXT = "#F3F6F8"; MUTED = "#9BA9B7"
ORANGE = "#FF7A00"; GREEN = "#16A34A"; BLUE = "#1677FF"; RED = "#EF3E2F"; YELLOW = "#F6B73C"


class CidexDemo(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CIDEX — UI-DEMO 1")
        self.geometry("1600x900")
        self.minsize(1240, 760)
        self.configure(fg_color=BG)
        self.status = tk.StringVar(value="UI-DEMO 1 — nic nie czyta ani nie zapisuje danych WM.")
        self.active = tk.StringVar(value="128")
        self.sync = tk.StringVar(value="DEMO")
        self.added = tk.StringVar(value="7")
        self.nav = {}
        self._style_tree()
        self._build()

    def _style_tree(self):
        s = ttk.Style(self); s.theme_use("clam")
        s.configure("Cidex.Treeview", background=PANEL2, fieldbackground=PANEL2, foreground=TEXT,
                    rowheight=38, borderwidth=0, font=("Segoe UI", 10))
        s.map("Cidex.Treeview", background=[("selected", "#22384D")], foreground=[("selected", TEXT)])
        s.configure("Cidex.Treeview.Heading", background="#1B2733", foreground=TEXT,
                    relief="flat", font=("Segoe UI Semibold", 10), padding=(8, 10))

    def _build(self):
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        side = ctk.CTkFrame(self, width=205, fg_color=SIDE, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew"); side.grid_propagate(False)
        main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew"); main.grid_columnconfigure(0, weight=1); main.grid_rowconfigure(4, weight=1)
        self._sidebar(side); self._header(main); self._root(main); self._stats(main); self._actions(main); self._workspace(main); self._status(main)

    def _sidebar(self, p):
        ctk.CTkLabel(p, text="⚙  🔧", text_color=ORANGE, font=("Segoe UI Emoji", 30)).pack(anchor="w", padx=20, pady=(22, 0))
        brand = ctk.CTkFrame(p, fg_color="transparent"); brand.pack(anchor="w", padx=20, pady=(0, 26))
        ctk.CTkLabel(brand, text="CID", text_color=TEXT, font=("Segoe UI Black", 25)).pack(side="left")
        ctk.CTkLabel(brand, text="EX", text_color=ORANGE, font=("Segoe UI Black", 25)).pack(side="left")
        for icon, name in [("⌂", "Planista"), ("⚙", "Ustawienia"), ("▣", "Instrukcja"), ("ⓘ", "O programie")]:
            active = name == "Planista"
            b = ctk.CTkButton(p, text=f"{icon}   {name}", height=52, corner_radius=16, anchor="w",
                              fg_color="#4A2B12" if active else "transparent", hover_color="#1A2631",
                              text_color=ORANGE if active else MUTED, border_width=1 if active else 0,
                              border_color=ORANGE, font=("Segoe UI Semibold", 12), command=lambda n=name: self._nav(n))
            b.pack(fill="x", padx=10, pady=4); self.nav[name] = b
        ctk.CTkLabel(p, text="PROSTE\nNARZĘDZIA\nREALNE EFEKTY", justify="left", text_color="#778592",
                     font=("Segoe UI Semibold", 13)).pack(side="bottom", anchor="w", padx=22, pady=30)

    def _nav(self, name):
        for key, b in self.nav.items():
            on = key == name
            b.configure(fg_color="#4A2B12" if on else "transparent", text_color=ORANGE if on else MUTED,
                        border_width=1 if on else 0)
        self._say("Planista — aktywny ekran DEMO." if name == "Planista" else f"{name} — tylko podświetlenie DEMO.")

    def _header(self, p):
        r = ctk.CTkFrame(p, fg_color="transparent"); r.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 8)); r.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(r, fg_color="transparent"); left.grid(row=0, column=0, sticky="w")
        brand = ctk.CTkFrame(left, fg_color="transparent"); brand.pack(anchor="w")
        ctk.CTkLabel(brand, text="CID", text_color=TEXT, font=("Segoe UI Black", 30)).pack(side="left")
        ctk.CTkLabel(brand, text="EX", text_color=ORANGE, font=("Segoe UI Black", 30)).pack(side="left")
        ctk.CTkLabel(left, text="Planista — zewnętrzny dodatek do WM", text_color=MUTED, font=("Segoe UI", 12)).pack(anchor="w")
        ctk.CTkLabel(r, text="Planowanie to większe możliwości", text_color="#C7D0D8", font=("Segoe Print", 14)).grid(row=0, column=1, padx=20)
        right = ctk.CTkFrame(r, fg_color="transparent"); right.grid(row=0, column=2, sticky="e")
        ctk.CTkLabel(right, text="v0.2 UI-DEMO 1", text_color=MUTED, font=("Segoe UI", 9)).pack(anchor="e")
        ctk.CTkLabel(right, text="by Edwin K", text_color=MUTED, font=("Segoe UI", 9)).pack(anchor="e")

    def _root(self, p):
        b = ctk.CTkFrame(p, fg_color=PANEL, corner_radius=20, border_width=1, border_color=BORDER, height=76)
        b.grid(row=1, column=0, sticky="ew", padx=24, pady=7); b.grid_columnconfigure(1, weight=1); b.grid_propagate(False)
        ctk.CTkLabel(b, text="📁  Ścieżka WM_ROOT", text_color=TEXT, font=("Segoe UI Semibold", 11)).grid(row=0, column=0, padx=18)
        e = ctk.CTkEntry(b, height=42, corner_radius=13, fg_color=PANEL2, border_color="#314250", text_color=TEXT, font=("Consolas", 10))
        e.insert(0, r"D:\WM_ROOT  (DEMO)"); e.configure(state="disabled"); e.grid(row=0, column=1, sticky="ew", padx=8)
        ctk.CTkButton(b, text="▣  DEMO", width=110, height=42, corner_radius=13, fg_color="#344553", hover_color="#405463",
                      command=lambda: self._say("WM_ROOT: przycisk jest tylko DEMO — niczego nie otwieram.")).grid(row=0, column=2, padx=8)
        ctk.CTkLabel(b, text="●  Połączono z WM\n    status wizualny DEMO", justify="left", text_color=GREEN,
                     font=("Segoe UI Semibold", 9)).grid(row=0, column=3, padx=(10, 18))

    def _stats(self, p):
        r = ctk.CTkFrame(p, fg_color="transparent"); r.grid(row=2, column=0, sticky="ew", padx=24, pady=7)
        for i in range(4): r.grid_columnconfigure(i, weight=1, uniform="s")
        data = [("▤", "Aktywne zlecenia", self.active, "w systemie WM — DEMO", YELLOW),
                ("↻", "Ostatnia synchronizacja", self.sync, "wersja graficzna", BLUE),
                ("▣", "Ostatnio dodane", self.added, "zleceń dzisiaj — DEMO", TEXT),
                ("ⓘ", "Autor zmian", tk.StringVar(value="Cidex"), "jeśli pole istnieje w WM", ORANGE)]
        for i, (icon, title, var, sub, color) in enumerate(data):
            c = ctk.CTkFrame(r, fg_color=PANEL, corner_radius=20, border_width=1, border_color=BORDER, height=98)
            c.grid(row=0, column=i, sticky="nsew", padx=5); c.grid_propagate(False)
            ctk.CTkLabel(c, text=icon, text_color=color, font=("Segoe UI Symbol", 27)).pack(side="left", padx=(16, 10))
            t = ctk.CTkFrame(c, fg_color="transparent"); t.pack(side="left", fill="both", expand=True, pady=10)
            ctk.CTkLabel(t, text=title, text_color=TEXT, font=("Segoe UI Semibold", 10)).pack(anchor="w")
            ctk.CTkLabel(t, textvariable=var, text_color=TEXT, font=("Segoe UI Black", 18)).pack(anchor="w")
            ctk.CTkLabel(t, text=sub, text_color=MUTED, font=("Segoe UI", 8)).pack(anchor="w")

    def _actions(self, p):
        r = ctk.CTkFrame(p, fg_color="transparent"); r.grid(row=3, column=0, sticky="ew", padx=24, pady=7)
        for i in range(4): r.grid_columnconfigure(i, weight=1, uniform="a")
        data = [("＋", "Dodaj zlecenie", "Przejdź do formularza DEMO", GREEN, self._focus),
                ("X", "Import Excel", "Załaduj 5 pozycji DEMO", BLUE, self._import),
                ("⚖", "Porównaj z WM", "Pokaż różnice DEMO", ORANGE, self._compare),
                ("✓", "Zastosuj zmiany", "Symulacja zatwierdzenia", RED, self._apply)]
        for i, (icon, title, sub, color, cmd) in enumerate(data):
            ctk.CTkButton(r, text=f"{icon}   {title}\n      {sub}", height=102, corner_radius=22, fg_color=color,
                          hover_color=self._light(color), text_color="white", anchor="w",
                          font=("Segoe UI Semibold", 14), command=cmd).grid(row=0, column=i, sticky="nsew", padx=5)

    def _workspace(self, p):
        a = ctk.CTkFrame(p, fg_color="transparent"); a.grid(row=4, column=0, sticky="nsew", padx=24, pady=7)
        a.grid_rowconfigure(0, weight=1); a.grid_columnconfigure(0, minsize=430); a.grid_columnconfigure(1, weight=1)
        self._form(a); self._table(a)

    def _title(self, p, text):
        h = ctk.CTkFrame(p, fg_color="transparent"); h.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkFrame(h, width=5, height=28, fg_color=ORANGE, corner_radius=3).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(h, text=text, text_color=TEXT, font=("Segoe UI Semibold", 13)).pack(side="left")

    def _form(self, p):
        c = ctk.CTkFrame(p, fg_color=PANEL, corner_radius=22, border_width=1, border_color=BORDER)
        c.grid(row=0, column=0, sticky="nsew", padx=(5, 8)); self._title(c, "Dodaj nowe zlecenie")
        b = ctk.CTkFrame(c, fg_color="transparent"); b.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        b.grid_columnconfigure(0, weight=1); b.grid_columnconfigure(1, weight=1)
        self.no = self._entry(b, "Nr zlecenia *", "ZP/2026/001", 0, 0, 2)
        self.product = self._entry(b, "Produkt *", "Stół warsztatowy", 1, 0, 2)
        self.qty = self._entry(b, "Ilość *", "100", 2, 0, 1)
        self.date = self._entry(b, "Data wysyłki *", "15.09.2026", 2, 1, 1)
        ctk.CTkLabel(b, text="Uwagi", text_color=TEXT, font=("Segoe UI", 10)).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 4))
        self.notes = ctk.CTkTextbox(b, height=86, corner_radius=13, fg_color=PANEL2, border_width=1, border_color="#314250", text_color=TEXT)
        self.notes.grid(row=4, column=0, columnspan=2, sticky="nsew"); self.notes.insert("1.0", "UI-DEMO 1 — przykładowa uwaga.")
        ctk.CTkButton(b, text="➤   Dodaj zlecenie do WM\n     DEMO — tylko do tabeli na ekranie", height=70, corner_radius=18,
                      fg_color=ORANGE, hover_color="#FF902A", anchor="w", font=("Segoe UI Semibold", 12),
                      command=self._add).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(14, 0))

    def _entry(self, p, label, value, row, col, span):
        w = ctk.CTkFrame(p, fg_color="transparent"); w.grid(row=row, column=col, columnspan=span, sticky="ew", padx=(0, 8 if span == 1 and col == 0 else 0), pady=(6, 2))
        ctk.CTkLabel(w, text=label, text_color=TEXT, font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 4))
        e = ctk.CTkEntry(w, height=40, corner_radius=12, fg_color=PANEL2, border_width=1, border_color="#314250", text_color=TEXT)
        e.insert(0, value); e.pack(fill="x"); return e

    def _table(self, p):
        c = ctk.CTkFrame(p, fg_color=PANEL, corner_radius=22, border_width=1, border_color=BORDER)
        c.grid(row=0, column=1, sticky="nsew", padx=(8, 5)); self._title(c, "Podgląd zmian z pliku Excel")
        h = ctk.CTkFrame(c, fg_color="transparent"); h.pack(fill="both", expand=True, padx=12, pady=(4, 8)); h.grid_rowconfigure(0, weight=1); h.grid_columnconfigure(0, weight=1)
        cols = ("lp", "nr", "produkt", "excel", "wm", "status", "uwagi"); self.tree = ttk.Treeview(h, columns=cols, show="headings", style="Cidex.Treeview"); self.tree.grid(row=0, column=0, sticky="nsew")
        names = ["Lp.", "Nr zlecenia", "Produkt", "Ilość (Excel)", "Ilość (WM)", "Status", "Uwagi"]
        widths = [45, 120, 175, 95, 90, 145, 210]
        for k, n, w in zip(cols, names, widths): self.tree.heading(k, text=n); self.tree.column(k, width=w, anchor="w", stretch=k in {"produkt", "uwagi"})
        for tag, color in {"new":"#67E58A", "changed":"#FFD166", "same":"#69B3FF", "removed":"#FF7B72", "missing":"#C899FF", "loaded":"#D8E1E8"}.items(): self.tree.tag_configure(tag, foreground=color)
        self._preview()
        tip = ctk.CTkFrame(c, fg_color=PANEL2, corner_radius=15, border_width=1, border_color="#314250"); tip.pack(fill="x", padx=12, pady=(2, 12))
        ctk.CTkLabel(tip, text="💡  Wskazówka: klikaj kolorowe kafle. To tylko UI-DEMO 1 — bez odczytu i zapisu WM.", text_color=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=10)

    def _status(self, p):
        b = ctk.CTkFrame(p, fg_color="#101923", corner_radius=16, border_width=1, border_color="#283746", height=48)
        b.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 14)); b.grid_propagate(False)
        ctk.CTkLabel(b, text="●", text_color="#34C6F4", font=("Segoe UI", 14)).pack(side="left", padx=(14, 8))
        ctk.CTkLabel(b, textvariable=self.status, text_color="#DBE5EC", font=("Segoe UI", 9)).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(b, text="BEZ ZAPISU DO WM", text_color=ORANGE, font=("Segoe UI Semibold", 9)).pack(side="right", padx=14)

    def _preview(self):
        self._clear(); rows = [("1","ZP/2026/001","Stół warsztatowy","100","—","DEMO","Kliknij Import Excel"), ("2","ZP/2026/002","Szafka narzędziowa","50","40","DEMO","Kliknij Porównaj z WM"), ("3","ZP/2026/003","Regał metalowy","20","20","DEMO","Dane pokazowe")]
        for x in rows: self.tree.insert("", "end", values=x, tags=("loaded",))

    def _import(self):
        self._clear(); rows = [("1","ZP/2026/001","Stół warsztatowy","100","—","Wczytane","Pozycja DEMO"), ("2","ZP/2026/002","Szafka narzędziowa","50","40","Wczytane","Pozycja DEMO"), ("3","ZP/2026/003","Regał metalowy","20","20","Wczytane","Pozycja DEMO"), ("4","ZP/2026/004","Wózek transportowy","—","15","Wczytane","Pozycja DEMO"), ("5","ZP/2026/005","Kompresor 50L","30","—","Wczytane","Pozycja DEMO")]
        for x in rows: self.tree.insert("", "end", values=x, tags=("loaded",))
        self._say("Import Excel DEMO: wczytano 5 pozycji. Żaden plik nie został otwarty.")

    def _compare(self):
        self._clear(); rows = [(("1","ZP/2026/001","Stół warsztatowy","100","—","Nowe","Nowe zlecenie z Excel"),"new"), (("2","ZP/2026/002","Szafka narzędziowa","50","40","Zmiana ilości","40 → 50"),"changed"), (("3","ZP/2026/003","Regał metalowy","20","20","Bez zmian","Brak różnic"),"same"), (("4","ZP/2026/004","Wózek transportowy","—","15","Usunięte w Excelu","Tylko informacja"),"removed"), (("5","ZP/2026/005","Kompresor 50L","30","—","Brak produktu w WM","Brak dopasowania"),"missing")]
        for x, tag in rows: self.tree.insert("", "end", values=x, tags=(tag,))
        self.sync.set(datetime.now().strftime("%H:%M:%S")); self._say("Porównaj z WM DEMO: pokazano kolorowe statusy. WM nie został odczytany.")

    def _apply(self):
        self.added.set(str(int(self.added.get()) + 2)); self.sync.set(datetime.now().strftime("%H:%M:%S")); self._say("Zastosuj zmiany DEMO: +2 w liczniku. Nic nie zapisano do WM_ROOT.")

    def _add(self):
        nr = self.no.get().strip() or "ZP/DEMO/001"; prod = self.product.get().strip() or "Produkt DEMO"; qty = self.qty.get().strip() or "1"; i = len(self.tree.get_children()) + 1
        self.tree.insert("", "end", values=(str(i), nr, prod, qty, "—", "Nowe DEMO", "Tylko ekran"), tags=("new",)); self._say(f"Dodano {nr} do tabeli DEMO. Bez zapisu do WM.")

    def _focus(self): self.no.focus_set(); self.no.select_range(0, "end"); self._say("Formularz aktywny — wpisz dane i kliknij pomarańczowy przycisk.")
    def _clear(self):
        for i in self.tree.get_children(): self.tree.delete(i)
    def _say(self, text): self.status.set(text)
    @staticmethod
    def _light(color):
        h = color.lstrip("#"); rgb = [int(h[i:i+2], 16) for i in (0,2,4)]; out = [min(255, int(v + (255-v)*0.13)) for v in rgb]; return "#" + "".join(f"{v:02X}" for v in out)


def main(): CidexDemo().mainloop()
if __name__ == "__main__": main()
