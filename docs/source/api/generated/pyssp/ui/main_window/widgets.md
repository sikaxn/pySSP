# `pyssp/ui/main_window/widgets.py`

- Source: `pyssp/ui/main_window/widgets.py`
- Module path: `pyssp.ui.main_window.widgets`
- API entries: `19`

## Module Docstring

No module docstring.

## Constants

### Public

- `SOUND_BUTTON_LIST_COLUMN_KEYS` [constant] (pyssp/ui/main_window/widgets.py:38)
  Detail: Value: ['ram', 'index', 'title', 'notes', 'status', 'edit', 'cue', 'lyric', 'automat...
- `SOUND_BUTTON_LIST_COLUMN_LABELS` [constant] (pyssp/ui/main_window/widgets.py:51)
  Detail: Value: {'ram': 'RAM', 'index': '#', 'title': 'Title', 'notes': 'Notes', 'status': 'S...

## Classes

### `SoundButtonData`

- Defined at `pyssp/ui/main_window/widgets.py:66`

#### Public Members

- `assigned(self) -> bool` [property] (pyssp/ui/main_window/widgets.py:97)
- `missing(self) -> bool` [property] (pyssp/ui/main_window/widgets.py:105)
- `display_text(self) -> str` [method] (pyssp/ui/main_window/widgets.py:112)

### `SoundButton`

- Defined at `pyssp/ui/main_window/widgets.py:132`
- Bases: QPushButton

#### Public Members

- `mousePressEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:146)
- `mouseMoveEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:151)
- `contextMenuEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:163)
- `dragEnterEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:167)
- `dragMoveEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:176)
- `dragLeaveEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:185)
- `dropEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:189)
- `enterEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:204)
- `leaveEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:208)
- `set_ram_loaded(self, loaded: bool) -> None` [method] (pyssp/ui/main_window/widgets.py:212)
- `set_indicator_colors(self, top_color: Optional[str], bottom_colors: List[str]) -> None` [method] (pyssp/ui/main_window/widgets.py:219)
- `paintEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:228)

#### Internal Members

- `__init__(self, slot_index: int, host: 'MainWindow')` [constructor] (pyssp/ui/main_window/widgets.py:133)

### `_SoundButtonListColumnsMixin`

- Defined at `pyssp/ui/main_window/widgets.py:268`

#### Internal Members

- `_column_width(self, widths: Dict[str, int], key: str, fallback: int) -> int` [method] (pyssp/ui/main_window/widgets.py:269)

### `SoundButtonListHeaderRow`

- Defined at `pyssp/ui/main_window/widgets.py:276`
- Bases: QFrame, _SoundButtonListColumnsMixin

#### Public Members

- `apply_column_widths(self, widths: Dict[str, int], hidden_columns: set[str]) -> None` [method] (pyssp/ui/main_window/widgets.py:303)
- `mousePressEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:320)
- `mouseMoveEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:332)
- `mouseReleaseEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:342)
- `leaveEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:353)
- `contextMenuEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:358)

#### Internal Members

- `__init__(self, host: 'MainWindow')` [constructor] (pyssp/ui/main_window/widgets.py:277)
- `_resize_candidate_key(self, pos: QPoint) -> Optional[str]` [method] (pyssp/ui/main_window/widgets.py:309)

### `SoundButtonListRow`

- Defined at `pyssp/ui/main_window/widgets.py:363`
- Bases: QFrame, _SoundButtonListColumnsMixin

#### Public Members

- `apply_column_widths(self, widths: Dict[str, int], hidden_columns: set[str]) -> None` [method] (pyssp/ui/main_window/widgets.py:468)
- `sync_slot(self, slot_index: int, slot: SoundButtonData, *, selected: bool, playing: bool) -> None` [method] (pyssp/ui/main_window/widgets.py:512)
- `mousePressEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:649)
- `mouseMoveEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:655)
- `mouseReleaseEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:667)
- `contextMenuEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:673)
- `dragEnterEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:677)
- `dragMoveEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:684)
- `dragLeaveEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:691)
- `dropEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:695)
- `enterEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:707)
- `leaveEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:711)

#### Internal Members

- `__init__(self, slot_index: int, host: 'MainWindow')` [constructor] (pyssp/ui/main_window/widgets.py:364)
- `_apply_elided_texts(self) -> None` [method] (pyssp/ui/main_window/widgets.py:484)
- `_set_bottom_indicator_colors(self, colors: List[str]) -> None` [method] (pyssp/ui/main_window/widgets.py:495)

### `NowPlayingLabel`

- Defined at `pyssp/ui/main_window/widgets.py:716`
- Bases: QWidget

#### Public Members

- `set_now_playing_text(self, prefix: str, value: str) -> None` [method] (pyssp/ui/main_window/widgets.py:746)
- `set_now_playing_html(self, prefix: str, value_html: str) -> None` [method] (pyssp/ui/main_window/widgets.py:752)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None)` [constructor] (pyssp/ui/main_window/widgets.py:717)
- `_to_wrapped_html(value: str) -> str` [staticmethod] (pyssp/ui/main_window/widgets.py:759)
- `_refresh_text(self) -> None` [method] (pyssp/ui/main_window/widgets.py:766)

