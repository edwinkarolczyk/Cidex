"""Search and quick-filter helpers for the CIDEX change list."""

from __future__ import annotations

from typing import Any, Iterable

CHANGED_TYPES = {"quantity_changed", "date_changed", "process_changed"}
FILTERS = (
    "Wszystkie",
    "Nowe",
    "Zmienione",
    "Usunięte",
    "Brak w WM",
    "Jest w WM",
)


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_text(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_text(item) for item in value)
    return str(value or "")


def _matches_quick_filter(change: dict[str, Any], quick_filter: str) -> bool:
    change_type = str(change.get("type", ""))
    wm_state = str(change.get("wm_state", ""))
    if quick_filter == "Nowe":
        return change_type == "new"
    if quick_filter == "Zmienione":
        return change_type in CHANGED_TYPES
    if quick_filter == "Usunięte":
        return change_type == "removed"
    if quick_filter == "Brak w WM":
        return wm_state == "missing"
    if quick_filter == "Jest w WM":
        return wm_state == "exists"
    return True


def searchable_text(change: dict[str, Any]) -> str:
    department = "dotyczy działu" if change.get("department_related") else "poza działem"
    parts: Iterable[Any] = (
        change.get("timestamp"),
        change.get("type"),
        change.get("type_label"),
        change.get("order"),
        change.get("symbol"),
        change.get("old"),
        change.get("new"),
        change.get("wm_label"),
        change.get("wm_state"),
        department,
    )
    return " ".join(_text(part) for part in parts).casefold()


def filter_changes(
    changes: list[dict[str, Any]],
    query: str = "",
    quick_filter: str = "Wszystkie",
) -> list[dict[str, Any]]:
    """Return changes matching both free-text search and the selected quick filter."""
    needle = str(query or "").strip().casefold()
    return [
        change
        for change in changes
        if _matches_quick_filter(change, quick_filter)
        and (not needle or needle in searchable_text(change))
    ]
