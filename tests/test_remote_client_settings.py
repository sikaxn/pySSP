from pathlib import Path

from pyssp.remote_client_settings import (
    RemoteClientSettings,
    load_remote_client_settings,
    save_remote_client_settings,
)


def test_remote_client_settings_defaults_use_http_plus_one_for_ws_port():
    settings = RemoteClientSettings(server_http_port=5050)
    assert settings.server_ws_port == 5051


def test_remote_client_settings_round_trip(tmp_path: Path):
    settings_path = tmp_path / "remote-client.ini"
    original = RemoteClientSettings(
        server_host="192.168.1.50",
        server_http_port=6060,
        lyric_display_font_family="Arial",
        lyric_display_font_size=44,
        stage_display_open_on_startup=True,
        stage_display_font_size=30,
    )
    save_remote_client_settings(original, path=settings_path)
    loaded = load_remote_client_settings(path=settings_path)
    assert loaded.server_host == "192.168.1.50"
    assert loaded.server_http_port == 6060
    assert loaded.server_ws_port == 6061
    assert loaded.lyric_display_font_family == "Arial"
    assert loaded.lyric_display_font_size == 44
    assert loaded.stage_display_open_on_startup is True
    assert loaded.stage_display_font_size == 30
