from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import threading
from typing import Iterable

AUTHOR = "Cidex"
MAX_PHOTO_BYTES = 15 * 1024 * 1024
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

_STATUS_ALIASES = {
    "ok": "ok",
    "sprawna": "ok",
    "sprawne": "ok",
    "sprawny": "ok",
    "dziala": "ok",
    "działa": "ok",
    "alert": "alert",
    "serwis": "alert",
    "przeglad": "alert",
    "przegląd": "alert",
    "serwis/przeglad": "alert",
    "serwis/przegląd": "alert",
    "warn": "warn",
    "warm": "warn",
    "warning": "warn",
    "awaria": "warn",
    "uszkodzona": "warn",
    "uszkodzone": "warn",
    "stop": "warn",
}

STATUS_LABELS = {
    "ok": "Sprawna",
    "alert": "Serwis / przegląd",
    "warn": "Awaria",
}

_WRITE_LOCK = threading.RLock()


class MachineStoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class MachinePaths:
    data_dir: Path
    primary: Path
    legacy: Path
    attachments: Path


def _data_dir(root: str | Path) -> Path:
    selected = Path(root).expanduser().resolve()
    if not selected.exists():
        raise MachineStoreError("Wybrany WM_ROOT nie istnieje.")
    data_dir = selected if selected.name.casefold() == "data" else selected / "data"
    if not data_dir.is_dir():
        raise MachineStoreError("Brak katalogu data w wybranym WM_ROOT.")
    return data_dir


def machine_paths(root: str | Path) -> MachinePaths:
    data_dir = _data_dir(root)
    return MachinePaths(
        data_dir=data_dir,
        primary=data_dir / "maszyny" / "maszyny.json",
        legacy=data_dir / "maszyny.json",
        attachments=data_dir / "maszyny" / "attachments",
    )


