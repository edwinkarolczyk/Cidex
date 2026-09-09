from __future__ import annotations

import argparse
from pathlib import Path
import socket
from typing import Callable

from flask import Flask, jsonify, request, send_file
from waitress import serve

from cidex_config import get_api_port, get_api_token, get_saved_root
from machine_store import (
    AUTHOR,
    MachineStoreError,
    add_note,
    add_photo,
    change_status,
    get_machine,
    list_machine_summaries,
    machine_summary,
    photo_paths,
    resolve_machine_qr,
)
from wm_store import WmStoreError, add_order, list_orders, list_products

API_VERSION = "1.2"
TOKEN_HEADER = "X-Cidex-Token"


def _local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def _public_machine(machine: dict) -> dict:
    result = machine_summary(machine)
    current = machine.get("status_current")
    if isinstance(current, dict):
        result["status_current"] = {
            "status": current.get("status", ""),
            "label": current.get("label", ""),
            "started_at": current.get("started_at", ""),
            "changed_by": current.get("changed_by", ""),
            "note": current.get("note", ""),
        }
    else:
        result["status_current"] = {}
    result["zadania"] = [
        dict(item)
        for item in machine.get("zadania") or []
        if isinstance(item, dict)
    ]
    result["photos"] = [
        {
            "index": index,
            "name": Path(path).name,
            "url": f"/api/v1/machines/{result['id']}/photos/{index}",
        }
        for index, path in enumerate(photo_paths(machine))
    ]
    return result


