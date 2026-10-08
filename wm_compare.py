"""Read-only classification of Excel products against WM product catalog."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from wm_store import WmStoreError, list_products

_CODE_RE = re.compile(r"^\s*([A-Za-z0-9]+(?:[.\-/_][A-Za-z0-9]+)*)")


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def normalize_designation(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    return re.sub(r"\s+", "", text)


def extract_product_designation(product_text: Any) -> str:
    """Pobierz kod produktu z początku opisu planu, np. '1.330.110 M27 Allit - RAL...'."""
    match = _CODE_RE.match(str(product_text or ""))
    return match.group(1).strip() if match else ""


def _catalog_candidates(products: list[dict[str, Any]], designation: str) -> list[dict[str, Any]]:
    target = normalize_designation(designation)
    candidates: list[dict[str, Any]] = []
    if not target:
        return candidates

    for product in products:
        if not isinstance(product, dict):
            continue
        symbol = str(product.get("kod") or product.get("symbol") or "").strip()
        if not symbol or normalize_designation(symbol) != target:
            continue
        candidates.append(
            {
                "symbol": symbol,
                "nazwa": str(product.get("nazwa") or product.get("name") or "").strip(),
                "record": product,
            }
        )
    return candidates


def _name_confirms(product_text: str, name: str) -> bool:
    normalized_name = _normalize_text(name)
    normalized_excel = _normalize_text(product_text)
    if not normalized_name or not normalized_excel:
        return False
    return f" {normalized_name} " in f" {normalized_excel} "


def match_excel_product(product_text: Any, products: list[dict[str, Any]]) -> dict[str, Any]:
    """Dopasuj produkt planu do katalogu WM tak samo jak Planista WM."""
    excel_text = str(product_text or "").strip()
    designation = extract_product_designation(excel_text)
    if not designation:
        return {
            "state": "missing",
            "label": "BRAK W WM",
            "designation": "",
            "wm_symbol": "",
            "wm_name": "",
            "note": "Nie udało się odczytać oznaczenia produktu z początku opisu Excel.",
        }

    candidates = _catalog_candidates(products, designation)
    if not candidates:
        return {
            "state": "missing",
            "label": "BRAK W WM",
            "designation": designation,
            "wm_symbol": "",
            "wm_name": "",
            "note": "Brak produktu o tym oznaczeniu w katalogu WM.",
        }

    if len(candidates) == 1:
        candidate = candidates[0]
        return {
            "state": "exists",
            "label": "ISTNIEJE W WM",
            "designation": designation,
            "wm_symbol": candidate["symbol"],
            "wm_name": candidate["nazwa"],
            "note": (
                "Oznaczenie i nazwa/wariant potwierdzone."
                if candidate["nazwa"] and _name_confirms(excel_text, candidate["nazwa"])
                else "Oznaczenie zgodne."
            ),
        }

    confirmed = [
        candidate
        for candidate in candidates
        if _name_confirms(excel_text, candidate["nazwa"])
    ]
    if len(confirmed) == 1:
        candidate = confirmed[0]
        return {
            "state": "exists",
            "label": "ISTNIEJE W WM",
            "designation": designation,
            "wm_symbol": candidate["symbol"],
            "wm_name": candidate["nazwa"],
            "note": "Kilka rekordów miało to oznaczenie; nazwa/wariant rozstrzygnęły dopasowanie.",
        }

    return {
        "state": "ambiguous",
        "label": "NIEJEDNOZNACZNY W WM",
        "designation": designation,
        "wm_symbol": "",
        "wm_name": "",
        "note": "Więcej niż jeden produkt WM pasuje do oznaczenia.",
    }


def product_index(root: str) -> set[str]:
    """Compatibility helper for tests/older callers."""
    if not str(root or "").strip():
        return set()
    return {
        normalize_designation(item.get("kod"))
        for item in list_products(root)
        if normalize_designation(item.get("kod"))
    }


def enrich_changes_with_wm(
    changes: list[dict[str, Any]],
    root: str,
) -> list[dict[str, Any]]:
    """Return copied changes annotated as exists/missing/ambiguous/unknown in WM."""
    root = str(root or "").strip()
    available = bool(root)
    products: list[dict[str, Any]] = []
    try:
        products = list_products(root) if available else []
    except (WmStoreError, OSError, ValueError):
        available = False

    enriched: list[dict[str, Any]] = []
    for source in changes:
        item = dict(source)
        if not available:
            item["wm_state"] = "unknown"
            item["wm_label"] = "NIE SPRAWDZONO"
            item["wm_designation"] = ""
            item["wm_symbol"] = ""
            item["wm_name"] = ""
            item["wm_note"] = ""
        else:
            match = match_excel_product(item.get("symbol"), products)
            item["wm_state"] = match["state"]
            item["wm_label"] = match["label"]
            item["wm_designation"] = match["designation"]
            item["wm_symbol"] = match["wm_symbol"]
            item["wm_name"] = match["wm_name"]
            item["wm_note"] = match["note"]
        enriched.append(item)
    return enriched
