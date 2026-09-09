import json
from pathlib import Path

import pytest

from wm_store import WmStoreError, add_order, inspect_root, update_order


def make_root(tmp_path: Path):
    data = tmp_path / "data"
    (data / "zlecenia").mkdir(parents=True)
    (data / "produkty").mkdir(parents=True)
    (data / "produkty" / "PRD001.json").write_text(
        json.dumps({"kod": "PRD001", "nazwa": "Stół", "version": "1.0"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return tmp_path


def test_add_order_uses_cidex_and_two_space_json(tmp_path):
    root = make_root(tmp_path)
    order = add_order(root, product_code="PRD001", quantity=10, external_no="123", due_date="2026-09-15")
    assert order["id"] == "000001"
    assert order["produkt"] == "PRD001"
    assert order["zlec_wew"] == "123"
    assert order["historia"][0]["kto"] == "Cidex"
    assert order["materialy_zarezerwowane"] is False
    text = (root / "data" / "zlecenia" / "000001.json").read_text(encoding="utf-8")
    assert '\n  "produkt"' in text


def test_duplicate_business_key_is_blocked(tmp_path):
    root = make_root(tmp_path)
    add_order(root, product_code="PRD001", quantity=10, external_no="123")
    with pytest.raises(WmStoreError):
        add_order(root, product_code="PRD001", quantity=5, external_no="123")


def test_quantity_update_with_reservations_is_blocked(tmp_path):
    root = make_root(tmp_path)
    order = add_order(root, product_code="PRD001", quantity=10, external_no="123")
    path = root / "data" / "zlecenia" / f"{order['id']}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["materialy_zarezerwowane"] = True
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(WmStoreError):
        update_order(root, order["id"], quantity=20)


def test_root_accepts_wm_root_and_data_root(tmp_path):
    root = make_root(tmp_path)
    assert inspect_root(root).data_dir == root / "data"
    assert inspect_root(root / "data").data_dir == root / "data"
