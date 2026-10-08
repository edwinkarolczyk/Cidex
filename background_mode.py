"""Windows tray mode and reliable start-with-Windows support for CIDEX."""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Any

from cidex_config import load_config, save_config

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "CIDEX"
DEFAULT_MINIMIZE_TO_TRAY = True
AUTOSTART_INITIAL_DELAY_MS = 2500
AUTOSTART_RETRY_MS = 10000


def get_minimize_to_tray() -> bool:
    return bool(load_config().get("minimize_to_tray", DEFAULT_MINIMIZE_TO_TRAY))


def set_minimize_to_tray(enabled: bool) -> None:
    data = load_config()
    data["minimize_to_tray"] = bool(enabled)
    save_config(data)


def _ps_quote(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def autostart_command_for_executable(executable: str | Path) -> str:
    """Build a hidden launcher that also sets the EXE working directory.

    CIDEX onefile uses a relative .cidex_runtime directory.  Windows Run does
    not guarantee the working directory, so launching the EXE directly can
    make PyInstaller unpack into an unwritable location.  Start-Process fixes
    the working directory before the bootloader starts.
    """
    exe = Path(executable).resolve()
    workdir = exe.parent
    command = (
        "Start-Process "
        f"-FilePath {_ps_quote(exe)} "
        f"-ArgumentList {_ps_quote('--background')} "
        f"-WorkingDirectory {_ps_quote(workdir)}"
    )
    return (
        "powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden "
        f"-Command \"{command}\""
    )


def startup_command() -> str:
    """Return the command registered for per-user Windows startup."""
    if getattr(sys, "frozen", False):
        return autostart_command_for_executable(Path(sys.executable).resolve())

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


def _read_autostart_value() -> str:
    if os.name != "nt":
        return ""
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, RUN_VALUE)
    except FileNotFoundError:
        return ""
    return str(value or "").strip()


def is_windows_autostart_enabled() -> bool:
    return bool(_read_autostart_value())


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


def repair_windows_autostart_if_enabled() -> None:
    """Upgrade an older CIDEX Run entry to the current safe launcher."""
    if os.name != "nt":
        return
    current = _read_autostart_value()
    if current and current != startup_command():
        set_windows_autostart(True)


def startup_source_ready(plan_file: str | Path) -> bool:
    """Return True only when the configured plan is currently reachable."""
    text = str(plan_file or "").strip()
    if not text:
        return False
    try:
        return Path(text).is_file()
    except OSError:
        return False


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
    """Patch the CIDEX Tk class with tray and robust Windows-startup controls."""
    if getattr(app_class, "_cidex_background_mode_installed", False):
        return

    original_init = app_class.__init__
    original_build_ui = app_class._build_ui
    original_first_run = app_class._first_run
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
            text="Autostart czeka na dysk sieciowy i działa ukryty do wykrycia zmian.",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(side="right")

    def init(self: Any) -> None:
        self._cidex_tray_controller = TrayController(self)
        self._cidex_hidden_to_tray = False
        self._cidex_quitting = False
        self._cidex_autostart_waiting = False
        original_init(self)
        self.protocol("WM_DELETE_WINDOW", self._cidex_close_window)

        try:
            repair_windows_autostart_if_enabled()
        except OSError:
            pass

        if "--background" in sys.argv:
            self.after(150, lambda: self._cidex_hide_to_tray(notify=False))

    def first_run(self: Any) -> None:
        if "--background" not in sys.argv:
            original_first_run(self)
            return

        if self._cidex_autostart_waiting:
            return
        self._cidex_autostart_waiting = True
        self.status_vars["Status"].set(
            "Start z Windows — czekam na plik planu / dysk sieciowy…"
        )
        self.after(AUTOSTART_INITIAL_DELAY_MS, self._cidex_background_first_run)

    def background_first_run(self: Any) -> None:
        plan_file = str(self.monitor.config.get("plan_file") or "").strip()
        if not plan_file:
            self.status_vars["Status"].set(
                "Start z Windows — brak skonfigurowanego pliku planu"
            )
            self._cidex_autostart_waiting = False
            return

        if not startup_source_ready(plan_file):
            self.status_vars["Status"].set(
                "Start z Windows — plik planu jeszcze niedostępny; ponawiam…"
            )
            self.after(AUTOSTART_RETRY_MS, self._cidex_background_first_run)
            return

        self._cidex_autostart_waiting = False
        original_first_run(self)

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
                (
                    "CIDEX będzie uruchamiany razem z Windowsem w tle. "
                    "Jeżeli plan jest na dysku sieciowym, program zaczeka aż dysk "
                    "będzie dostępny i sam rozpocznie monitoring."
                ),
                parent=self,
            )

    def hide_to_tray(self: Any, notify: bool = True) -> None:
        if self._cidex_hidden_to_tray:
            return
        try:
            self._cidex_tray_controller.start()
        except Exception:
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
        # During hidden autostart do not create a modal warning behind the tray.
        # The normal scheduler will retry the source on the next interval.
        if (
            getattr(result, "status", "") == "error"
            and self._cidex_hidden_to_tray
            and "--background" in sys.argv
        ):
            self._checking = False
            self.status_vars["Ostatnie sprawdzenie"].set(
                getattr(result, "checked_at", "—")
            )
            self.status_vars["Status"].set(
                "Monitoring w tle — źródło chwilowo niedostępne; ponowię próbę"
            )
            self.status_vars["Ostatni błąd"].set(
                getattr(result, "error", "") or getattr(result, "message", "")
            )
            return

        if getattr(result, "changes", None) and self._cidex_hidden_to_tray:
            self._cidex_restore_from_tray()
        original_handle_result(self, result)

    app_class._build_ui = build_ui
    app_class.__init__ = init
    app_class._first_run = first_run
    app_class._handle_result = handle_result
    app_class._cidex_background_first_run = background_first_run
    app_class._cidex_toggle_tray_setting = toggle_tray_setting
    app_class._cidex_toggle_autostart = toggle_autostart
    app_class._cidex_hide_to_tray = hide_to_tray
    app_class._cidex_restore_from_tray = restore_from_tray
    app_class._cidex_close_window = close_window
    app_class._cidex_quit_from_tray = quit_from_tray
    app_class._cidex_background_mode_installed = True
