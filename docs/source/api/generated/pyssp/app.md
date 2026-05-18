# `pyssp/app.py`

- Source: `pyssp/app.py`
- Module path: `pyssp.app`
- API entries: `16`

## Module Docstring

No module docstring.

## Functions

### Public

- `main() -> int` [function] (pyssp/app.py:423)

### Internal

- `_force_light_qt_theme(app: QApplication) -> None` [function] (pyssp/app.py:37)
- `_parse_startup_args(argv: list[str]) -> tuple[list[str], bool, bool, bool]` [function] (pyssp/app.py:57)
- `_enable_debug_console(enabled: bool) -> None` [function] (pyssp/app.py:80)
- `_ensure_standard_streams(debug_enabled: bool) -> None` [function] (pyssp/app.py:101)
- `_install_crash_handler(app: QApplication) -> None` [function] (pyssp/app.py:125)
- `_apply_cleanstart() -> bool` [function] (pyssp/app.py:180)
- `_clear_waveform_cache_for_cleanstart() -> None` [function] (pyssp/app.py:198)
- `_acquire_single_instance_lock() -> bool` [function] (pyssp/app.py:220)
- `_is_process_running(image_name: str) -> bool` [function] (pyssp/app.py:237)
- `_confirm_sports_sounds_pro_warning() -> bool` [function] (pyssp/app.py:252)
- `_prompt_first_run_language() -> str` [function] (pyssp/app.py:269)
- `_confirm_cleanstart_warning() -> bool` [function] (pyssp/app.py:295)
- `_resolve_startup_language(preferred_if_missing: Optional[str] = None) -> str` [function] (pyssp/app.py:306)
- `_asset_path(*parts: str) -> Path` [function] (pyssp/app.py:317)

## Classes

### `_StartupSplash`

- Defined at `pyssp/app.py:333`
- Bases: QSplashScreen

#### Public Members

- `set_status(self, status_text: str) -> None` [method] (pyssp/app.py:347)
- `drawContents(self, painter: QPainter) -> None` [method] (pyssp/app.py:352)

#### Internal Members

- `__init__(self, pixmap: QPixmap, version_text: str, build_text: str = '') -> None` [constructor] (pyssp/app.py:336)