def create_app(
    *,
    root_provider: Callable[[], str] | None = None,
    token_provider: Callable[[], str] | None = None,
) -> Flask:
    root_provider = root_provider or get_saved_root
    token_provider = token_provider or get_api_token
    app = Flask("cidex_api")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    def root_value() -> str:
        value = str(root_provider() or "").strip()
        if not value:
            raise WmStoreError("WM_ROOT nie jest ustawiony w Cidex.")
        return value

    @app.before_request
    def require_token():
        if not request.path.startswith("/api/v1/"):
            return None
        expected = str(token_provider() or "").strip()
        supplied = str(request.headers.get(TOKEN_HEADER) or "").strip()
        if not supplied:
            auth = str(request.headers.get("Authorization") or "").strip()
            if auth.casefold().startswith("bearer "):
                supplied = auth[7:].strip()
        if not expected or supplied != expected:
            return jsonify({"ok": False, "error": "Brak lub błędny token CIDEX."}), 401
        return None

    @app.errorhandler(MachineStoreError)
    @app.errorhandler(WmStoreError)
    def known_error(exc):
        return jsonify({"ok": False, "error": str(exc)}), 400

    @app.errorhandler(413)
    def too_large(_exc):
        return jsonify({"ok": False, "error": "Plik jest za duży."}), 413

    @app.get("/health")
    def health():
        return jsonify(
            {
                "ok": True,
                "service": "CIDEX",
                "api_version": API_VERSION,
                "author": AUTHOR,
            }
        )

    @app.get("/api/v1/info")
    def info():
        root = root_value()
        return jsonify(
            {
                "ok": True,
                "api_version": API_VERSION,
                "wm_root_configured": bool(root),
                "author": AUTHOR,
                "features": {
                    "planista_read": True,
                    "planista_create": True,
                    "machines_read": True,
                    "machine_qr": True,
                    "machine_status": True,
                    "machine_notes": True,
                    "machine_photos": True,
                },
            }
        )

    @app.get("/api/v1/planista/orders")
    def planista_orders():
        rows = list_orders(root_value())
        return jsonify({"ok": True, "count": len(rows), "items": rows})

    @app.post("/api/v1/planista/orders")
    def planista_add_order():
        payload = request.get_json(silent=True) or {}
        order = add_order(
            root_value(),
            product_code=str(payload.get("product_code") or "").strip(),
            quantity=payload.get("quantity"),
            external_no=str(payload.get("external_no") or "").strip(),
            due_date=str(payload.get("due_date") or "").strip(),
            notes=str(payload.get("notes") or "").strip(),
        )
        return jsonify({"ok": True, "item": order}), 201

    @app.get("/api/v1/planista/products")
    def planista_products():
        rows = list_products(root_value())
        return jsonify({"ok": True, "count": len(rows), "items": rows})

    @app.get("/api/v1/machines")
    def machines():
        rows = list_machine_summaries(root_value())
        return jsonify({"ok": True, "count": len(rows), "items": rows})

    @app.get("/api/v1/machines/<machine_id>")
    def machine(machine_id: str):
        row = get_machine(root_value(), machine_id)
        return jsonify({"ok": True, "item": _public_machine(row)})

    @app.get("/api/v1/qr/resolve")
    def qr_resolve():
        code = request.args.get("code", "")
        row = resolve_machine_qr(root_value(), code)
        return jsonify({"ok": True, "type": "machine", "item": _public_machine(row)})

    @app.post("/api/v1/machines/<machine_id>/status")
    def machine_status(machine_id: str):
        payload = request.get_json(silent=True) or {}
        row = change_status(
            root_value(),
            machine_id,
            payload.get("status"),
            note=str(payload.get("note") or ""),
            actor=AUTHOR,
        )
        return jsonify({"ok": True, "item": _public_machine(row)})

    @app.post("/api/v1/machines/<machine_id>/note")
    def machine_note(machine_id: str):
        payload = request.get_json(silent=True) or {}
        row = add_note(
            root_value(),
            machine_id,
            str(payload.get("note") or ""),
            actor=AUTHOR,
        )
        return jsonify({"ok": True, "item": _public_machine(row)})

    @app.post("/api/v1/machines/<machine_id>/photos")
    def machine_photo(machine_id: str):
        upload = request.files.get("photo")
        if upload is None or not upload.filename:
            raise MachineStoreError("Brak zdjęcia w polu 'photo'.")
        content = upload.read()
        row, _saved_path = add_photo(
            root_value(),
            machine_id,
            content,
            upload.filename,
            actor=AUTHOR,
        )
        return jsonify({"ok": True, "item": _public_machine(row)}), 201

    @app.get("/api/v1/machines/<machine_id>/photos/<int:index>")
    def machine_photo_get(machine_id: str, index: int):
        root = root_value()
        row = get_machine(root, machine_id)
        paths = photo_paths(row)
        if index < 0 or index >= len(paths):
            return jsonify({"ok": False, "error": "Nie znaleziono zdjęcia."}), 404
        target = Path(paths[index]).expanduser()
        if not target.is_absolute():
            data_root = Path(root).expanduser().resolve()
            if data_root.name.casefold() != "data":
                data_root = data_root / "data"
            target = (data_root / target).resolve()
        else:
            target = target.resolve()
        data_root = Path(root).expanduser().resolve()
        if data_root.name.casefold() != "data":
            data_root = data_root / "data"
        allowed_root = (data_root / "maszyny").resolve()
        try:
            target.relative_to(allowed_root)
        except ValueError:
            return jsonify({"ok": False, "error": "Zdjęcie jest poza katalogiem Maszyn."}), 403
        if not target.is_file():
            return jsonify({"ok": False, "error": "Plik zdjęcia nie istnieje."}), 404
        return send_file(target)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="CIDEX API dla Cidex Mobile")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Adres nasłuchu. Domyślnie 0.0.0.0 dla sieci LAN.",
    )
    parser.add_argument("--port", type=int, default=get_api_port())
    args = parser.parse_args()

    root = get_saved_root()
    if not root:
        raise SystemExit("Najpierw ustaw WM_ROOT w Cidex.exe / run.bat.")
    token = get_api_token()
    print("=" * 56)
    print("CIDEX Mobile API")
    print(f"WM_ROOT: {root}")
    print(f"Emulator Android: http://10.0.2.2:{args.port}")
    print(f"Telefon w LAN:    http://{_local_ip()}:{args.port}")
    print(f"Token:            {token}")
    print("Autor zapisów:    Cidex")
    print("Zatrzymanie: Ctrl+C")
    print("=" * 56)
    serve(create_app(), host=args.host, port=args.port, threads=8)


if __name__ == "__main__":
    main()
