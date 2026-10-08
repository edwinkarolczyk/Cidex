import wm_compare


def test_missing_product_is_green_state(monkeypatch):
    monkeypatch.setattr(
        wm_compare,
        "list_products",
        lambda root: [{"kod": "ABC-1", "nazwa": "Produkt A"}],
    )
    changes = [{"type": "new", "symbol": "XYZ-9"}]
    result = wm_compare.enrich_changes_with_wm(changes, "C:/WM")
    assert result[0]["wm_state"] == "missing"
    assert result[0]["wm_label"] == "BRAK W WM"


def test_existing_product_is_existing_state(monkeypatch):
    monkeypatch.setattr(
        wm_compare,
        "list_products",
        lambda root: [{"kod": "ABC-1", "nazwa": "Produkt A"}],
    )
    changes = [{"type": "new", "symbol": "abc-1"}]
    result = wm_compare.enrich_changes_with_wm(changes, "C:/WM")
    assert result[0]["wm_state"] == "exists"
    assert result[0]["wm_label"] == "ISTNIEJE W WM"


def test_without_root_is_unknown():
    result = wm_compare.enrich_changes_with_wm(
        [{"type": "new", "symbol": "ABC-1"}],
        "",
    )
    assert result[0]["wm_state"] == "unknown"


def test_existing_product_matches_plan_symbol_with_ral_suffix(monkeypatch):
    monkeypatch.setattr(
        wm_compare,
        "list_products",
        lambda root: [{"kod": "6.FWB", "nazwa": "6.FWB"}],
    )
    changes = [{"type": "new", "symbol": "6.FWB - RAL 7036"}]
    result = wm_compare.enrich_changes_with_wm(changes, "C:/WM")
    assert result[0]["wm_state"] == "exists"
    assert result[0]["wm_label"] == "ISTNIEJE W WM"


def test_product_code_prefix_does_not_match_longer_code(monkeypatch):
    monkeypatch.setattr(
        wm_compare,
        "list_products",
        lambda root: [{"kod": "ABC-1", "nazwa": "Produkt A"}],
    )
    changes = [{"type": "new", "symbol": "ABC-10 - RAL 7036"}]
    result = wm_compare.enrich_changes_with_wm(changes, "C:/WM")
    assert result[0]["wm_state"] == "missing"


def test_existing_product_matches_real_plan_description_with_variant_and_ral(monkeypatch):
    monkeypatch.setattr(
        wm_compare,
        "list_products",
        lambda root: [
            {"kod": "1.330.110", "nazwa": "M27 Allit"},
            {"kod": "1.435.100", "nazwa": "Allit"},
        ],
    )
    changes = [
        {"type": "new", "symbol": "1.330.110 M27 Allit - RAL 7036"},
        {"type": "new", "symbol": "1.435.100 Allit - RAL 5010"},
    ]
    result = wm_compare.enrich_changes_with_wm(changes, "C:/WM")
    assert [item["wm_state"] for item in result] == ["exists", "exists"]
    assert [item["wm_symbol"] for item in result] == ["1.330.110", "1.435.100"]


def test_extract_product_designation_uses_only_leading_code():
    assert wm_compare.extract_product_designation(
        "1.330.110 M27 Allit - RAL 7036"
    ) == "1.330.110"
    assert wm_compare.extract_product_designation(
        "6.FWB - RAL 7036"
    ) == "6.FWB"
