from __future__ import annotations

from excel_diff import ACTION_CREATE, ACTION_UPDATE, source_meta
from wm_store import add_order, update_order


def apply_selected(root, payload: dict, plan: dict, selected_identities: set[str]) -> list[dict]:
    results = []
    for item in plan.get("items") or []:
        identity = str(item.get("identity") or "")
        if not identity or identity not in selected_identities:
            continue
        action = item.get("action")
        try:
            if action == ACTION_CREATE:
                order = add_order(
                    root,
                    product_code=item.get("wm_symbol"),
                    quantity=item.get("ilosc_excel"),
                    external_no=item.get("nr_zlec"),
                    due_date=item.get("termin_excel"),
                    notes="Import Excel przez Cidex",
                    excel_meta=source_meta(payload, item),
                )
                results.append({"identity": identity, "action": action, "status": "OK", "order_id": order.get("id")})
            elif action == ACTION_UPDATE:
                order = update_order(
                    root,
                    item.get("order_id"),
                    quantity=item.get("ilosc_excel"),
                    due_date=item.get("termin_excel"),
                    external_no=item.get("nr_zlec"),
                    excel_meta=source_meta(payload, item),
                )
                results.append({"identity": identity, "action": action, "status": "OK", "order_id": order.get("id")})
        except Exception as exc:
            results.append({"identity": identity, "action": action, "status": "BŁĄD", "error": str(exc)})
    return results
