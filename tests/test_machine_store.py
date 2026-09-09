import json
from pathlib import Path

import pytest

from machine_store import (
    MachineStoreError,
    add_note,
    add_photo,
    change_status,
    decode_machine_qr,
    get_machine,
    list_machines,
)


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "WM"
    machines_dir = root / "data" / "maszyny"
    machines_dir.mkdir(parents=True)
    payload = {
        "maszyny": [
            {
                "id": "42",
                "nr_ewid": "42",
                "nazwa": "Strugarka wzdłużna",
                "typ": "BLELL",
                "status": "OK",
                "hala": "1",
                "zadania": [],
            }
        ]
    }
    (machines_dir / "maszyny.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return root


def test_loads_primary_machine_wrapper(tmp_path):
    root = _root(tmp_path)
    rows = list_machines(root)
    assert len(rows) == 1
    assert rows[0]["id"] == "42"


def test_qr_uses_existing_wm_machine_id():
    assert decode_machine_qr("CIDEX:MACHINE:42") == "42"
    assert decode_machine_qr("cidex://machine/42") == "42"
    assert decode_machine_qr("42") == "42"


def test_status_change_uses_existing_wm_status_model(tmp_path):
    root = _root(tmp_path)
    machine = change_status(root, "42", "Awaria", note="Nie startuje")
    assert machine["status"] == "warn"
    assert machine["status_current"]["label"] == "Awaria"
    assert machine["status_current"]["changed_by"] == "Cidex"
    assert machine["status_current"]["note"] == "Nie startuje"
    assert machine["status_history"]

    saved = json.loads(
        (root / "data" / "maszyny" / "maszyny.json").read_text(encoding="utf-8")
    )
    assert isinstance(saved, dict)
    assert saved["maszyny"][0]["status"] == "warn"


def test_failure_and_service_require_description(tmp_path):
    root = _root(tmp_path)
    with pytest.raises(MachineStoreError):
        change_status(root, "42", "Awaria", note="")


def test_note_is_attached_to_current_status(tmp_path):
    root = _root(tmp_path)
    machine = add_note(root, "42", "Sprawdzić osłonę")
    assert "Sprawdzić osłonę" in machine["status_current"]["note"]
    assert "Cidex" in machine["status_current"]["note"]


def test_photo_goes_to_wm_machine_attachments(tmp_path):
    root = _root(tmp_path)
    machine, path = add_photo(root, "42", b"fake-jpeg", "awaria.jpg")
    target = Path(path)
    assert target.is_file()
    assert root / "data" / "maszyny" / "attachments" in target.parents
    assert path in machine["status_current"]["photos"]

    saved_machine = get_machine(root, "42")
    assert path in saved_machine["status_current"]["photos"]
