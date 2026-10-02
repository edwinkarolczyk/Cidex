"""Read-only classification of Excel products against WM product catalog."""

from __future__ import annotations

import re
from typing import Any

from wm_store import WmStoreError, list_products


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _catalog_indexes(root: str) -> tuple[set[str], set[str]]:
    """Return exact product values and product codes used for safe prefix matching."""
    if not str(root or "").strip():
        return set(), set()

    exact: set[str] = set()
    codes: set[str] = set()
    for product in list_products(root):
        code = _norm(product.get("kod"))
        name = _norm(product.get("nazwa"))
        if code:
            codes.add(code)
            exact.add(code)
        if name:
            exact.add(name)
    return exact, codes


def product_index(root: str) -> set[str]:
    """Compatibility helper: all exact WM product codes and names."""
    exact, _codes = _catalog_indexes(root)
    return exact


def _strip_plan_suffix(symbol: str) -> str:
    """Remove plan-only decorations such as ' - RAL 7036' from a product symbol."""
    value = _norm(symbol)
    return re.sub(
        r"\s*[-–—]\s*ral\s*[-:]?\s*\d{3,4}(?:\s.*)?$",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()


def _matches_product(symbol: Any, exact: set[str], codes: set[str]) -> bool:
    normalized = _norm(symbol)
    if not normalized:
        return False
    if normalized in exact:
        return True

    base = _strip_plan_suffix(normalized)
    if base in exact or base in codes:
        return True

    # Some plans append additional readable information after the product code.
    # Match only when a real separator follows the code, never ABC-1 against ABC-10.
    separators = (" - ", " – ", " — ")
    return any(
        normalized.startswith(code + separator)
        for code in codes
        for separator in separators
    )


def enrich_changes_with_wm(
    changes: list[dict[str, Any]],
    root: str,
) -> list[dict[str, Any]]:
    """Return copied changes annotated as exists/missing/unknown in WM."""
    root = str(root or "").strip()
    available = bool(root)
    try:
        exact, codes = _catalog_indexes(root) if available else (set(), set())
    except (WmStoreError, OSError, ValueError):
        available = False
        exact, codes = set(), set()

    enriched: list[dict[str, Any]] = []
    for source in changes:
        item = dict(source)
        if not available:
            item["wm_state"] = "unknown"
            item["wm_label"] = "NIE SPRAWDZONO"
        elif _matches_product(item.get("symbol"), exact, codes):
            item["wm_state"] = "exists"
            item["wm_label"] = "ISTNIEJE W WM"
        else:
            item["wm_state"] = "missing"
            item["wm_label"] = "BRAK W WM"
        enriched.append(item)
    return enriched