### `GroupButton`

- Defined at `pyssp/ui/main_window/widgets.py:774`
- Bases: QPushButton

#### Public Members

- `dragEnterEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:781)
- `dragMoveEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:790)

#### Internal Members

- `__init__(self, group: str, host: 'MainWindow')` [constructor] (pyssp/ui/main_window/widgets.py:775)

### `ToolListWindow`

- Defined at `pyssp/ui/main_window/widgets.py:799`
- Bases: QDialog

#### Public Members

- `set_handlers(self, goto_handler: Callable[[dict], None], play_handler: Optional[Callable[[dict], None]], export_handler: Callable[[str], None], print_handler: Callable[[], None]) -> None` [method] (pyssp/ui/main_window/widgets.py:874)
- `enable_order_controls(self, options: List[str], refresh_handler: Callable[[str], None]) -> None` [method] (pyssp/ui/main_window/widgets.py:886)
- `current_order(self) -> str` [method] (pyssp/ui/main_window/widgets.py:895)
- `set_items(self, lines: List[str], matches: Optional[List[Optional[dict]]] = None, status: str = '') -> None` [method] (pyssp/ui/main_window/widgets.py:898)
- `set_note(self, text: str) -> None` [method] (pyssp/ui/main_window/widgets.py:907)
- `go_to_selected(self) -> None` [method] (pyssp/ui/main_window/widgets.py:912)
- `play_selected(self) -> None` [method] (pyssp/ui/main_window/widgets.py:920)

#### Internal Members

- `__init__(self, title: str, parent = None, double_click_action: str = 'goto', show_play_button: bool = True) -> None` [constructor] (pyssp/ui/main_window/widgets.py:800)
- `_export(self, export_format: str) -> None` [method] (pyssp/ui/main_window/widgets.py:928)
- `_print(self) -> None` [method] (pyssp/ui/main_window/widgets.py:933)
- `_refresh_from_order(self, _value: str = '') -> None` [method] (pyssp/ui/main_window/widgets.py:938)
- `_on_item_activated(self, _item) -> None` [method] (pyssp/ui/main_window/widgets.py:943)
- `_selected_match(self) -> Optional[dict]` [method] (pyssp/ui/main_window/widgets.py:949)

### `AboutWindowDialog`

- Defined at `pyssp/ui/main_window/widgets.py:959`
- Bases: QDialog

#### Public Members

- `resizeEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:1044)
- `set_content(self, about_text: str, credits_text: str, license_text: str) -> None` [method] (pyssp/ui/main_window/widgets.py:1048)
- `set_version_and_website(self, version_text: str, website_url: str, build_text: str = '') -> None` [method] (pyssp/ui/main_window/widgets.py:1053)

#### Internal Members

- `__init__(self, title: str, logo_path: str, version_text: str = '', website_url: str = '', parent = None) -> None` [constructor] (pyssp/ui/main_window/widgets.py:960)
- `_build_tab_textbox(self, no_wrap: bool = False) -> QPlainTextEdit` [method] (pyssp/ui/main_window/widgets.py:1026)
- `_refresh_cover_pixmap(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1032)

### `TimecodePanel`

- Defined at `pyssp/ui/main_window/widgets.py:1078`
- Bases: QWidget

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/main_window/widgets.py:1079)

### `DbfsMeterScale`

- Defined at `pyssp/ui/main_window/widgets.py:1115`
- Bases: QWidget

#### Public Members

- `paintEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:1129)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/main_window/widgets.py:1118)
- `_db_to_ratio(db_value: int) -> float` [staticmethod] (pyssp/ui/main_window/widgets.py:1125)

### `DbfsMeter`

- Defined at `pyssp/ui/main_window/widgets.py:1150`
- Bases: QWidget

#### Public Members

- `setLevel(self, level: float) -> None` [method] (pyssp/ui/main_window/widgets.py:1170)
- `paintEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:1177)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/main_window/widgets.py:1151)
- `_db_to_ratio(db_value: float) -> float` [staticmethod] (pyssp/ui/main_window/widgets.py:1159)
- `_level_to_ratio(level: float) -> float` [staticmethod] (pyssp/ui/main_window/widgets.py:1164)

### `StageDisplayWindow`

- Defined at `pyssp/ui/main_window/widgets.py:1222`
- Bases: QWidget

#### Public Members

- `configure_layout(self, order: List[str], visibility: Dict[str, bool]) -> None` [method] (pyssp/ui/main_window/widgets.py:1365)
- `update_values(self, total_time: str, elapsed: str, remaining: str, progress_percent: int, song_name: str, next_song: str, progress_text: str = '', progress_style: str = '') -> None` [method] (pyssp/ui/main_window/widgets.py:1374)
- `mouseDoubleClickEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:1409)
- `keyPressEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:1419)
- `resizeEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:1438)
- `set_playback_status(self, state: str) -> None` [method] (pyssp/ui/main_window/widgets.py:1497)
- `retranslate_ui(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1519)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/main_window/widgets.py:1232)
- `_apply_layout(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1426)
- `_update_datetime(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1435)
- `_apply_responsive_sizes(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1442)
- `_apply_song_text_fit(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1532)

