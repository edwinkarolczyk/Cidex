"""Single-instance guard for CIDEX on Windows."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

DEFAULT_MUTEX_NAME = r"Local\CIDEX_SINGLE_INSTANCE_2026"
ERROR_ALREADY_EXISTS = 183
SW_RESTORE = 9


class SingleInstanceGuard:
    """Keep only one CIDEX process per Windows user session."""

    def __init__(self, name: str = DEFAULT_MUTEX_NAME) -> None:
        self.name = name
        self.handle: int | None = None

    def acquire(self) -> bool:
        if os.name != "nt":
            return True

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        )
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        handle = kernel32.CreateMutexW(None, False, self.name)
        if not handle:
            raise OSError(ctypes.get_last_error(), "Nie można utworzyć blokady CIDEX.")

        self.handle = int(handle)
        return ctypes.get_last_error() != ERROR_ALREADY_EXISTS

    @staticmethod
    def restore_existing_window() -> bool:
        """Show and focus the already-running CIDEX main window."""
        if os.name != "nt":
            return False

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        found: list[int] = []
        enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def enum_proc(hwnd: int, _lparam: int) -> bool:
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value.strip()
            if title.startswith("CIDEX ") and "monitor planu Excel" in title:
                found.append(int(hwnd))
                return False
            return True

        callback = enum_proc_type(enum_proc)
        user32.EnumWindows(callback, 0)
        if not found:
            return False

        hwnd = found[0]
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        return True

    def close(self) -> None:
        if os.name != "nt" or not self.handle:
            self.handle = None
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle(wintypes.HANDLE(self.handle))
        self.handle = None
