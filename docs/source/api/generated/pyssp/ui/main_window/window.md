# `pyssp/ui/main_window/window.py`

- Source: `pyssp/ui/main_window/window.py`
- Module path: `pyssp.ui.main_window.window`
- API entries: `3`

## Module Docstring

No module docstring.

## Functions

### Internal

- `_stop_qthread_safely(thread: Optional[QThread], timeout_ms: int = 1500) -> None` [function] (pyssp/ui/main_window/window.py:23)
- `_shutdown_executor_safely(executor) -> None` [function] (pyssp/ui/main_window/window.py:39)

## Classes

### `MainWindow`

- Defined at `pyssp/ui/main_window/window.py:48`
- Bases: UiBuildMixin, TimecodeMixin, VideoDisplayMixin, SettingsArchiveMixin, ToolsLibraryMixin, PagesSlotsMixin, PlaybackMixin, LyricsStageMixin, CompanionSatelliteMixin, RemoteApiMixin, ActionsInputMixin, LockingMixin, QMainWindow

#### Public Members

- `close(self) -> bool` [method] (pyssp/ui/main_window/window.py:1260)

#### Internal Members

- `__init__(self, *, show_getting_started_on_startup: bool = False) -> None` [constructor] (pyssp/ui/main_window/window.py:63)
- `_shutdown_runtime_threads(self) -> None` [method] (pyssp/ui/main_window/window.py:1198)
