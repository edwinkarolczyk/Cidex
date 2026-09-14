import pytest

from settings_enhancements import build_plan_config


def _values() -> dict[str, str]:
    return {
        "plan_file": "C:/Plan/produkcja.xlsx",
        "check_interval_seconds": "60",
        "department_keywords": "CIĘCIE, MONTAŻ",
        "sheet_name": "",
        "header_scan_rows": "15",
        "data_start_row": "",
        "data_end_row": "",
        "order": "",
        "symbol": "",
        "quantity": "",
        "date": "",
        "process": "",
    }


def test_settings_preserve_auto_columns_and_unrelated_keys() -> None:
    current = {"other_key": "keep-me", "column_mapping": {}}
    result = build_plan_config(current, _values())

    assert result["other_key"] == "keep-me"
    assert result["check_interval_seconds"] == 60
    assert result["sheet_name"] is None
    assert result["column_mapping"] == {
        "order": "",
        "symbol": "",
        "quantity": "",
        "date": "",
        "process": "",
    }
    assert result["department_keywords"] == ["CIĘCIE", "MONTAŻ"]


def test_settings_reject_end_row_before_start_row() -> None:
    values = _values()
    values["data_start_row"] = "20"
    values["data_end_row"] = "10"

    with pytest.raises(ValueError):
        build_plan_config({}, values)
