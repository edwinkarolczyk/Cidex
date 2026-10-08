from __future__ import annotations

from pathlib import Path

from background_mode import (
    autostart_command_for_executable,
    startup_source_ready,
)


def test_autostart_launcher_sets_working_directory(tmp_path: Path) -> None:
    exe = tmp_path / "CIDEX Folder" / "Cidex.exe"
    exe.parent.mkdir()
    command = autostart_command_for_executable(exe)

    assert "powershell.exe" in command
    assert "-WindowStyle Hidden" in command
    assert "Start-Process" in command
    assert str(exe.resolve()) in command
    assert str(exe.parent.resolve()) in command
    assert "--background" in command
    assert "-WorkingDirectory" in command


def test_startup_source_ready_waits_for_plan_file(tmp_path: Path) -> None:
    plan = tmp_path / "Plan Produkcji 2026.xlsx"

    assert startup_source_ready(plan) is False

    plan.write_bytes(b"xlsx-placeholder")
    assert startup_source_ready(plan) is True


def test_startup_source_ready_rejects_empty_value() -> None:
    assert startup_source_ready("") is False
