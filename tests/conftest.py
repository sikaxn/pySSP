from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_settings_ini(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    settings_path = tmp_path / "settings.ini"
    monkeypatch.setattr("pyssp.settings_store.get_settings_path", lambda: settings_path)
