"""CIDEX: bezpieczny wybór aktywnego planu spośród oryginału i kopii."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tkinter as tk
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import plan_monitor as pm

_STATE_VERSION = 1


def _spaces(value: str) -> str:
    value = value.replace("_", " ")
    value = re.sub(r"[\-–—]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def canonical_plan_family(path: str | Path) -> str:
    """Ujednolica nazwy oryginału i typowych kopii tego samego planu."""
    stem = _spaces(Path(path).stem.casefold())
    patterns = (
        r"^(?:kopia|copy)(?:\s*\(\d+\))?\s+",
        r"\s+(?:kopia|copy)(?:\s*\(\d+\))?$",
        r"\s*\(\d+\)$",
    )
    previous = None
    while previous != stem:
        previous = stem
        for pattern in patterns:
            stem = re.sub(pattern, "", stem, flags=re.IGNORECASE).strip()
        stem = _spaces(stem)
    return stem


def discover_plan_candidates(reference: str | Path) -> list[Path]:
    """Skanuje tylko bieżący folder i tylko rodzinę nazw wskazanego planu."""
    reference_path = Path(reference)
    folder = reference_path.parent
    family = canonical_plan_family(reference_path)
    if not family or not folder.is_dir():
        return []

    try:
        entries = list(folder.iterdir())
    except OSError:
        return []

    result: list[Path] = []
    for path in entries:
        if path.name.startswith("~$"):
            continue
        if path.suffix.lower() not in pm.SUPPORTED_EXTENSIONS:
            continue
        try:
            if not path.is_file():
                continue
        except OSError:
            continue
        if canonical_plan_family(path) == family:
            result.append(path)
    return sorted(result, key=lambda item: item.name.casefold())


def _key(path: Path) -> str:
    try:
        value = str(path.resolve(strict=False))
    except OSError:
        value = str(path)
    return os.path.normcase(value)


def _signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return int(stat.st_mtime_ns), int(stat.st_size)


def _modified(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%H:%M:%S")
    except OSError:
        return ""


def _fingerprint(rows: list[dict[str, Any]]) -> str:
    records: dict[str, dict[str, Any]] = {}
    for row in rows:
        canonical = dict(row)
        canonical["date"] = pm.normalize_date(row.get("date", row.get("deadline")))
        canonical.pop("deadline", None)
        canonical.setdefault("process", "")
        records[pm.position_key(row)] = canonical
    payload = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _state_path(monitor: pm.PlanMonitor) -> Path:
    return monitor.snapshot_path.with_name("source_state.json")


def _load_state(monitor: pm.PlanMonitor) -> dict[str, Any]:
    path = _state_path(monitor)
    if not path.is_file():
        return {"version": _STATE_VERSION, "sources": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": _STATE_VERSION, "sources": {}}
    if not isinstance(data, dict):
        return {"version": _STATE_VERSION, "sources": {}}
    if not isinstance(data.get("sources"), dict):
        data["sources"] = {}
    data["version"] = _STATE_VERSION
    return data


def _save_state(monitor: pm.PlanMonitor, state: dict[str, Any]) -> None:
    path = _state_path(monitor)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temp, path)


def _make_result(
    status: str,
    checked_at: str,
    *,
    modified_at: str = "",
    changes: list[dict[str, Any]] | None = None,
    message: str = "",
    parser: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
    error: str = "",
    source_file: str = "",
    candidate_count: int = 0,
    source_reason: str = "",
    conflict_files: list[str] | None = None,
) -> pm.CheckResult:
    result = pm.CheckResult(
        status=status,
        checked_at=checked_at,
        file_modified_at=modified_at,
        changes=changes or [],
        message=message,
        parser=parser or {},
        rows=rows or [],
        error=error,
    )
    result.source_file = source_file
    result.candidate_count = candidate_count
    result.source_reason = source_reason
    result.conflict_files = conflict_files or []
    return result


def _pick(paths: list[Path], reference: Path, active_source: str) -> Path:
    active_key = _key(Path(active_source)) if active_source else ""
    for path in paths:
        if _key(path) == active_key:
            return path
    reference_key = _key(reference)
    for path in paths:
        if _key(path) == reference_key:
            return path
    return max(paths, key=lambda item: (_signature(item)[0], item.name.casefold()))


def _snapshot_timestamp(snapshot: dict[str, Any] | None) -> float | None:
    if not snapshot:
        return None
    text = str(snapshot.get("created_at") or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _route_check(self: pm.PlanMonitor, force: bool = False) -> pm.CheckResult:
    checked_at = datetime.now().strftime("%H:%M:%S")
    reference_text = str(self.config.get("plan_file") or "").strip()
    if not reference_text:
        message = "Nie wybrano pliku planu."
        return _make_result("error", checked_at, message=message, error=message)

    reference = Path(reference_text)
    candidates = discover_plan_candidates(reference)
    if not candidates:
        message = (
            "Nie znaleziono pliku planu ani jego kopii w folderze: "
            f"{reference.parent}"
        )
        return _make_result("error", checked_at, message=message, error=message)

    snapshot = pm.load_snapshot(self.snapshot_path)
    baseline_rows = pm.snapshot_rows(snapshot)
    baseline_fp = _fingerprint(baseline_rows) if snapshot else ""
    snapshot_time = _snapshot_timestamp(snapshot)
    snapshot_source_key = (
        _key(Path(str(snapshot.get("source_file") or "")))
        if snapshot and snapshot.get("source_file")
        else ""
    )

    if snapshot and not self.last_rows:
        self.last_rows = list(baseline_rows)
        self.last_parser = dict(snapshot.get("parser") or {})

    previous_state = _load_state(self)
    previous_sources = previous_state.get("sources", {})
    next_sources: dict[str, Any] = {}
    parsed: dict[str, pm.ParseResult] = {}
    fingerprints: dict[str, str] = {}
    changed_keys: set[str] = set()

    selected_once = str(getattr(self, "_cidex_selected_source_once", "") or "")
    selected_once_key = os.path.normcase(selected_once) if selected_once else ""

    try:
        for path in candidates:
            key = _key(path)
            mtime_ns, size = _signature(path)
            previous = previous_sources.get(key) or {}
            previous_fp = str(previous.get("fingerprint") or "")
            signature_changed = previous.get("signature") != [mtime_ns, size]
            need_parse = (
                force
                or signature_changed
                or not previous_fp
                or key == selected_once_key
            )

            fingerprint = previous_fp
            if need_parse:
                result = self._read(str(path))
                parsed[key] = result
                fingerprint = _fingerprint(result.rows)

            if previous:
                logical_changed = signature_changed or (
                    bool(previous_fp) and fingerprint != previous_fp
                )
            elif snapshot:
                mtime = mtime_ns / 1_000_000_000
                newer = snapshot_time is None or mtime > snapshot_time + 0.001
                logical_changed = (
                    fingerprint != baseline_fp
                    and (newer or key == snapshot_source_key)
                )
            else:
                logical_changed = True

            if logical_changed:
                changed_keys.add(key)

            fingerprints[key] = fingerprint
            next_sources[key] = {
                "path": str(path),
                "signature": [mtime_ns, size],
                "fingerprint": fingerprint,
                "modified_at": _modified(path),
            }
    except Exception as exc:
        logging.exception("[PLAN][SOURCE] bezpieczny odczyt źródła nie powiódł się")
        message = (
            "Nie udało się wykonać bezpiecznej kopii jednego z plików planu. "
            "CIDEX niczego nie nadpisał i ponowi próbę. "
            f"Szczegóły: {exc}"
        )
        return _make_result(
            "error",
            checked_at,
            message=message,
            error=message,
            candidate_count=len(candidates),
        )

    active_source = str(
        previous_state.get("active_source")
        or (snapshot.get("source_file") if snapshot else "")
        or ""
    )
    selected: Path | None = None
    reason = ""

    if selected_once:
        selected = next(
            (path for path in candidates if _key(path) == selected_once_key),
            None,
        )
        if selected is None:
            self._cidex_selected_source_once = ""
            message = "Wybrany plik nie jest już dostępny w folderze planu."
            return _make_result(
                "error",
                checked_at,
                message=message,
                error=message,
                candidate_count=len(candidates),
            )
        reason = "wybór użytkownika"

    elif not snapshot:
        groups: dict[str, list[Path]] = {}
        for path in candidates:
            groups.setdefault(fingerprints[_key(path)], []).append(path)
        if len(groups) > 1:
            return _make_result(
                "conflict",
                checked_at,
                message=(
                    "Wykryto kilka różnych wersji planu. CIDEX nie zgaduje po "
                    "dacie pliku — wybierz właściwe źródło."
                ),
                error="Konflikt wersji planu",
                candidate_count=len(candidates),
                conflict_files=[str(path) for path in candidates],
            )
        selected = _pick(next(iter(groups.values())), reference, active_source)
        reason = "pierwszy bezpieczny odczyt"

    else:
        changed_content: dict[str, list[Path]] = {}
        for path in candidates:
            key = _key(path)
            if key not in changed_keys:
                continue
            fingerprint = fingerprints[key]
            if fingerprint != baseline_fp:
                changed_content.setdefault(fingerprint, []).append(path)

        if len(changed_content) > 1:
            files = [str(path) for group in changed_content.values() for path in group]
            return _make_result(
                "conflict",
                checked_at,
                message=(
                    "Jednocześnie zmieniono kilka kopii planu i zawierają różne "
                    "dane. Snapshot nie został zmieniony. Wybierz właściwy plik."
                ),
                error="Konflikt wersji planu",
                candidate_count=len(candidates),
                conflict_files=files,
            )

        if len(changed_content) == 1:
            same = next(iter(changed_content.values()))
            selected = _pick(same, reference, active_source)
            reason = (
                "zmieniony plik planu"
                if len(same) == 1
                else "kilka kopii z identyczną zmianą"
            )
        else:
            baseline_paths = [
                path
                for path in candidates
                if fingerprints.get(_key(path)) == baseline_fp
            ]
            if baseline_paths:
                selected = _pick(baseline_paths, reference, active_source)
                active_source = str(selected)
            _save_state(
                self,
                {
                    "version": _STATE_VERSION,
                    "reference": str(reference),
                    "active_source": active_source,
                    "sources": next_sources,
                },
            )
            return _make_result(
                "unchanged",
                checked_at,
                modified_at=_modified(selected) if selected else "",
                message="Żaden plik planu nie zawiera nowych zmian.",
                parser=self.last_parser,
                rows=self.last_rows,
                source_file=active_source,
                candidate_count=len(candidates),
                source_reason="brak zmian danych",
            )

    if selected is None:
        message = "Nie udało się ustalić aktywnego źródła planu."
        return _make_result(
            "error",
            checked_at,
            message=message,
            error=message,
            candidate_count=len(candidates),
        )

    selected_key = _key(selected)
    selected_parse = parsed.get(selected_key)
    if selected_parse is None:
        try:
            selected_parse = self._read(str(selected))
        except Exception as exc:
            logging.exception("[PLAN][SOURCE] odczyt wybranego źródła nie powiódł się")
            message = f"Błąd bezpiecznego odczytu wybranego pliku: {exc}"
            return _make_result(
                "error",
                checked_at,
                message=message,
                error=message,
                candidate_count=len(candidates),
            )
        parsed[selected_key] = selected_parse
        fingerprints[selected_key] = _fingerprint(selected_parse.rows)
        next_sources[selected_key]["fingerprint"] = fingerprints[selected_key]

    rows = selected_parse.rows
    parser = asdict(selected_parse.diagnostics)
    changes = pm.compare_plans(
        baseline_rows,
        rows,
        self.config.get("department_keywords", []),
    )
    pm.save_snapshot(
        rows,
        {
            "plan_file": str(selected),
            "read_at": datetime.now().isoformat(timespec="seconds"),
            "sheet": selected_parse.diagnostics.sheet,
            "parser": parser,
        },
        self.snapshot_path,
    )
    if changes:
        pm.append_history(changes, self.history_path)

    _save_state(
        self,
        {
            "version": _STATE_VERSION,
            "reference": str(reference),
            "active_source": str(selected),
            "sources": next_sources,
        },
    )

    mtime_ns, size = _signature(selected)
    self.last_signature = (mtime_ns / 1_000_000_000, size)
    self.last_parser = parser
    self.last_rows = rows
    self._cidex_selected_source_once = ""

    logging.info(
        "[PLAN][SOURCE] aktywne=%s; kandydaci=%s; powod=%s; zmiany=%s",
        selected,
        len(candidates),
        reason,
        len(changes),
    )
    return _make_result(
        "changed" if changes else "unchanged",
        checked_at,
        modified_at=_modified(selected),
        changes=changes,
        message=pm.notification_message(changes),
        parser=parser,
        rows=rows,
        source_file=str(selected),
        candidate_count=len(candidates),
        source_reason=reason,
    )


def _select_source(self: pm.PlanMonitor, path: str | Path) -> None:
    self._cidex_selected_source_once = _key(Path(path))


class _ConflictDialog(tk.Toplevel):
    def __init__(self, parent: Any, files: list[str]) -> None:
        super().__init__(parent)
        self.parent = parent
        self.title("CIDEX — konflikt wersji planu")
        self.geometry("760x420")
        self.minsize(680, 360)
        self.configure(bg="#0B1118")
        self.transient(parent)
        self.lift()

        tk.Label(
            self,
            text="WYKRYTO RÓŻNE WERSJE PLANU",
            bg="#0B1118",
            fg="#FF7A00",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=18, pady=(18, 6))
        tk.Label(
            self,
            text=(
                "CIDEX nie wybiera pliku po samej dacie modyfikacji. "
                "Oryginał i kopie nie są nadpisywane ani pozostawiane otwarte. "
                "Wskaż wersję, która jest aktualnym planem."
            ),
            bg="#0B1118",
            fg="#9BA9B7",
            justify="left",
            wraplength=710,
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=18, pady=(0, 12))

        body = tk.Frame(self, bg="#111A23")
        body.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        for path_text in files:
            row = tk.Frame(body, bg="#111A23")
            row.pack(fill="x", padx=10, pady=6)
            tk.Label(
                row,
                text=Path(path_text).name,
                bg="#111A23",
                fg="#F3F6F8",
                anchor="w",
                font=("Segoe UI", 10, "bold"),
            ).pack(side="left", fill="x", expand=True)
            tk.Button(
                row,
                text="Użyj tego pliku",
                command=lambda value=path_text: self._choose(value),
                bg="#1677FF",
                fg="white",
                activebackground="#1677FF",
                activeforeground="white",
                bd=0,
                padx=12,
                pady=6,
            ).pack(side="right")

        tk.Button(
            self,
            text="Zamknij — niczego nie zmieniaj",
            command=self.destroy,
            bg="#344553",
            fg="white",
            bd=0,
            padx=14,
            pady=7,
        ).pack(anchor="e", padx=18, pady=(0, 16))

    def _choose(self, path: str) -> None:
        self.parent.monitor.select_source(path)
        self.parent._check_async(force=True)
        self.destroy()


def _install_ui(app_class: type[Any]) -> None:
    if getattr(app_class, "_cidex_source_router_ui_installed", False):
        return

    original_handle = app_class._handle_result

    def handle_result(self: Any, result: Any) -> None:
        if getattr(result, "status", "") == "conflict":
            self._checking = False
            self.status_vars["Ostatnie sprawdzenie"].set(result.checked_at)
            self.status_vars["Status"].set(
                f"KONFLIKT PLANU — {getattr(result, 'candidate_count', 0)} źródła"
            )
            self.status_vars["Ostatni błąd"].set("Wybierz właściwą wersję planu")
            self.summary.set(result.message)
            existing = getattr(self, "_cidex_source_conflict_dialog", None)
            if existing is not None:
                try:
                    if existing.winfo_exists():
                        existing.lift()
                        return
                except tk.TclError:
                    pass
            dialog = _ConflictDialog(
                self,
                list(getattr(result, "conflict_files", []) or []),
            )
            self._cidex_source_conflict_dialog = dialog
            return

        original_handle(self, result)
        source = str(getattr(result, "source_file", "") or "")
        if source:
            count = int(getattr(result, "candidate_count", 0) or 0)
            reason = str(getattr(result, "source_reason", "") or "")
            self.status_vars["Plik"].set(source)
            base = self.status_vars["Status"].get()
            suffix = f" • źródła: {count} • aktywny: {Path(source).name}"
            if reason:
                suffix += f" ({reason})"
            self.status_vars["Status"].set(base + suffix)

    app_class._handle_result = handle_result
    app_class._cidex_source_router_ui_installed = True


def install_plan_source_router(app_class: type[Any] | None = None) -> None:
    if not getattr(pm.PlanMonitor, "_cidex_source_router_installed", False):
        pm.PlanMonitor.check = _route_check
        pm.PlanMonitor.select_source = _select_source
        pm.PlanMonitor._cidex_source_router_installed = True
    if app_class is not None:
        _install_ui(app_class)
