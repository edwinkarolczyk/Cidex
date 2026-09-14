from search_filter import filter_changes


CHANGES = [
    {
        "type": "new",
        "type_label": "NOWE",
        "order": "222",
        "symbol": "DETAL-A",
        "old": "",
        "new": 11,
        "wm_state": "missing",
        "wm_label": "BRAK W WM",
        "department_related": True,
        "timestamp": "2026-09-14 08:00:00",
    },
    {
        "type": "quantity_changed",
        "type_label": "ILOŚĆ",
        "order": "333",
        "symbol": "DETAL-B",
        "old": 5,
        "new": 8,
        "wm_state": "exists",
        "wm_label": "ISTNIEJE W WM",
        "department_related": False,
        "timestamp": "2026-09-14 08:05:00",
    },
    {
        "type": "removed",
        "type_label": "USUNIĘTE",
        "order": "444",
        "symbol": "DETAL-C",
        "old": 3,
        "new": "",
        "wm_state": "unknown",
        "wm_label": "NIE SPRAWDZONO",
        "department_related": False,
        "timestamp": "2026-09-14 08:10:00",
    },
]


def test_search_matches_order_symbol_and_wm_status():
    assert [item["symbol"] for item in filter_changes(CHANGES, "333")] == ["DETAL-B"]
    assert [item["order"] for item in filter_changes(CHANGES, "detal-a")] == ["222"]
    assert [item["order"] for item in filter_changes(CHANGES, "brak w wm")] == ["222"]


def test_quick_filters_cover_requested_groups():
    assert len(filter_changes(CHANGES, quick_filter="Wszystkie")) == 3
    assert [item["order"] for item in filter_changes(CHANGES, quick_filter="Nowe")] == ["222"]
    assert [item["order"] for item in filter_changes(CHANGES, quick_filter="Zmienione")] == ["333"]
    assert [item["order"] for item in filter_changes(CHANGES, quick_filter="Usunięte")] == ["444"]
    assert [item["order"] for item in filter_changes(CHANGES, quick_filter="Brak w WM")] == ["222"]
    assert [item["order"] for item in filter_changes(CHANGES, quick_filter="Jest w WM")] == ["333"]


def test_search_and_quick_filter_are_combined():
    assert filter_changes(CHANGES, "DETAL-A", "Jest w WM") == []
    result = filter_changes(CHANGES, "DETAL-B", "Jest w WM")
    assert len(result) == 1
    assert result[0]["order"] == "333"