### `NoAudioPlayer`

- Defined at `pyssp/ui/main_window/widgets.py:1568`
- Bases: QObject

#### Public Members

- `setNotifyInterval(self, interval_ms: int) -> None` [method] (pyssp/ui/main_window/widgets.py:1585)
- `setMedia(self, file_path: str, dsp_config: Optional[DSPConfig] = None) -> None` [method] (pyssp/ui/main_window/widgets.py:1588)
- `setDSPConfig(self, dsp_config: DSPConfig) -> None` [method] (pyssp/ui/main_window/widgets.py:1595)
- `play(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1598)
- `pause(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1602)
- `stop(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1606)
- `state(self) -> int` [method] (pyssp/ui/main_window/widgets.py:1612)
- `setPosition(self, position_ms: int) -> None` [method] (pyssp/ui/main_window/widgets.py:1615)
- `position(self) -> int` [method] (pyssp/ui/main_window/widgets.py:1619)
- `duration(self) -> int` [method] (pyssp/ui/main_window/widgets.py:1622)
- `setVolume(self, volume: int) -> None` [method] (pyssp/ui/main_window/widgets.py:1625)
- `volume(self) -> int` [method] (pyssp/ui/main_window/widgets.py:1628)
- `setMasterVolume(self, volume: int) -> None` [method] (pyssp/ui/main_window/widgets.py:1631)
- `masterVolume(self) -> int` [method] (pyssp/ui/main_window/widgets.py:1634)
- `meterLevels(self) -> Tuple[float, float]` [method] (pyssp/ui/main_window/widgets.py:1637)
- `sampleRate(self) -> int` [method] (pyssp/ui/main_window/widgets.py:1640)
- `outputBlockSize(self) -> int` [method] (pyssp/ui/main_window/widgets.py:1643)
- `outputTapFrameCounts(self) -> Dict[str, int]` [method] (pyssp/ui/main_window/widgets.py:1646)
- `waveformPeaks(self, sample_count: int = 1024) -> List[float]` [method] (pyssp/ui/main_window/widgets.py:1649)

#### Internal Members

- `__init__(self, parent: Optional[QObject] = None) -> None` [constructor] (pyssp/ui/main_window/widgets.py:1577)

### `TransportProgressDisplay`

- Defined at `pyssp/ui/main_window/widgets.py:1654`
- Bases: QLabel

#### Public Members

- `set_display_mode(self, mode: str) -> None` [method] (pyssp/ui/main_window/widgets.py:1664)
- `display_mode(self) -> str` [method] (pyssp/ui/main_window/widgets.py:1673)
- `set_waveform(self, peaks: List[float]) -> None` [method] (pyssp/ui/main_window/widgets.py:1676)
- `set_transport_state(self, progress_ratio: float, cue_in_ratio: float, cue_out_ratio: float, audio_file_mode: bool) -> None` [method] (pyssp/ui/main_window/widgets.py:1688)
- `paintEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:1706)

#### Internal Members

- `__init__(self, text: str = '', parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/main_window/widgets.py:1655)

### `MainThreadExecutor`

- Defined at `pyssp/ui/main_window/widgets.py:1797`
- Bases: QObject

#### Public Members

- `call(self, fn, timeout: float = 8.0)` [method] (pyssp/ui/main_window/widgets.py:1811)

#### Internal Members

- `__init__(self, parent: Optional[QObject] = None) -> None` [constructor] (pyssp/ui/main_window/widgets.py:1800)
- `_on_execute(self, fn, result_queue) -> None` [method] (pyssp/ui/main_window/widgets.py:1805)

### `LockScreenOverlay`

- Defined at `pyssp/ui/main_window/widgets.py:1822`
- Bases: QWidget

#### Public Members

- `activate_lock(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1841)
- `deactivate_lock(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1850)
- `reset_unlock_progress(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1855)
- `sync_geometry(self, rebuild_targets: bool = False) -> None` [method] (pyssp/ui/main_window/widgets.py:1862)
- `mousePressEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:1937)
- `mouseMoveEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:1966)
- `mouseReleaseEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:1978)
- `keyPressEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:1995)
- `keyReleaseEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:1999)
- `paintEvent(self, event) -> None` [method] (pyssp/ui/main_window/widgets.py:2003)

#### Internal Members

- `__init__(self, host: 'MainWindow') -> None` [constructor] (pyssp/ui/main_window/widgets.py:1825)
- `_rebuild_unlock_geometry(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1870)
- `_rebuild_targets(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1878)
- `_rebuild_fixed_button(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1909)
- `_rebuild_slide_unlock(self) -> None` [method] (pyssp/ui/main_window/widgets.py:1922)
- `_slide_handle_rect(self) -> QRect` [method] (pyssp/ui/main_window/widgets.py:2097)
