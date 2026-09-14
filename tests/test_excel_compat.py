from __future__ import annotations

import re
import zipfile
from pathlib import Path

from openpyxl import Workbook

from excel_compat import install_plan_monitor_excel_fix
from plan_monitor import parse_plan


def _make_unsized_xlsx(path: Path) -> None:
    source = path.with_name("source.xlsx")
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Nr zlecenia", "Produkt", "Ilość", "Termin", "Proces"])
    worksheet.append(["10", "DETAL-X", 2, "2026-09-20", "Cięcie"])
    workbook.save(source)
    workbook.close()

    with zipfile.ZipFile(source, "r") as input_zip:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as output_zip:
            for item in input_zip.infolist():
                data = input_zip.read(item.filename)
                if item.filename == "xl/worksheets/sheet1.xml":
                    text = data.decode("utf-8")
                    text = re.sub(r"<dimension[^>]*/>", "", text)
                    data = text.encode("utf-8")
                output_zip.writestr(item, data)


def test_parse_plan_handles_worksheet_without_dimension_metadata(tmp_path: Path):
    path = tmp_path / "unsized.xlsx"
    _make_unsized_xlsx(path)

    install_plan_monitor_excel_fix()
    parsed = parse_plan(path)

    assert len(parsed.rows) == 1
    assert parsed.rows[0]["order"] == "10"
    assert parsed.rows[0]["symbol"] == "DETAL-X"
    assert parsed.rows[0]["quantity"] == 2
