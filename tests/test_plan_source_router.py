from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook

from excel_source_guard import install_excel_source_guard
from plan_monitor import PlanMonitor, load_snapshot, snapshot_rows
from plan_source_router import (
    canonical_plan_family,
    discover_plan_candidates,
    install_plan_source_router,
)


def _save_plan(path: Path, quantity: int) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Nr zlecenia", "Produkt", "Ilość", "Termin", "Proces"])
    worksheet.append(["10", "DETAL-X", quantity, "2026-10-02", "Cięcie"])
    workbook.save(path)
    workbook.close()


def _config(path: Path, plan: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "plan_file": str(plan),
                "check_interval_seconds": 60,
                "department_keywords": [],
                "sheet_name": None,
                "header_scan_rows": 15,
                "data_start_row": None,
                "data_end_row": None,
                "column_mapping": {
                    "order": "",
                    "symbol": "",
                    "quantity": "",
                    "date": "",
                    "process": "",
                },
            }
        ),
        encoding="utf-8",
    )


def _monitor(tmp_path: Path, reference: Path) -> PlanMonitor:
    config = tmp_path / "config.json"
    _config(config, reference)
    return PlanMonitor(
        config_path=config,
        snapshot_path=tmp_path / "snapshot.json",
        history_path=tmp_path / "history.jsonl",
    )


def test_copy_names_belong_to_same_family() -> None:
    expected = "plan produkcji 2026"
    assert canonical_plan_family("Plan Produkcji 2026.xlsx") == expected
    assert canonical_plan_family("Kopia Plan Produkcji 2026.xlsx") == expected
    assert canonical_plan_family("Kopia (2) Plan Produkcji 2026.xlsx") == expected
    assert canonical_plan_family("Plan Produkcji 2026 - kopia.xlsx") == expected
    assert canonical_plan_family("Plan Produkcji 2026 (3).xlsx") == expected


def test_discovery_ignores_unrelated_and_excel_lock_files(tmp_path: Path) -> None:
    reference = tmp_path / "Plan Produkcji 2026.xlsx"
    names = [
        reference.name,
        "Kopia Plan Produkcji 2026.xlsx",
        "Kopia (2) Plan Produkcji 2026.xlsx",
        "Plan Produkcji 2026 - kopia.xlsm",
        "Grafik pracowników.xlsx",
        "Zamówienia.xlsx",
        "~$Plan Produkcji 2026.xlsx",
    ]
    for name in names:
        (tmp_path / name).write_bytes(b"x")

    found = {path.name for path in discover_plan_candidates(reference)}

    assert found == {
        "Plan Produkcji 2026.xlsx",
        "Kopia Plan Produkcji 2026.xlsx",
        "Kopia (2) Plan Produkcji 2026.xlsx",
        "Plan Produkcji 2026 - kopia.xlsm",
    }


def test_changed_copy_becomes_active_source(tmp_path: Path) -> None:
    install_excel_source_guard()
    install_plan_source_router()

    original = tmp_path / "Plan Produkcji 2026.xlsx"
    copy = tmp_path / "Kopia Plan Produkcji 2026.xlsx"
    _save_plan(original, 2)
    _save_plan(copy, 2)

    monitor = _monitor(tmp_path, original)
    first = monitor.check(force=True)
    assert first.status == "changed"
    assert Path(first.source_file) == original

    _save_plan(copy, 4)
    second = monitor.check()

    assert second.status == "changed"
    assert Path(second.source_file) == copy
    assert [item["type"] for item in second.changes] == ["quantity_changed"]
    assert snapshot_rows(load_snapshot(monitor.snapshot_path))[0]["quantity"] == 4


def test_different_simultaneous_changes_require_operator_choice(tmp_path: Path) -> None:
    install_excel_source_guard()
    install_plan_source_router()

    original = tmp_path / "Plan Produkcji 2026.xlsx"
    copy = tmp_path / "Kopia Plan Produkcji 2026.xlsx"
    _save_plan(original, 2)
    _save_plan(copy, 2)

    monitor = _monitor(tmp_path, original)
    monitor.check(force=True)

    _save_plan(original, 3)
    _save_plan(copy, 4)
    conflict = monitor.check(force=True)

    assert conflict.status == "conflict"
    assert {Path(item).name for item in conflict.conflict_files} == {
        original.name,
        copy.name,
    }
    assert snapshot_rows(load_snapshot(monitor.snapshot_path))[0]["quantity"] == 2

    monitor.select_source(copy)
    resolved = monitor.check(force=True)
    assert resolved.status == "changed"
    assert Path(resolved.source_file) == copy
    assert snapshot_rows(load_snapshot(monitor.snapshot_path))[0]["quantity"] == 4
