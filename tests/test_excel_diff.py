from excel_diff import ACTION_CREATE, ACTION_NONE, ACTION_UPDATE, build_diff

PRODUCTS = [{"kod": "PRD001", "nazwa": "Stół"}]


def payload(qty=10, due="2026-09-15"):
    return {"rows": [{"nr_zlec": "123", "produkt_input": "PRD001", "ilosc": qty, "data_wysylki": due, "proces": ""}]}


def test_new_order_is_selected_for_create():
    item = build_diff(payload(), PRODUCTS, [])["items"][0]
    assert item["action"] == ACTION_CREATE
    assert item["selected"] is True


def test_same_order_is_no_change():
    orders = [{"id": "000001", "produkt": "PRD001", "ilosc": 10, "termin": "2026-09-15", "zlec_wew": "123", "status": "nowe"}]
    item = build_diff(payload(), PRODUCTS, orders)["items"][0]
    assert item["action"] == ACTION_NONE


def test_safe_quantity_change_is_update():
    orders = [{"id": "000001", "produkt": "PRD001", "ilosc": 5, "termin": "2026-09-15", "zlec_wew": "123", "status": "nowe", "materialy_zarezerwowane": False}]
    item = build_diff(payload(qty=10), PRODUCTS, orders)["items"][0]
    assert item["action"] == ACTION_UPDATE
    assert item["selected"] is True
