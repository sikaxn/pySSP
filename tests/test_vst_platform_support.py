import os

from pyssp import settings_store, vst


def test_is_vst_supported_on_macos(monkeypatch):
    monkeypatch.setattr(vst.sys, "platform", "darwin")
    assert vst.is_vst_supported() is True


def test_default_vst_directories_include_macos_au_paths(monkeypatch):
    monkeypatch.setattr(settings_store.sys, "platform", "darwin")
    monkeypatch.setattr(settings_store.os, "name", "posix")

    directories = settings_store.default_vst_directories()

    assert "/Library/Audio/Plug-Ins/VST3" in directories
    assert "/Library/Audio/Plug-Ins/VST" in directories
    assert "/Library/Audio/Plug-Ins/Components" in directories
    assert os.path.expanduser("~/Library/Audio/Plug-Ins/VST3") in directories
    assert os.path.expanduser("~/Library/Audio/Plug-Ins/VST") in directories
    assert os.path.expanduser("~/Library/Audio/Plug-Ins/Components") in directories


def test_scan_falls_back_to_default_dirs_when_configured_dirs_missing(monkeypatch, tmp_path):
    plugin_root = tmp_path / "defaults"
    plugin_root.mkdir(parents=True, exist_ok=True)
    plugin_bundle = plugin_root / "Fallback.vst3"
    plugin_bundle.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(vst, "is_vst_supported", lambda: True)
    monkeypatch.setattr(vst, "default_vst_directories", lambda: [str(plugin_root)])
    monkeypatch.setattr(vst, "_discover_single_file", lambda path: [vst.make_plugin_ref(path, "Fallback")])

    scanned = vst.scan_vst_plugins(["/path/that/does/not/exist"])
    assert vst.make_plugin_ref(str(plugin_bundle), "Fallback") in scanned


def test_scan_accepts_plugin_bundle_path_directly(monkeypatch, tmp_path):
    plugin_bundle = tmp_path / "MyUnit.component"
    plugin_bundle.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(vst, "is_vst_supported", lambda: True)
    monkeypatch.setattr(vst, "default_vst_directories", lambda: [])
    monkeypatch.setattr(vst, "_discover_single_file", lambda path: [vst.make_plugin_ref(path, "MyUnit")])

    scanned = vst.scan_vst_plugins([str(plugin_bundle)])
    assert scanned == [vst.make_plugin_ref(str(plugin_bundle), "MyUnit")]


def test_scan_includes_defaults_even_when_custom_dirs_exist(monkeypatch, tmp_path):
    custom_root = tmp_path / "custom"
    custom_root.mkdir(parents=True, exist_ok=True)
    custom_plugin = custom_root / "Custom.vst3"
    custom_plugin.mkdir(parents=True, exist_ok=True)

    default_root = tmp_path / "default"
    default_root.mkdir(parents=True, exist_ok=True)
    default_plugin = default_root / "Default.component"
    default_plugin.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(vst, "is_vst_supported", lambda: True)
    monkeypatch.setattr(vst, "default_vst_directories", lambda: [str(default_root)])
    monkeypatch.setattr(
        vst,
        "_discover_single_file",
        lambda path: [vst.make_plugin_ref(path, os.path.splitext(os.path.basename(path))[0])],
    )

    scanned = vst.scan_vst_plugins([str(custom_root)])
    assert vst.make_plugin_ref(str(custom_plugin), "Custom") in scanned
    assert vst.make_plugin_ref(str(default_plugin), "Default") in scanned
