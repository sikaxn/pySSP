# `pyssp/ui/getting_started_dialog.py`

- Source: `pyssp/ui/getting_started_dialog.py`
- Module path: `pyssp.ui.getting_started_dialog`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `GettingStartedDialog`

- Defined at `pyssp/ui/getting_started_dialog.py:22`
- Bases: QDialog

#### Public Members

- `set_language(self, language: str) -> None` [method] (pyssp/ui/getting_started_dialog.py:382)
- `reset_to_first_page(self) -> None` [method] (pyssp/ui/getting_started_dialog.py:463)
- `showEvent(self, event) -> None` [method] (pyssp/ui/getting_started_dialog.py:501)

#### Internal Members

- `__init__(self, *, language: str = 'en', version_text: str, build_text: str, beta_build: bool, splash_image_path: str = '', add_page_image_path: str = '', drag_file_image_path: str = '', ndi_status_text: str = '', ndi_runtime_download_url: str = '', open_audio_device_options: Optional[Callable[[], None]] = None, open_ndi_options: Optional[Callable[[], None]] = None, open_latest_version_page: Optional[Callable[[], None]] = None, open_docs_page: Optional[Callable[[], None]] = None, open_options_page: Optional[Callable[[], None]] = None, open_about_window: Optional[Callable[[], None]] = None, parent = None) -> None` [constructor] (pyssp/ui/getting_started_dialog.py:23)
- `_build_welcome_page(self, splash_image_path: str) -> QWidget` [method] (pyssp/ui/getting_started_dialog.py:119)
- `_build_beta_page(self) -> QWidget` [method] (pyssp/ui/getting_started_dialog.py:158)
- `_build_add_sound_page(self, add_page_image_path: str, drag_file_image_path: str) -> QWidget` [method] (pyssp/ui/getting_started_dialog.py:182)
- `_build_audio_device_page(self) -> QWidget` [method] (pyssp/ui/getting_started_dialog.py:217)
- `_build_finish_page(self) -> QWidget` [method] (pyssp/ui/getting_started_dialog.py:302)
- `_action_button(self, handler: Callable[[], None]) -> QPushButton` [method] (pyssp/ui/getting_started_dialog.py:331)
- `_card_widget(self) -> QFrame` [method] (pyssp/ui/getting_started_dialog.py:342)
- `_image_card(self, image_path: str) -> tuple[QLabel, QWidget]` [method] (pyssp/ui/getting_started_dialog.py:348)
- `_image_label(self, image_path: str, *, max_width: int, max_height: int) -> QLabel` [method] (pyssp/ui/getting_started_dialog.py:363)
- `_info_line(self) -> QLabel` [method] (pyssp/ui/getting_started_dialog.py:376)
- `_advance_page(self) -> None` [method] (pyssp/ui/getting_started_dialog.py:457)
- `_sync_buttons(self) -> None` [method] (pyssp/ui/getting_started_dialog.py:467)
- `_handle_open_audio_device_options(self) -> None` [method] (pyssp/ui/getting_started_dialog.py:477)
- `_handle_open_ndi_options(self) -> None` [method] (pyssp/ui/getting_started_dialog.py:481)
- `_handle_open_latest_version_page(self) -> None` [method] (pyssp/ui/getting_started_dialog.py:485)
- `_handle_open_docs_page(self) -> None` [method] (pyssp/ui/getting_started_dialog.py:489)
- `_handle_open_options_page(self) -> None` [method] (pyssp/ui/getting_started_dialog.py:493)
- `_handle_open_about_window(self) -> None` [method] (pyssp/ui/getting_started_dialog.py:497)
