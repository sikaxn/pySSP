# `pyssp/ui/system_info_dialog.py`

- Source: `pyssp/ui/system_info_dialog.py`
- Module path: `pyssp.ui.system_info_dialog`
- API entries: `19`

## Module Docstring

No module docstring.

## Functions

### Public

- `detect_supported_audio_format_extensions(timeout_sec: float = 10.0, register_process: Optional[Callable[[Optional[subprocess.Popen[str]]], None]] = None) -> List[str]` [function] (pyssp/ui/system_info_dialog.py:347)
- `build_system_information_text(app_version_text: str, app_build_text: str = '', register_probe_process: Optional[Callable[[Optional[subprocess.Popen[str]]], None]] = None, runtime_debug_info: Optional[dict] = None) -> str` [function] (pyssp/ui/system_info_dialog.py:439)

### Internal

- `_subprocess_platform_kwargs() -> dict` [function] (pyssp/ui/system_info_dialog.py:47)
- `_safe_package_version(name: str) -> str` [function] (pyssp/ui/system_info_dialog.py:61)
- `_safe_runtime_module_version(import_name: str, attributes: List[str], package_name: Optional[str] = None) -> str` [function] (pyssp/ui/system_info_dialog.py:68)
- `_safe_pyqt_version() -> str` [function] (pyssp/ui/system_info_dialog.py:85)
- `_get_library_versions() -> List[str]` [function] (pyssp/ui/system_info_dialog.py:100)
- `_run_command(args: List[str]) -> str` [function] (pyssp/ui/system_info_dialog.py:116)
- `_dedupe(values: List[str]) -> List[str]` [function] (pyssp/ui/system_info_dialog.py:134)
- `_parse_windows_ipconfig(raw: str) -> List[NetworkInterfaceInfo]` [function] (pyssp/ui/system_info_dialog.py:149)
- `_parse_unix_ifconfig(raw: str) -> List[NetworkInterfaceInfo]` [function] (pyssp/ui/system_info_dialog.py:188)
- `_fallback_network_info() -> List[NetworkInterfaceInfo]` [function] (pyssp/ui/system_info_dialog.py:230)
- `_get_network_interfaces() -> List[NetworkInterfaceInfo]` [function] (pyssp/ui/system_info_dialog.py:256)
- `_list_midi_outputs_cross_platform() -> List[str]` [function] (pyssp/ui/system_info_dialog.py:270)
- `_get_pygame_decoder_report(register_process: Optional[Callable[[Optional[subprocess.Popen[str]]], None]] = None, timeout_sec: float = 12.0) -> List[str]` [function] (pyssp/ui/system_info_dialog.py:296)
- `_get_current_running_config_report() -> List[str]` [function] (pyssp/ui/system_info_dialog.py:375)

## Classes

### `NetworkInterfaceInfo`

- Defined at `pyssp/ui/system_info_dialog.py:40`

### `_SystemInfoWorker`

- Defined at `pyssp/ui/system_info_dialog.py:557`
- Bases: QObject

#### Public Members

- `run(self) -> None` [method] (pyssp/ui/system_info_dialog.py:570)
- `cancel(self) -> None` [method] (pyssp/ui/system_info_dialog.py:592)

#### Internal Members

- `__init__(self, app_version_text: str, app_build_text: str = '', runtime_debug_info: Optional[dict] = None) -> None` [constructor] (pyssp/ui/system_info_dialog.py:562)
- `_set_probe_process(self, proc: Optional[subprocess.Popen[str]]) -> None` [method] (pyssp/ui/system_info_dialog.py:589)

### `SystemInformationDialog`

- Defined at `pyssp/ui/system_info_dialog.py:610`
- Bases: QDialog

#### Public Members

- `set_app_version_text(self, value: str) -> None` [method] (pyssp/ui/system_info_dialog.py:664)
- `set_app_build_text(self, value: str) -> None` [method] (pyssp/ui/system_info_dialog.py:667)
- `refresh(self) -> None` [method] (pyssp/ui/system_info_dialog.py:670)
- `closeEvent(self, event) -> None` [method] (pyssp/ui/system_info_dialog.py:715)

#### Internal Members

- `__init__(self, app_version_text: str, app_build_text: str = '', runtime_debug_provider: Optional[Callable[[], dict]] = None, parent = None) -> None` [constructor] (pyssp/ui/system_info_dialog.py:611)
- `_set_refresh_in_progress(self, active: bool) -> None` [method] (pyssp/ui/system_info_dialog.py:697)
- `_handle_refresh_finished(self, text: str) -> None` [method] (pyssp/ui/system_info_dialog.py:703)
- `_handle_refresh_failed(self, error: str) -> None` [method] (pyssp/ui/system_info_dialog.py:707)
- `_clear_refresh_thread(self) -> None` [method] (pyssp/ui/system_info_dialog.py:711)
- `_copy_text(self) -> None` [method] (pyssp/ui/system_info_dialog.py:734)
- `_export_text(self) -> None` [method] (pyssp/ui/system_info_dialog.py:739)
- `_export_settings_ini(self) -> None` [method] (pyssp/ui/system_info_dialog.py:758)
