from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from plan_monitor import (
    PlanMonitor,
    compare_plans,
    detect_column_mapping,
    normalize_quantity,
    parse_plan,
)


def _save_plan(path: Path, rows: list[list[object]]) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    for row in rows:
        worksheet.append(row)
    workbook.save(path)
    workbook.close()


def test_normalize_quantity_matches_wm_plan_monitor():
    assert normalize_quantity("450 szt") == 450
    assert normalize_quantity("12,5") == 12.5
    assert normalize_quantity("") is None


def test_detect_columns_across_header_rows():
    mapping = detect_column_mapping(
        [
            ["PLAN PRODUKCJI", None, None, None, None],
            ["Nr zlecenia", "Produkt", "Ilość", "Termin", "Proces"],
        ]
    )
    assert mapping == {
        "order": "A",
        "symbol": "B",
        "quantity": "C",
        "date": "D",
        "process": "E",
    }


def test_parse_plan_carries_order_and_date_like_wm(tmp_path: Path):
    path = tmp_path / "plan.xlsx"
    _save_plan(
        path,
        [
            ["PLAN PRODUKCJI", None, None, None, None],
            ["Nr zlecenia", "Produkt", "Ilość", "Termin", "Proces"],
            ["1001", "DETAL-A", "10 szt", "2026-09-20", "Cięcie"],
            [None, "DETAL-B", 5, None, "Gięcie"],
        ],
    )

    parsed = parse_plan(path)

    assert len(parsed.rows) == 2
    assert parsed.rows[0] == {
        "order": "1001",
        "symbol": "DETAL-A",
        "quantity": 10,
        "date": "2026-09-20",
        "process": "Cięcie",
    }
    assert parsed.rows[1] == {
        "order": "1001",
        "symbol": "DETAL-B",
        "quantity": 5,
        "date": "2026-09-20",
        "process": "Gięcie",
    }


def test_compare_plans_reports_same_change_types_as_wm():
    previous = [
        {
            "order": "1",
            "symbol": "A-100",
            "quantity": 10,
            "date": "2026-09-20",
            "process": "Cięcie",
        },
        {
            "order": "2",
            "symbol": "B-200",
            "quantity": 5,
            "date": "2026-09-21",
            "process": "Gięcie",
        },
    ]
    current = [
        {
            "order": "1",
            "symbol": "A-100",
            "quantity": 12,
            "date": "2026-09-22",
            "process": "Spawanie",
        },
        {
            "order": "3",
            "symbol": "C-300",
            "quantity": 1,
            "date": "2026-09-23",
            "process": "Pakowanie",
        },
    ]

    changes = compare_plans(
        previous,
        current,
        timestamp="2026-09-13T12:00:00",
    )
    types = [change["type"] for change in changes]

    assert types.count("quantity_changed") == 1
    assert types.count("date_changed") == 1
    assert types.count("process_changed") == 1
    assert types.count("new") == 1
    assert types.count("removed") == 1


def test_plan_monitor_persists_snapshot_and_history(tmp_path: Path):
    plan = tmp_path / "plan.xlsx"
    config = tmp_path / "config.json"
    snapshot = tmp_path / "snapshot.json"
    history = tmp_path / "history.jsonl"

    _save_plan(
        plan,
        [
            ["Nr zlecenia", "Produkt", "Ilość", "Termin", "Proces"],
            ["10", "DETAL-X", 2, "2026-09-20", "Cięcie"],
        ],
    )
    config.write_text(
        (
            "{\n"
            f'  "plan_file": "{str(plan).replace(chr(92), chr(92) * 2)}",\n'
            '  "check_interval_seconds": 60,\n'
            '  "department_keywords": [],\n'
            '  "sheet_name": null,\n'
            '  "header_scan_rows": 15,\n'
            '  "data_start_row": null,\n'
            '  "data_end_row": null,\n'
            '  "column_mapping": {\n'
            '    "order": "",\n'
            '    "symbol": "",\n'
            '    "quantity": "",\n'
            '    "date": "",\n'
            '    "process": ""\n'
            '  }\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    monitor = PlanMonitor(
        config_path=config,
        snapshot_path=snapshot,
        history_path=history,
    )

    first = monitor.check(force=True)
    assert first.status == "changed"
    assert [change["type"] for change in first.changes] == ["new"]
    assert snapshot.exists()
    assert history.exists()

    _save_plan(
        plan,
        [
            ["Nr zlecenia", "Produkt", "Ilość", "Termin", "Proces"],
            ["10", "DETAL-X", 4, "2026-09-20", "Cięcie"],
        ],
    )
    second = monitor.check(force=True)
    assert second.status == "changed"
    assert [change["type"] for change in second.changes] == [
        "quantity_changed"
    ]
