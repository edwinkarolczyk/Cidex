from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path

AUTHOR = "Cidex"
PROTECTED_STATUSES = {
    "w przygotowaniu", "w trakcie", "wstrzymane", "zakończone", "anulowane", "archiwum"
}


class WmStoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class RootInfo:
    selected: Path
    data_dir: Path
    orders_dir: Path
    products_dir: Path


def _norm(value) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def inspect_root(path: str | Path) -> RootInfo:
    selected = Path(path).expanduser().resolve()
    if not selected.exists():
        raise WmStoreError("Wybrany WM_ROOT nie istnieje.")
    data_dir = selected if selected.name.casefold() == "data" else selected / "data"
    orders_dir = data_dir / "zlecenia"
    products_dir = data_dir / "produkty"
    if not data_dir.is_dir():
        raise WmStoreError("Brak katalogu data w wybranym WM_ROOT.")
    if not orders_dir.is_dir():
        raise WmStoreError("Brak katalogu data/zlecenia.")
    if not products_dir.is_dir():
        raise WmStoreError("Brak katalogu data/produkty.")
    return RootInfo(selected, data_dir, orders_dir, products_dir)


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WmStoreError(f"Nie można odczytać {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise WmStoreError(f"Plik {path.name} nie zawiera obiektu JSON.")
    return data


def write_json_atomic(path: Path, data: dict) -> None:
    temp = path.with_name(path.name + ".cidex.tmp")
    try:
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise WmStoreError(f"Nie można zapisać {path.name}: {exc}") from exc


def list_products(root: str | Path) -> list[dict]:
    info = inspect_root(root)
    out = []
    for path in sorted(info.products_dir.glob("*.json")):
        try:
            data = read_json(path)
        except WmStoreError:
            continue
        code = str(data.get("kod") or data.get("symbol") or path.stem).strip()
        if not code:
            continue
        out.append({
            "kod": code,
            "nazwa": str(data.get("nazwa") or code).strip(),
            "version": data.get("version"),
        })
    return out


def list_orders(root: str | Path) -> list[dict]:
    info = inspect_root(root)
    out = []
    for path in sorted(info.orders_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            data = read_json(path)
        except WmStoreError:
            continue
        data.setdefault("id", path.stem)
        out.append(data)
    return out


def next_order_id(root: str | Path) -> str:
    nums = []
    for path in inspect_root(root).orders_dir.glob("*.json"):
        try:
            nums.append(int(path.stem))
        except ValueError:
            pass
    return f"{(max(nums) + 1 if nums else 1):06d}"


def business_key(external_no, product_code) -> str:
    return f"{_norm(external_no)}|{_norm(product_code)}"


def order_business_key(order: dict) -> str:
    prov = order.get("planista_excel")
    if isinstance(prov, dict) and prov.get("nr_zlec") and prov.get("wm_symbol"):
        return business_key(prov.get("nr_zlec"), prov.get("wm_symbol"))
    if order.get("zlec_wew") and order.get("produkt"):
        return business_key(order.get("zlec_wew"), order.get("produkt"))
    return ""


def find_orders_by_key(root, external_no, product_code) -> list[dict]:
    key = business_key(external_no, product_code)
    return [order for order in list_orders(root) if order_business_key(order) == key]


def _has_live_reservations(order: dict) -> bool:
    if bool(order.get("materialy_zarezerwowane")):
        return True
    for field in ("rezerwacje_polprodukty", "rezerwacje_surowce"):
        raw = order.get(field)
        if not isinstance(raw, dict):
            continue
        for value in raw.values():
            try:
                if float(value or 0) > 0:
                    return True
            except (TypeError, ValueError):
                return True
    return False


def _history(order: dict, what: str) -> None:
    order.setdefault("historia", []).append({
        "kiedy": datetime.now().isoformat(timespec="seconds"),
        "kto": AUTHOR,
        "co": what,
    })


def add_order(root, *, product_code: str, quantity, external_no="", due_date="", notes="", excel_meta=None) -> dict:
    product_code = str(product_code or "").strip()
    products = {item["kod"]: item for item in list_products(root)}
    if product_code not in products:
        raise WmStoreError(f"Brak produktu WM: {product_code}")
    try:
        quantity = float(quantity)
    except (TypeError, ValueError) as exc:
        raise WmStoreError("Ilość musi być liczbą.") from exc
    if quantity <= 0:
        raise WmStoreError("Ilość musi być większa od zera.")
    external_no = str(external_no or "").strip()
    if external_no and find_orders_by_key(root, external_no, product_code):
        raise WmStoreError("Istnieje już zlecenie z tym samym Zleceniem wew i Produktem.")

    oid = next_order_id(root)
    now = datetime.now()
    order = {
        "id": oid,
        "produkt": product_code,
        "ilosc": quantity,
        "wykonano": 0.0,
        "status": "nowe",
        "termin": str(due_date or "").strip(),
        "rzaz_mm": 2.0,
        "utworzono": now.strftime("%Y-%m-%d %H:%M:%S"),
        "uwagi": str(notes or ""),
        "plan_polprodukty": {},
        "zapotrzebowanie_surowce": {},
        "rezerwacje_polprodukty": {},
        "rezerwacje_surowce": {},
        "materialy_zarezerwowane": False,
        "historia": [{"kiedy": now.isoformat(timespec="seconds"), "kto": AUTHOR, "co": "utworzenie"}],
    }
    version = products[product_code].get("version")
    if version not in (None, ""):
        order["version"] = version
    if external_no:
        order["zlec_wew"] = external_no
    if excel_meta:
        order["planista_excel"] = dict(excel_meta)

    path = inspect_root(root).orders_dir / f"{oid}.json"
    if path.exists():
        raise WmStoreError(f"Plik {path.name} już istnieje.")
    write_json_atomic(path, order)
    return order


def update_order(root, order_id: str, *, quantity=None, due_date=None, notes=None, external_no=None, excel_meta=None) -> dict:
    path = inspect_root(root).orders_dir / f"{str(order_id).strip()}.json"
    if not path.is_file():
        raise WmStoreError(f"Nie znaleziono zlecenia {order_id}.")
    order = read_json(path)
    status = _norm(order.get("status"))
    changed = []

    if quantity is not None:
        try:
            new_qty = float(quantity)
        except (TypeError, ValueError) as exc:
            raise WmStoreError("Ilość musi być liczbą.") from exc
        if new_qty <= 0:
            raise WmStoreError("Ilość musi być większa od zera.")
        old_qty = float(order.get("ilosc", 0) or 0)
        if old_qty != new_qty:
            if status in PROTECTED_STATUSES:
                raise WmStoreError(f"Zlecenie ma chroniony status: {order.get('status')}.")
            if _has_live_reservations(order):
                raise WmStoreError("Zmiana ilości zablokowana: zlecenie ma rezerwacje materiałowe WM.")
            order["ilosc"] = new_qty
            changed.append(f"ilosc -> {new_qty:g}")

    if due_date is not None:
        new_due = str(due_date or "").strip()
        if str(order.get("termin") or "") != new_due:
            if status in PROTECTED_STATUSES:
                raise WmStoreError(f"Zlecenie ma chroniony status: {order.get('status')}.")
            order["termin"] = new_due
            changed.append(f"termin -> {new_due}")

    if notes is not None and str(order.get("uwagi") or "") != str(notes):
        order["uwagi"] = str(notes)
        changed.append("uwagi")

    if external_no is not None:
        new_ext = str(external_no or "").strip()
        if str(order.get("zlec_wew") or "") != new_ext:
            if new_ext:
                duplicates = [x for x in find_orders_by_key(root, new_ext, order.get("produkt")) if str(x.get("id")) != str(order_id)]
                if duplicates:
                    raise WmStoreError("Inne zlecenie ma już ten sam klucz Zlecenie wew + Produkt.")
                order["zlec_wew"] = new_ext
            else:
                order.pop("zlec_wew", None)
            changed.append(f"zlec_wew -> {new_ext}")

    if excel_meta is not None:
        order["planista_excel"] = dict(excel_meta)
        changed.append("pochodzenie Excel")

    if changed:
        _history(order, "; ".join(changed))
        write_json_atomic(path, order)
    return order
