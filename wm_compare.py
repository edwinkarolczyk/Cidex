"""Read-only classification of Excel products against WM product catalog."""

from __future__ import annotations

from typing import Any

from wm_store import WmStoreError, list_products


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def product_index(root: str) -> set[str]:
    if not str(root or "").strip():
        return set()
    products = list_products(root)
    index: set[str] = set()
    for product in products:
        for value in (product.get("kod"), product.get("nazwa")):
            normalized = _norm(value)
            if normalized:
                index.add(normalized)
    return index


def enrich_changes_with_wm(
    changes: list[dict[str, Any]],
    root: str,
) -> list[dict[str, Any]]:
    """Return copied changes annotated as exists/missing/unknown in WM."""
    root = str(root or "").strip()
    available = bool(root)
    try:
        index = product_index(root) if available else set()
    except (WmStoreError, OSError, ValueError):
        available = False
        index = set()

    enriched: list[dict[str, Any]] = []
    for source in changes:
        item = dict(source)
        if not available:
            item["wm_state"] = "unknown"
            item["wm_label"] = "NIE SPRAWDZONO"
        elif _norm(item.get("symbol")) in index:
            item["wm_state"] = "exists"
            item["wm_label"] = "ISTNIEJE W WM"
        else:
            item["wm_state"] = "missing"
            item["wm_label"] = "BRAK W WM"
        enriched.append(item)
    return enriched
