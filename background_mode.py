"""Windows tray mode and optional start-with-Windows support for CIDEX."""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Any, Callable

from cidex_config import load_config, save_config

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "CIDEX"
DEFAULT_MINIMIZE_TO_TRAY = True


def get_minimize_to_tray() -> bool:
    return bool(load_config().get("minimize_to_tray", DEFAULT_MINIMIZE_TO_TRAY))


def set_minimize_to_tray(enabled: bool) -> None:
    data = load_config()
    data["minimize_to_tray"] = bool(enabled)
    save_config(data)


def startup_command() -> str:
    """Return the command registered for per-user Windows startup."""
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" --background'

    entry = Path(__file__).resolve().with_name("cidex_entry.py")
    executable = Path(sys.executable).resolve()
    pythonw = executable.with_name("pythonw.exe")
    if pythonw.is_file():
        executable = pythonw
    return f'"{executable}" "{entry}" --background'


def _winreg() -> Any:
    if os.name != "nt":
        raise OSError("Autostart CIDEX jest dostępny tylko w Windows.")
    import winreg

    return winreg


def is_windows_autostart_enabled() -> bool:
    if os.name != "nt":
        return False
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, RUN_VALUE)
    except FileNotFoundError:
        return False
    return bool(str(value).strip())


def set_windows_autostart(enabled: bool) -> None:
    """Enable/disable CIDEX startup for the current Windows user only."""
    winreg = _winreg()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, startup_command())
            return
        try:
            winreg.DeleteValue(key, RUN_VALUE)
        except FileNotFoundError:
            pass


class TrayController:
    def __init__(self, app: Any) -> None:
        self.app = app
        self.icon: Any | None = None
        self.thread: threading.Thread | None = None
        self.started = False

    @staticmethod
    def _image() -> Any:
        from PIL import Image, ImageDraw

        image = Image.new("RGB", (64, 64), (11, 17, 24))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=12, fill=(22, 119, 255))
        draw.ellipse((40, 40, 56, 56), fill=(103, 229, 138))
        return image

    def start(self) -> None:
        if self.started:
            return
        import pystray

        menu = pystray.Menu(
            pystray.MenuItem("Otwórz CIDEX", self._restore, default=True),
            pystray.MenuItem("Zakończ CIDEX", self._quit),
        )
        self.icon = pystray.Icon(
            "CIDEX",
            self._image(),
            "CIDEX — monitor Excel działa w tle",
            menu,
        )
        self.started = True
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()

    def notify_background(self) -> None:
        if not self.icon:
            return
        try:
            self.icon.notify(
                "CIDEX nadal monitoruje wybrany plik Excel.",
                "CIDEX działa w tle",
            )
        except Exception:
            pass

    def stop(self) -> None:
        icon = self.icon
        self.icon = None
        self.started = False
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass

    def _restore(self, *_args: Any) -> None:
        self.app.after(0, self.app._cidex_restore_from_tray)

    def _quit(self, *_args: Any) -> None:
        self.app.after(0, self.app._cidex_quit_from_tray)


def install_background_mode(app_class: type[Any]) -> None:
    """Patch the CIDEX Tk class with tray and Windows-startup controls."""
    if getattr(app_class, "_cidex_background_mode_installed", False):
        return

    original_init = app_class.__init__
    original_build_ui = app_class._build_ui
    original_handle_result = app_class._handle_result
    original_on_close = app_class._on_close

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        import tkinter as tk
        from main import BG, MUTED, PANEL, TEXT

        self._cidex_tray_var = tk.BooleanVar(value=get_minimize_to_tray())
        self._cidex_autostart_var = tk.BooleanVar(value=is_windows_autostart_enabled())

        bar = tk.Frame(
            self,
            bg=PANEL,
            highlightbackground="#263442",
            highlightthickness=1,
            padx=12,
            pady=7,
        )
        bar.pack(fill="x", padx=24, pady=(0, 10))
        tk.Label(
            bar,
            text="PRACA W TLE",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 14))
        tk.Checkbutton(
            bar,
            text="X = schowaj do zasobnika",
            variable=self._cidex_tray_var,
            command=self._cidex_toggle_tray_setting,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL,
            activeforeground=TEXT,
            selectcolor=BG,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 18))
        tk.Checkbutton(
            bar,
            text="Uruchamiaj CIDEX z Windows",
            variable=self._cidex_autostart_var,
            command=self._cidex_toggle_autostart,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL,
            activeforeground=TEXT,
            selectcolor=BG,
            font=("Segoe UI", 9),
        ).pack(side="left")
        tk.Label(
            bar,
            text="Po starcie z Windows monitor działa ukryty do wykrycia zmian.",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(side="right")

    def init(self: Any) -> None:
        self._cidex_tray_controller = TrayController(self)
        self._cidex_hidden_to_tray = False
        self._cidex_quitting = False
        original_init(self)
        self.protocol("WM_DELETE_WINDOW", self._cidex_close_window)
        if "--background" in sys.argv:
            self.after(150, lambda: self._cidex_hide_to_tray(notify=False))

    def toggle_tray_setting(self: Any) -> None:
        set_minimize_to_tray(bool(self._cidex_tray_var.get()))

    def toggle_autostart(self: Any) -> None:
        from tkinter import messagebox

        enabled = bool(self._cidex_autostart_var.get())
        try:
            set_windows_autostart(enabled)
        except Exception as exc:
            self._cidex_autostart_var.set(is_windows_autostart_enabled())
            messagebox.showerror("CIDEX — autostart", str(exc), parent=self)
            return
        if enabled:
            messagebox.showinfo(
                "CIDEX — autostart",
                "CIDEX będzie uruchamiany razem z Windowsem i zacznie działać w tle.",
                parent=self,
            )

    def hide_to_tray(self: Any, notify: bool = True) -> None:
        if self._cidex_hidden_to_tray:
            return
        try:
            self._cidex_tray_controller.start()
        except Exception:
            # If the tray cannot start, never make the window disappear permanently.
            original_on_close(self)
            return
        self._cidex_hidden_to_tray = True
        self.withdraw()
        if notify:
            self.after(250, self._cidex_tray_controller.notify_background)

    def restore_from_tray(self: Any) -> None:
        self._cidex_hidden_to_tray = False
        self.deiconify()
        self.state("normal")
        self.lift()
        try:
            self.focus_force()
        except Exception:
            pass

    def close_window(self: Any) -> None:
        if self._cidex_quitting:
            original_on_close(self)
            return
        if get_minimize_to_tray():
            self._cidex_hide_to_tray()
        else:
            self._cidex_quit_from_tray()

    def quit_from_tray(self: Any) -> None:
        self._cidex_quitting = True
        self._cidex_tray_controller.stop()
        original_on_close(self)

    def handle_result(self: Any, result: Any) -> None:
        if getattr(result, "changes", None) and self._cidex_hidden_to_tray:
            self._cidex_restore_from_tray()
        original_handle_result(self, result)

    app_class._build_ui = build_ui
    app_class.__init__ = init
    app_class._handle_result = handle_result
    app_class._cidex_toggle_tray_setting = toggle_tray_setting
    app_class._cidex_toggle_autostart = toggle_autostart
    app_class._cidex_hide_to_tray = hide_to_tray
    app_class._cidex_restore_from_tray = restore_from_tray
    app_class._cidex_close_window = close_window
    app_class._cidex_quit_from_tray = quit_from_tray
    app_class._cidex_background_mode_installed = True
