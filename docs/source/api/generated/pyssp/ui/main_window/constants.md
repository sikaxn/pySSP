# `pyssp/ui/main_window/constants.py`

- Source: `pyssp/ui/main_window/constants.py`
- Module path: `pyssp.ui.main_window.constants`
- API entries: `12`

## Module Docstring

No module docstring.

## Constants

### Public

- `LOSSY_AUDIO_EXTENSIONS` [constant] (pyssp/ui/main_window/constants.py:5)
  Detail: Value: {'.mp3', '.m4a', '.aac', '.ogg', '.wma'}
- `FFMPEG_AUDIO_CODEC_FLAGS` [constant] (pyssp/ui/main_window/constants.py:6)
  Detail: Value: {'.mp3': ['-c:a', 'libmp3lame', '-q:a', '2'], '.m4a': ['-c:a', 'aac', '-b:a',...
- `GROUPS` [constant] (pyssp/ui/main_window/constants.py:15)
  Detail: Value: list('ABCDEFGHIJ')
- `PAGE_COUNT` [constant] (pyssp/ui/main_window/constants.py:16)
  Detail: Value: 18
- `SLOTS_PER_PAGE` [constant] (pyssp/ui/main_window/constants.py:17)
  Detail: Value: 48
- `GRID_ROWS` [constant] (pyssp/ui/main_window/constants.py:18)
  Detail: Value: 6
- `GRID_COLS` [constant] (pyssp/ui/main_window/constants.py:19)
  Detail: Value: 8
- `COLORS` [constant] (pyssp/ui/main_window/constants.py:21)
  Detail: Value: {'empty': '#0B868A', 'assigned': '#B0B0B0', 'highlighted': '#A6D8FF', 'playin...
- `TIMECODE_SLOT_INDICATOR_COLOR` [constant] (pyssp/ui/main_window/constants.py:37)
  Detail: Value: '#9C4DFF'
- `HOTKEY_DEFAULTS` [constant] (pyssp/ui/main_window/constants.py:39)
  Detail: Value: {'new_set': ('Ctrl+N', ''), 'open_set': ('Ctrl+O', ''), 'save_set': ('Ctrl+S'...
- `MIDI_HOTKEY_DEFAULTS` [constant] (pyssp/ui/main_window/constants.py:76)
  Detail: Value: {key: ('', '') for key in HOTKEY_DEFAULTS.keys()}
- `SYSTEM_HOTKEY_ORDER_DEFAULT` [constant] (pyssp/ui/main_window/constants.py:78)
  Detail: Value: ['new_set', 'open_set', 'save_set', 'save_set_as', 'search', 'options', 'play...
