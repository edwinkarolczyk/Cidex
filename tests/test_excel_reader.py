from pathlib import Path

from openpyxl import Workbook

from excel_reader import read_excel


def test_reader_maps_common_polish_headers(tmp_path: Path):
    path = tmp_path / "plan.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Nr zlec.", "Produkt", "Ilość", "Data wysyłki", "Proces"])
    ws.append(["123", "PRD001", 10, "2026-09-15", "Cięcie"])
    wb.save(path)

    payload = read_excel(path)
    assert payload["rows"][0]["nr_zlec"] == "123"
    assert payload["rows"][0]["produkt_input"] == "PRD001"
    assert payload["rows"][0]["ilosc"] == 10
