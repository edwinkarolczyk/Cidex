from io import BytesIO
import json
from pathlib import Path

from api_server import create_app


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "WM"
    data = root / "data"
    (data / "maszyny").mkdir(parents=True)
    (data / "zlecenia").mkdir(parents=True)
    (data / "produkty").mkdir(parents=True)
    (data / "produkty" / "PRD001.json").write_text(
        json.dumps({"kod": "PRD001", "nazwa": "Produkt"}),
        encoding="utf-8",
    )
    (data / "zlecenia" / "000001.json").write_text(
        json.dumps(
            {
                "id": "000001",
                "produkt": "PRD001",
                "ilosc": 5,
                "status": "nowe",
                "zlec_wew": "1001",
            }
        ),
        encoding="utf-8",
    )
    (data / "maszyny" / "maszyny.json").write_text(
        json.dumps(
            {
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
        ),
        encoding="utf-8",
    )
    return root


def _client(tmp_path):
    root = _root(tmp_path)
    app = create_app(root_provider=lambda: str(root), token_provider=lambda: "test-token")
    app.config.update(TESTING=True)
    return app.test_client(), root


def _headers():
    return {"X-Cidex-Token": "test-token"}


def test_health_does_not_require_token(tmp_path):
    client, _root_path = _client(tmp_path)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["service"] == "CIDEX"


def test_api_requires_token(tmp_path):
    client, _root_path = _client(tmp_path)
    response = client.get("/api/v1/machines")
    assert response.status_code == 401


def test_machine_can_be_resolved_from_qr(tmp_path):
    client, _root_path = _client(tmp_path)
    response = client.get(
        "/api/v1/qr/resolve?code=CIDEX:MACHINE:42",
        headers=_headers(),
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["type"] == "machine"
    assert payload["item"]["id"] == "42"


def test_mobile_can_report_failure_and_add_photo(tmp_path):
    client, root = _client(tmp_path)
    response = client.post(
        "/api/v1/machines/42/status",
        headers=_headers(),
        json={"status": "Awaria", "note": "Brak napędu"},
    )
    assert response.status_code == 200
    assert response.get_json()["item"]["status_label"] == "Awaria"

    response = client.post(
        "/api/v1/machines/42/photos",
        headers=_headers(),
        data={"photo": (BytesIO(b"image"), "awaria.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    item = response.get_json()["item"]
    assert len(item["photos"]) == 1

    attachments = root / "data" / "maszyny" / "attachments" / "42"
    assert attachments.is_dir()
    assert list(attachments.rglob("*.jpg"))


def test_planista_read_endpoint_uses_current_wm_root(tmp_path):
    client, _root_path = _client(tmp_path)
    response = client.get("/api/v1/planista/orders", headers=_headers())
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["items"][0]["zlec_wew"] == "1001"
