from __future__ import annotations

import importlib

from pyssp import ndi_support


def test_probe_ndi_capability_reports_missing_binding(monkeypatch):
    monkeypatch.setattr(ndi_support.importlib.metadata, "version", lambda _name: (_ for _ in ()).throw(importlib.metadata.PackageNotFoundError()))
    monkeypatch.setattr(ndi_support.importlib, "import_module", lambda _name: (_ for _ in ()).throw(ImportError("missing")))
    monkeypatch.setattr(ndi_support, "_runtime_candidates", lambda: ("", []))
    monkeypatch.setattr(ndi_support, "_sdk_candidates", lambda: [])
    monkeypatch.setattr(ndi_support, "_env_dir", lambda _name: "")

    status = ndi_support.probe_ndi_capability(force_refresh=True)

    assert status.ndi_python_available is False
    assert status.ready is False
    assert "not installed" in status.availability_reason.lower()


def test_probe_ndi_capability_reports_missing_binding_even_when_sdk_exists(monkeypatch):
    monkeypatch.setattr(ndi_support.importlib.metadata, "version", lambda _name: (_ for _ in ()).throw(importlib.metadata.PackageNotFoundError()))
    monkeypatch.setattr(ndi_support.importlib, "import_module", lambda _name: (_ for _ in ()).throw(ImportError("missing")))
    monkeypatch.setattr(ndi_support, "_runtime_candidates", lambda: ("NDI_RUNTIME_DIR_V6", ["/opt/ndi"]))
    monkeypatch.setattr(ndi_support, "_sdk_candidates", lambda: ["/opt/ndi-sdk"])
    monkeypatch.setattr(ndi_support, "_existing_paths", lambda values: list(values))
    monkeypatch.setattr(ndi_support, "_env_dir", lambda _name: "/opt/ndi")

    status = ndi_support.probe_ndi_capability(force_refresh=True)

    assert status.ndi_runtime_or_sdk_detected is True
    assert status.ready is False
    assert "python binding is not installed" in status.availability_reason.lower()
    assert "sdk/runtime was detected" in status.availability_reason.lower()


def test_probe_ndi_capability_reports_runtime_missing(monkeypatch):
    monkeypatch.setattr(ndi_support.importlib.metadata, "version", lambda _name: "6.3.2.1")
    monkeypatch.setattr(ndi_support.importlib, "import_module", lambda _name: object())
    monkeypatch.setattr(ndi_support, "_runtime_candidates", lambda: ("NDI_RUNTIME_DIR_V6", []))
    monkeypatch.setattr(ndi_support, "_sdk_candidates", lambda: [])
    monkeypatch.setattr(ndi_support, "_env_dir", lambda _name: "")

    status = ndi_support.probe_ndi_capability(force_refresh=True)

    assert status.ndi_python_available is True
    assert status.ndi_module_importable is True
    assert status.ndi_runtime_or_sdk_detected is False
    assert status.ready is False
    assert "runtime/sdk was not detected" in status.availability_reason.lower()


def test_probe_ndi_capability_reports_ready(monkeypatch):
    monkeypatch.setattr(ndi_support.importlib.metadata, "version", lambda _name: "6.3.2.1")
    monkeypatch.setattr(ndi_support.importlib, "import_module", lambda _name: object())
    monkeypatch.setattr(ndi_support, "_runtime_candidates", lambda: ("NDI_RUNTIME_DIR_V6", ["/opt/ndi"]))
    monkeypatch.setattr(ndi_support, "_sdk_candidates", lambda: ["/opt/ndi-sdk"])
    monkeypatch.setattr(ndi_support, "_existing_paths", lambda values: list(values))
    monkeypatch.setattr(ndi_support, "_env_dir", lambda _name: "/opt/ndi")

    status = ndi_support.probe_ndi_capability(force_refresh=True)

    assert status.ready is True
    assert status.ndi_python_version == "6.3.2.1"
    assert status.runtime_paths == ["/opt/ndi"]
    assert status.sdk_paths == ["/opt/ndi-sdk"]
