from __future__ import annotations

from pyssp import ndi_support


def test_probe_ndi_capability_reports_missing_runtime(monkeypatch):
    monkeypatch.setattr(ndi_support, "_runtime_candidates", lambda: ("NDI_RUNTIME_DIR_V6", []))
    monkeypatch.setattr(ndi_support, "_sdk_candidates", lambda: [])
    monkeypatch.setattr(ndi_support, "_env_dir", lambda _name: "")

    status = ndi_support.probe_ndi_capability(force_refresh=True)

    assert status.ndi_runtime_or_sdk_detected is False
    assert status.ready is False
    assert "not detected" in status.availability_reason.lower()


def test_probe_ndi_capability_reports_sdk_without_library(monkeypatch):
    monkeypatch.setattr(ndi_support, "_runtime_candidates", lambda: ("NDI_RUNTIME_DIR_V6", ["/opt/ndi"]))
    monkeypatch.setattr(ndi_support, "_sdk_candidates", lambda: ["/opt/ndi-sdk"])
    monkeypatch.setattr(ndi_support, "_existing_paths", lambda values: list(values))
    monkeypatch.setattr(ndi_support, "_resolve_runtime_library_path", lambda runtime_paths, sdk_paths: "")
    monkeypatch.setattr(ndi_support, "_env_dir", lambda _name: "/opt/ndi")

    status = ndi_support.probe_ndi_capability(force_refresh=True)

    assert status.ndi_runtime_or_sdk_detected is True
    assert status.ready is False
    assert "library file was not found" in status.availability_reason.lower()


def test_probe_ndi_capability_reports_ready(monkeypatch):
    monkeypatch.setattr(ndi_support, "_runtime_candidates", lambda: ("NDI_RUNTIME_DIR_V6", ["/opt/ndi"]))
    monkeypatch.setattr(ndi_support, "_sdk_candidates", lambda: ["/opt/ndi-sdk"])
    monkeypatch.setattr(ndi_support, "_existing_paths", lambda values: list(values))
    monkeypatch.setattr(
        ndi_support,
        "_resolve_runtime_library_path",
        lambda runtime_paths, sdk_paths: "/opt/ndi/libndi.so.6",
    )
    monkeypatch.setattr(ndi_support, "probe_runtime_version", lambda _path: "6.3.1")
    monkeypatch.setattr(ndi_support, "_env_dir", lambda _name: "/opt/ndi")

    status = ndi_support.probe_ndi_capability(force_refresh=True)

    assert status.ready is True
    assert status.runtime_paths == ["/opt/ndi"]
    assert status.sdk_paths == ["/opt/ndi-sdk"]
    assert status.runtime_library_path == "/opt/ndi/libndi.so.6"
    assert status.ndi_runtime_version == "6.3.1"


def test_runtime_library_file_candidates_cover_windows_and_macos(monkeypatch):
    monkeypatch.setattr(ndi_support.platform, "system", lambda: "Windows")
    windows_candidates = ndi_support._runtime_library_file_candidates(r"C:\Program Files\NDI\NDI 6 SDK")
    assert any(
        candidate.replace("\\", "/").endswith("/Bin/x64/Processing.NDI.Lib.x64.dll")
        for candidate in windows_candidates
    )

    monkeypatch.setattr(ndi_support.platform, "system", lambda: "Darwin")
    mac_candidates = ndi_support._runtime_library_file_candidates("/Library/NDI SDK for Apple")
    assert any(candidate.replace("\\", "/").endswith("/lib/macOS/libndi.dylib") for candidate in mac_candidates)
    assert any(candidate.replace("\\", "/").endswith("/lib/macOS/libndi_advanced.dylib") for candidate in mac_candidates)


def test_probe_ndi_capability_reports_ready_for_macos_tool_bundle(monkeypatch):
    monkeypatch.setattr(ndi_support.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        ndi_support,
        "_runtime_candidates",
        lambda: (
            "NDI_RUNTIME_DIR_V6",
            ["/Applications/NDI Video Monitor.app/Contents/Frameworks"],
        ),
    )
    monkeypatch.setattr(ndi_support, "_sdk_candidates", lambda: [])
    monkeypatch.setattr(ndi_support, "_existing_paths", lambda values: list(values))
    monkeypatch.setattr(
        ndi_support,
        "_resolve_runtime_library_path",
        lambda runtime_paths, sdk_paths: "/Applications/NDI Video Monitor.app/Contents/Frameworks/libndi_advanced.dylib",
    )
    monkeypatch.setattr(ndi_support, "probe_runtime_version", lambda _path: "6.3.2.0")
    monkeypatch.setattr(ndi_support, "_env_dir", lambda _name: "")

    status = ndi_support.probe_ndi_capability(force_refresh=True)

    assert status.ready is True
    assert status.runtime_paths == ["/Applications/NDI Video Monitor.app/Contents/Frameworks"]
    assert status.runtime_library_path.endswith("/Applications/NDI Video Monitor.app/Contents/Frameworks/libndi_advanced.dylib")
    assert status.ndi_runtime_version == "6.3.2.0"
