from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from wm_store import PROTECTED_STATUSES, business_key, order_business_key

ACTION_CREATE = "Utwórz"
ACTION_UPDATE = "Aktualizuj"
ACTION_NONE = "Bez zmian"
ACTION_SKIP = "Nie importuj"
ACTION_CONFLICT = "Wymaga decyzji"
ACTION_PROTECTED = "Chronione"
ACTION_REMOVED = "Usunięte w Excelu"


def _text(value) -> str:
    return str(value or "").strip()


def _norm(value) -> str:
    return " ".join(_text(value).casefold().split())


def _qty(value):
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def match_product(value, products: list[dict]):
    raw = _text(value)
    by_code = {_norm(p.get("kod")): p for p in products if _text(p.get("kod"))}
    by_name = defaultdict(list)
    for product in products:
        if _text(product.get("nazwa")):
            by_name[_norm(product.get("nazwa"))].append(product)
    if _norm(raw) in by_code:
        p = by_code[_norm(raw)]
        return "found", _text(p.get("kod")), _text(p.get("nazwa"))
    matches = by_name.get(_norm(raw), [])
    if len(matches) == 1:
        p = matches[0]
        return "found", _text(p.get("kod")), _text(p.get("nazwa"))
    if len(matches) > 1:
        return "ambiguous", "", ""
    return "missing", "", ""


def source_meta(payload: dict, item: dict) -> dict:
    row = dict(item.get("row") or {})
    return {
        "schema": 1,
        "typ": "plan_excel",
        "nr_zlec": _text(item.get("nr_zlec")),
        "wm_symbol": _text(item.get("wm_symbol")),
        "excel_oznaczenie": _text(row.get("produkt_input")),
        "proces": _text(row.get("proces")),
        "source_name": _text(payload.get("source_name")),
        "source_path": _text(payload.get("source_path")),
        "sheet": _text(payload.get("sheet")),
        "source_sha256": _text(payload.get("source_sha256")),
        "identity": business_key(item.get("nr_zlec"), item.get("wm_symbol")),
        "last_sync_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def build_diff(payload: dict, products: list[dict], orders: list[dict]) -> dict:
    current_by_key = defaultdict(list)
    by_external = defaultdict(list)
    for order in orders:
        key = order_business_key(order)
        if key:
            current_by_key[key].append(order)
        ext = _text(order.get("zlec_wew"))
        prov = order.get("planista_excel")
        if isinstance(prov, dict):
            ext = _text(prov.get("nr_zlec") or ext)
        if ext:
            by_external[_norm(ext)].append(order)

    prepared = []
    counts = defaultdict(int)
    for raw in payload.get("rows") or []:
        row = dict(raw)
        status, code, name = match_product(row.get("produkt_input"), products)
        row["product_match"] = status
        row["wm_symbol"] = code
        row["wm_name"] = name
        if status == "found":
            counts[business_key(row.get("nr_zlec"), code)] += 1
        prepared.append(row)

    items = []
    excel_keys = set()
    for row in prepared:
        nr = _text(row.get("nr_zlec"))
        qty = _qty(row.get("ilosc"))
        match = row.get("product_match")
        item = {
            "identity": "",
            "nr_zlec": nr,
            "produkt_input": _text(row.get("produkt_input")),
            "wm_symbol": _text(row.get("wm_symbol")),
            "wm_name": _text(row.get("wm_name")),
            "ilosc_excel": qty,
            "ilosc_wm": None,
            "termin_excel": _text(row.get("data_wysylki")),
            "termin_wm": "",
            "status": "",
            "action": ACTION_SKIP,
            "reason": "",
            "order_id": "",
            "selected": False,
            "row": row,
        }
        if not nr:
            item.update(status="Brak nr zlecenia", reason="Brak Nr zlec. w Excelu.")
            items.append(item); continue
        if match == "missing":
            item.update(status="Brak produktu w WM", reason="Produktu nie znaleziono po kodzie ani nazwie.")
            items.append(item); continue
        if match == "ambiguous":
            item.update(status="Niejednoznaczny produkt", action=ACTION_CONFLICT, reason="Kilka produktów WM ma tę samą nazwę.")
            items.append(item); continue
        if qty is None or qty <= 0:
            item.update(status="Błędna ilość", reason="Ilość musi być większa od zera.")
            items.append(item); continue

        key = business_key(nr, row.get("wm_symbol"))
        item["identity"] = key
        excel_keys.add(key)
        if counts[key] > 1:
            item.update(status="Duplikat w Excelu", action=ACTION_CONFLICT, reason="Ten sam Nr zlec. + Produkt występuje więcej niż raz.")
            items.append(item); continue

        matches = current_by_key.get(key, [])
        if len(matches) > 1:
            item.update(status="Duplikat w WM", action=ACTION_CONFLICT, reason="Więcej niż jedno zlecenie WM ma ten sam klucz.")
            items.append(item); continue
        if not matches:
            different = [o for o in by_external.get(_norm(nr), []) if _norm(o.get("produkt")) != _norm(row.get("wm_symbol"))]
            if different:
                item.update(status="Zmiana produktu", action=ACTION_CONFLICT, reason="Nr zlecenia istnieje w WM z innym produktem.", order_id=_text(different[0].get("id")))
            else:
                item.update(status="Nowe", action=ACTION_CREATE, reason="Brak tego klucza w WM.", selected=True)
            items.append(item); continue

        order = matches[0]
        item["order_id"] = _text(order.get("id"))
        item["ilosc_wm"] = _qty(order.get("ilosc"))
        item["termin_wm"] = _text(order.get("termin"))
        changes = []
        if item["ilosc_wm"] != qty:
            changes.append("ilość")
        if item["termin_wm"] != item["termin_excel"]:
            changes.append("data")
        if not changes:
            item.update(status="Bez zmian", action=ACTION_NONE, reason="Ilość i data są zgodne.")
            items.append(item); continue

        if _norm(order.get("status")) in PROTECTED_STATUSES:
            item.update(status="Chronione", action=ACTION_PROTECTED, reason=f"Status WM: {order.get('status')}.")
            items.append(item); continue
        if bool(order.get("materialy_zarezerwowane")) and "ilość" in changes:
            item.update(status="Rezerwacje WM", action=ACTION_PROTECTED, reason="Zmiana ilości wymaga logiki rezerwacji WM.")
            items.append(item); continue

        item.update(status="Zmiana " + " + ".join(changes), action=ACTION_UPDATE, reason="Bezpieczna aktualizacja.", selected=True)
        items.append(item)

    for order in orders:
        prov = order.get("planista_excel")
        if not isinstance(prov, dict):
            continue
        key = order_business_key(order)
        if not key or key in excel_keys:
            continue
        items.append({
            "identity": key,
            "nr_zlec": _text(prov.get("nr_zlec")),
            "produkt_input": _text(prov.get("excel_oznaczenie")),
            "wm_symbol": _text(order.get("produkt")),
            "wm_name": "",
            "ilosc_excel": None,
            "ilosc_wm": _qty(order.get("ilosc")),
            "termin_excel": "",
            "termin_wm": _text(order.get("termin")),
            "status": "Usunięte w Excelu",
            "action": ACTION_REMOVED,
            "reason": "Tylko informacja. Cidex nie usuwa zleceń z WM.",
            "order_id": _text(order.get("id")),
            "selected": False,
            "row": {},
        })

    return {
        "items": items,
        "can_write": any(i.get("selected") and i.get("action") in {ACTION_CREATE, ACTION_UPDATE} for i in items),
    }
