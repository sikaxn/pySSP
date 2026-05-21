from __future__ import annotations

import os
import platform
import time
from pathlib import Path

from pyssp.runtime_logging import RuntimeLogManager, append_playback_log_entry, get_playback_log_path, get_runtime_log_dir
from pyssp.version import get_display_build_id, get_display_version


def test_append_playback_log_entry_writes_to_new_pyssp_log_file(monkeypatch, tmp_path):
    settings_path = tmp_path / "pySSP" / "settings.ini"
    monkeypatch.setattr("pyssp.settings_store.get_settings_path", lambda: settings_path)

    append_playback_log_entry(True, "pySSP started")

    log_path = get_playback_log_path()
    assert log_path.name == "pySSPLogFile.txt"
    assert log_path.exists() is True
    assert "pySSP started" in log_path.read_text(encoding="utf-8")


def test_runtime_log_prune_removes_oldest_completed_runs(monkeypatch, tmp_path):
    settings_path = tmp_path / "pySSP" / "settings.ini"
    monkeypatch.setattr("pyssp.settings_store.get_settings_path", lambda: settings_path)

    log_dir = get_runtime_log_dir()
    oldest = log_dir / "oldest.log"
    middle = log_dir / "middle.log"
    newest = log_dir / "newest.log"
    current = log_dir / "current.log"
    oldest.write_text("a" * 10, encoding="utf-8")
    middle.write_text("b" * 10, encoding="utf-8")
    newest.write_text("c" * 10, encoding="utf-8")
    current.write_text("d" * 10, encoding="utf-8")
    now = time.time()
    os.utime(oldest, (now - 30, now - 30))
    os.utime(middle, (now - 20, now - 20))
    os.utime(newest, (now - 10, now - 10))
    os.utime(current, (now, now))

    manager = RuntimeLogManager(limit_mb=16)
    manager.log_dir = log_dir
    manager.log_path = current
    manager.limit_bytes = 25
    manager.prune_runtime_logs()

    assert oldest.exists() is False
    assert middle.exists() is False
    assert newest.exists() is True
    assert current.exists() is True


def test_runtime_log_manager_captures_stream_lines(monkeypatch, tmp_path):
    settings_path = tmp_path / "pySSP" / "settings.ini"
    monkeypatch.setattr("pyssp.settings_store.get_settings_path", lambda: settings_path)

    manager = RuntimeLogManager(limit_mb=16)
    assert manager.start() is True
    try:
        manager.capture_stream_text("stdout", "hello runtime log\n")
        manager.capture_stream_text("stderr", "oops\n")
        manager.flush_stream("stdout")
        manager.flush_stream("stderr")
    finally:
        manager.stop()

    content = Path(manager.log_path).read_text(encoding="utf-8")
    assert f"pySSP version: {get_display_version()}" in content
    assert f"pySSP build: {get_display_build_id() or '(none)'}" in content
    assert f"Platform: {platform.platform()}" in content
    assert "[stdout] hello runtime log" in content
    assert "[stderr] oops" in content
