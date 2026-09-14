from runtime_compat import display_change_value, same_snapshot_source


def test_display_change_value_uses_quantity_for_row_dict():
    assert display_change_value({"order": "222", "symbol": "A", "quantity": 11}) == 11
    assert display_change_value({"order": "222", "symbol": "A", "quantity": None}) == ""
    assert display_change_value("2026-09-20") == "2026-09-20"
    assert display_change_value(None) == ""


def test_snapshot_from_another_excel_is_not_compared():
    snapshot = {"source_file": r"C:\\Plan\\stary.xlsx"}
    assert same_snapshot_source(snapshot, r"C:\\Plan\\stary.xlsx")
    assert not same_snapshot_source(snapshot, r"C:\\Plan\\nowy.xlsx")
