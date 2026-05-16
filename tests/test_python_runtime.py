from __future__ import annotations

from pathlib import Path

from pyssp.python_runtime import preferred_python_executable


def test_preferred_python_executable_prefers_prefix_launcher(monkeypatch, tmp_path):
    prefix = tmp_path / "venv"
    scripts = prefix / "Scripts"
    scripts.mkdir(parents=True)
    launcher = scripts / "python.exe"
    launcher.write_text("", encoding="utf-8")

    monkeypatch.setattr("pyssp.python_runtime.sys.prefix", str(prefix))
    monkeypatch.setattr("pyssp.python_runtime.sys.executable", str(tmp_path / "base-python.exe"))
    monkeypatch.setattr("pyssp.python_runtime.sys.frozen", False, raising=False)
    monkeypatch.setattr("pyssp.python_runtime.os.name", "nt")

    assert preferred_python_executable() == str(launcher.resolve())


def test_preferred_python_executable_falls_back_to_current_executable(monkeypatch, tmp_path):
    exe = tmp_path / "python.exe"
    exe.write_text("", encoding="utf-8")

    monkeypatch.setattr("pyssp.python_runtime.sys.prefix", str(tmp_path / "missing-venv"))
    monkeypatch.setattr("pyssp.python_runtime.sys.executable", str(exe))
    monkeypatch.setattr("pyssp.python_runtime.sys.frozen", False, raising=False)

    assert preferred_python_executable() == str(exe.resolve())
