# `pyssp/ui/waveform_view.py`

- Source: `pyssp/ui/waveform_view.py`
- Module path: `pyssp.ui.waveform_view`
- API entries: `2`

## Module Docstring

No module docstring.

## Classes

### `CueRangeIndicator`

- Defined at `pyssp/ui/waveform_view.py:13`
- Bases: QWidget

#### Public Members

- `sizeHint(self) -> QSize` [method] (pyssp/ui/waveform_view.py:25)
- `set_values(self, duration_ms: int, start_ms: Optional[int], end_ms: Optional[int]) -> None` [method] (pyssp/ui/waveform_view.py:28)
- `set_position(self, position_ms: int) -> None` [method] (pyssp/ui/waveform_view.py:34)
- `set_waveform(self, peaks: List[float]) -> None` [method] (pyssp/ui/waveform_view.py:38)
- `set_loading(self, loading: bool, text: str = 'Loading waveform...') -> None` [method] (pyssp/ui/waveform_view.py:50)
- `paintEvent(self, _event) -> None` [method] (pyssp/ui/waveform_view.py:61)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/waveform_view.py:14)
- `_x_for_ms(self, value_ms: int, width: int) -> int` [method] (pyssp/ui/waveform_view.py:55)

### `WaveformRefreshController`

- Defined at `pyssp/ui/waveform_view.py:141`
- Bases: QObject

#### Public Members

- `stop(self) -> None` [method] (pyssp/ui/waveform_view.py:164)
- `request(self, *, player: ExternalMediaPlayer, duration_ms: int) -> None` [method] (pyssp/ui/waveform_view.py:173)

#### Internal Members

- `__init__(self, *, on_peaks: Callable[[List[float]], None], is_valid: Optional[Callable[[], bool]] = None, sample_count: int = 1800, interval_ms: int = 50, parent: Optional[QObject] = None) -> None` [constructor] (pyssp/ui/waveform_view.py:142)
- `_submit(self, token: int) -> None` [method] (pyssp/ui/waveform_view.py:183)
- `_poll(self) -> None` [method] (pyssp/ui/waveform_view.py:197)
