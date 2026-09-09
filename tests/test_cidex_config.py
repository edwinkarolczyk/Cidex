import json

import cidex_config


def test_api_token_is_six_safe_characters(tmp_path, monkeypatch):
    app_dir = tmp_path / "Cidex"
    config_path = app_dir / "config.json"
    monkeypatch.setattr(cidex_config, "APP_DIR", app_dir)
    monkeypatch.setattr(cidex_config, "CONFIG_PATH", config_path)

    token = cidex_config.get_api_token()

    assert len(token) == 6
    assert all(ch in cidex_config.API_TOKEN_ALPHABET for ch in token)
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["api_token"] == token


def test_old_long_token_is_migrated_to_six_characters(tmp_path, monkeypatch):
    app_dir = tmp_path / "Cidex"
    app_dir.mkdir()
    config_path = app_dir / "config.json"
    config_path.write_text(
        json.dumps({"api_token": "stary-bardzo-dlugi-token"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(cidex_config, "APP_DIR", app_dir)
    monkeypatch.setattr(cidex_config, "CONFIG_PATH", config_path)

    token = cidex_config.get_api_token()

    assert len(token) == 6
    assert token != "stary-bardzo-dlugi-token"