def _coerce_rows(payload) -> list[dict]:
    if isinstance(payload, list):
        return [dict(row) for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("maszyny", "machines"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [dict(row) for row in rows if isinstance(row, dict)]
        values = list(payload.values())
        if values and all(isinstance(row, dict) for row in values):
            return [dict(row) for row in values]
    return []


def _read_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MachineStoreError(f"Nie można odczytać {path}: {exc}") from exc
    return _coerce_rows(payload)


def _machine_id(machine: dict) -> str:
    return str(
        machine.get("id") or machine.get("nr_ewid") or machine.get("nr") or ""
    ).strip()


def _sort_key(machine: dict):
    value = _machine_id(machine)
    try:
        return 0, int(value)
    except ValueError:
        return 1, value.casefold()


def _merge_rows(primary: Iterable[dict], legacy: Iterable[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    anonymous: list[dict] = []
    for row in legacy:
        mid = _machine_id(row)
        if mid:
            merged[mid] = dict(row)
        else:
            anonymous.append(dict(row))
    for row in primary:
        mid = _machine_id(row)
        if mid:
            merged[mid] = dict(row)
        else:
            anonymous.append(dict(row))
    return sorted(merged.values(), key=_sort_key) + anonymous


def _signature(path: Path):
    if not path.exists():
        return None
    try:
        stat = path.stat()
    except OSError as exc:
        raise MachineStoreError(f"Nie można sprawdzić {path}: {exc}") from exc
    return stat.st_mtime_ns, stat.st_size


def load_machines(root: str | Path) -> list[dict]:
    paths = machine_paths(root)
    return _merge_rows(_read_rows(paths.primary), _read_rows(paths.legacy))


def _load_for_write(root: str | Path) -> tuple[MachinePaths, list[dict], object]:
    paths = machine_paths(root)
    signature = _signature(paths.primary)
    rows = _merge_rows(_read_rows(paths.primary), _read_rows(paths.legacy))
    return paths, rows, signature


def _write_primary(paths: MachinePaths, rows: list[dict], expected_signature) -> None:
    paths.primary.parent.mkdir(parents=True, exist_ok=True)
    if _signature(paths.primary) != expected_signature:
        raise MachineStoreError(
            "Dane Maszyn zmieniły się w WM podczas operacji. Odśwież i spróbuj ponownie."
        )
    payload = {"maszyny": rows}
    temp = paths.primary.with_name(paths.primary.name + ".cidex.tmp")
    try:
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp, paths.primary)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise MachineStoreError(f"Nie można zapisać Maszyn: {exc}") from exc


def get_machine(root: str | Path, machine_id: object) -> dict:
    wanted = str(machine_id or "").strip()
    for machine in load_machines(root):
        if _machine_id(machine) == wanted:
            return machine
    raise MachineStoreError(f"Nie znaleziono maszyny {wanted or '?'}.")


def normalize_status(value: object) -> str:
    raw = str(value or "").strip().casefold()
    if not raw:
        return "ok"
    key = " ".join(raw.replace("_", " ").replace("-", " ").split())
    direct = _STATUS_ALIASES.get(key)
    if direct:
        return direct
    compact = key.replace(" ", "")
    return _STATUS_ALIASES.get(compact, key)


def status_label(value: object) -> str:
    key = normalize_status(value)
    return STATUS_LABELS.get(key, str(value or "Sprawna"))


def _parse_date(value: object):
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _next_review(machine: dict) -> str:
    today = datetime.now().date()
    candidates = []
    for task in machine.get("zadania") or []:
        if not isinstance(task, dict):
            continue
        kind = str(task.get("typ_zadania") or task.get("typ") or "").casefold()
        if "przegl" not in kind and "serwis" not in kind:
            continue
        parsed = _parse_date(task.get("data") or task.get("termin"))
        if parsed:
            candidates.append(parsed)
    if not candidates:
        return ""
    future = sorted(item for item in candidates if item >= today)
    chosen = future[0] if future else sorted(candidates)[-1]
    return chosen.isoformat()


def photo_paths(machine: dict) -> list[str]:
    out: list[str] = []
    current = machine.get("status_current")
    if isinstance(current, dict):
        for path in current.get("photos") or []:
            text = str(path or "").strip()
            if text and text not in out:
                out.append(text)
    for event in reversed(machine.get("status_history") or []):
        if not isinstance(event, dict):
            continue
        for path in event.get("photos") or []:
            text = str(path or "").strip()
            if text and text not in out:
                out.append(text)
    return out


def machine_summary(machine: dict) -> dict:
    mid = _machine_id(machine)
    raw_status = machine.get("status")
    return {
        "id": mid,
        "nr_ewid": str(machine.get("nr_ewid") or mid).strip(),
        "nazwa": str(machine.get("nazwa") or "").strip(),
        "typ": str(machine.get("typ") or machine.get("model") or "").strip(),
        "hala": str(machine.get("hala") or machine.get("nr_hali") or "").strip(),
        "lokalizacja": str(machine.get("lokalizacja") or "").strip(),
        "status": normalize_status(raw_status),
        "status_label": status_label(raw_status),
        "next_review": _next_review(machine),
        "photo_count": len(photo_paths(machine)),
    }


def list_machine_summaries(root: str | Path) -> list[dict]:
    return [machine_summary(machine) for machine in load_machines(root)]


def decode_machine_qr(code: object) -> str:
    text = str(code or "").strip()
    if not text:
        raise MachineStoreError("Kod QR jest pusty.")
    upper = text.upper()
    if upper.startswith("CIDEX:MACHINE:"):
        return text.split(":", 2)[2].strip()
    match = re.match(r"^(?:cidex|wm)://machine/([^/?#]+)", text, re.I)
    if match:
        return match.group(1).strip()
    match = re.match(r"^machine\s*:\s*(.+)$", text, re.I)
    if match:
        return match.group(1).strip()
    return text


def resolve_machine_qr(root: str | Path, code: object) -> dict:
    return get_machine(root, decode_machine_qr(code))


def qr_value(machine: dict) -> str:
    mid = _machine_id(machine)
    if not mid:
        raise MachineStoreError("Maszyna nie ma ID do kodu QR.")
    return f"CIDEX:MACHINE:{mid}"


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _duration_minutes(started_at: object, ended_at: object) -> int:
    def parse(value):
        text = str(value or "").strip().replace("Z", "")
        if not text:
            return None
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    start = parse(started_at)
    end = parse(ended_at)
    if not start or not end:
        return 0
    return max(0, int((end - start).total_seconds() // 60))


def _ensure_status_current(machine: dict, actor: str = AUTHOR) -> dict:
    current = machine.get("status_current")
    if isinstance(current, dict):
        current.setdefault("photos", [])
        return current
    status = normalize_status(machine.get("status"))
    current = {
        "status": status,
        "label": status_label(status),
        "started_at": _now_iso(),
        "changed_by": actor,
        "note": "",
        "photos": [],
    }
    machine["status_current"] = current
    return current


def _find_index(rows: list[dict], machine_id: object) -> int:
    wanted = str(machine_id or "").strip()
    for index, machine in enumerate(rows):
        if _machine_id(machine) == wanted:
            return index
    raise MachineStoreError(f"Nie znaleziono maszyny {wanted or '?'}.")


def change_status(
    root: str | Path,
    machine_id: object,
    new_status: object,
    *,
    note: str = "",
    actor: str = AUTHOR,
) -> dict:
    normalized = normalize_status(new_status)
    if normalized not in STATUS_LABELS:
        raise MachineStoreError("Dozwolone statusy: Sprawna, Serwis / przegląd, Awaria.")
    note = str(note or "").strip()
    if normalized in {"alert", "warn"} and not note:
        raise MachineStoreError("Opis jest wymagany dla awarii i serwisu / przeglądu.")

    with _WRITE_LOCK:
        paths, rows, signature = _load_for_write(root)
        index = _find_index(rows, machine_id)
        machine = dict(rows[index])
        old_status = normalize_status(machine.get("status"))
        if old_status == normalized:
            machine["status"] = normalized
            _ensure_status_current(machine, actor=actor)
            rows[index] = machine
            _write_primary(paths, rows, signature)
            return machine

        now = _now_iso()
        current = _ensure_status_current(machine, actor=actor)
        history = machine.get("status_history")
        if not isinstance(history, list):
            history = []
            machine["status_history"] = history

        closed = dict(current)
        closed.setdefault("status", old_status)
        closed.setdefault("label", status_label(old_status))
        closed["ended_at"] = now
        closed["duration_minutes"] = _duration_minutes(
            closed.get("started_at"), now
        )
        closed["closed_by"] = actor
        closed["close_note"] = note
        history.append(closed)

        machine["status"] = normalized
        machine["status_current"] = {
            "status": normalized,
            "label": status_label(normalized),
            "started_at": now,
            "changed_by": actor,
            "note": note,
            "photos": [],
        }
        rows[index] = machine
        _write_primary(paths, rows, signature)
        return machine


def add_note(
    root: str | Path,
    machine_id: object,
    note: str,
    *,
    actor: str = AUTHOR,
) -> dict:
    note = str(note or "").strip()
    if not note:
        raise MachineStoreError("Uwaga nie może być pusta.")
    with _WRITE_LOCK:
        paths, rows, signature = _load_for_write(root)
        index = _find_index(rows, machine_id)
        machine = dict(rows[index])
        current = _ensure_status_current(machine, actor=actor)
        previous = str(current.get("note") or "").strip()
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        line = f"[{actor} {stamp}] {note}"
        current["note"] = f"{previous}\n{line}".strip() if previous else line
        rows[index] = machine
        _write_primary(paths, rows, signature)
        return machine


def _safe_file_part(value: object) -> str:
    text = str(value or "").strip()
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")
    return safe or "machine"


def add_photo(
    root: str | Path,
    machine_id: object,
    content: bytes,
    filename: str,
    *,
    actor: str = AUTHOR,
) -> tuple[dict, str]:
    if not isinstance(content, (bytes, bytearray)) or not content:
        raise MachineStoreError("Zdjęcie jest puste.")
    if len(content) > MAX_PHOTO_BYTES:
        raise MachineStoreError("Zdjęcie jest za duże. Maksymalnie 15 MB.")
    extension = Path(str(filename or "")).suffix.casefold()
    if extension not in ALLOWED_PHOTO_EXTENSIONS:
        raise MachineStoreError("Dozwolone formaty zdjęć: JPG, JPEG, PNG, WEBP, BMP.")

    with _WRITE_LOCK:
        paths, rows, signature = _load_for_write(root)
        index = _find_index(rows, machine_id)
        machine = dict(rows[index])
        current = _ensure_status_current(machine, actor=actor)

        machine_part = _safe_file_part(_machine_id(machine))
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        target_dir = paths.attachments / machine_part / stamp
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"status_01{extension}"
        try:
            target.write_bytes(bytes(content))
        except OSError as exc:
            raise MachineStoreError(f"Nie można zapisać zdjęcia: {exc}") from exc

        photos = current.get("photos")
        if not isinstance(photos, list):
            photos = []
            current["photos"] = photos
        photos.append(str(target))
        rows[index] = machine
        try:
            _write_primary(paths, rows, signature)
        except Exception:
            try:
                target.unlink(missing_ok=True)
                target_dir.rmdir()
            except OSError:
                pass
            raise
        return machine, str(target)
