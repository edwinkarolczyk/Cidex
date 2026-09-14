from pathlib import Path

import pytest

from excel_source_guard import parse_from_detached_copy


def test_parser_receives_detached_copy_and_copy_is_removed(tmp_path: Path) -> None:
    source = tmp_path / "plan.xlsx"
    source.write_bytes(b"excel-data")
    seen: dict[str, object] = {}

    def parser(path: str | Path, _config):
        detached = Path(path)
        seen["path"] = detached
        seen["content"] = detached.read_bytes()
        assert detached != source
        assert detached.exists()
        return "ok"

    assert parse_from_detached_copy(source, parser, {}) == "ok"
    assert seen["content"] == b"excel-data"
    assert source.read_bytes() == b"excel-data"
    assert not Path(seen["path"]).exists()


def test_detached_copy_is_removed_when_parser_fails(tmp_path: Path) -> None:
    source = tmp_path / "plan.xls"
    source.write_bytes(b"xls-data")
    seen: dict[str, Path] = {}

    def parser(path: str | Path, _config):
        seen["path"] = Path(path)
        raise RuntimeError("parse failed")

    with pytest.raises(RuntimeError, match="parse failed"):
        parse_from_detached_copy(source, parser, {})

    assert source.exists()
    assert not seen["path"].exists()
