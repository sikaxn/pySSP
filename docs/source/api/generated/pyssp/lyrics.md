# `pyssp/lyrics.py`

- Source: `pyssp/lyrics.py`
- Module path: `pyssp.lyrics`
- API entries: `15`

## Module Docstring

No module docstring.

## Functions

### Public

- `parse_lyric_file(file_path: str) -> List[LyricLine]` [function] (pyssp/lyrics.py:24)
- `line_for_position(lines: List[LyricLine], position_ms: int) -> str` [function] (pyssp/lyrics.py:32)
- `lyric_lines_around_position(lines: List[LyricLine], position_ms: int, previous_count: int, next_count: int) -> List[str]` [function] (pyssp/lyrics.py:45)
- `lyric_segments_around_position(lines: List[LyricLine], position_ms: int, previous_count: int, next_count: int) -> List[tuple[str, str]]` [function] (pyssp/lyrics.py:64)
- `lyric_text_around_position(lines: List[LyricLine], position_ms: int, previous_count: int, next_count: int) -> str` [function] (pyssp/lyrics.py:87)
- `lyric_segments_to_html(segments: List[tuple[str, str]], *, font_family: str = '', role_styles: dict[str, dict[str, object]] | None = None) -> str` [function] (pyssp/lyrics.py:96)

### Internal

- `_parse_lrc(text: str) -> List[LyricLine]` [function] (pyssp/lyrics.py:119)
- `_line_index_for_position(lines: List[LyricLine], position_ms: int) -> int | None` [function] (pyssp/lyrics.py:153)
- `_parse_srt(text: str) -> List[LyricLine]` [function] (pyssp/lyrics.py:163)
- `_lrc_timestamp_to_ms(mm: str, ss: str, frac: str | None) -> int` [function] (pyssp/lyrics.py:187)
- `_srt_timestamp_to_ms(hh: str, mm: str, ss: str, ms: str) -> int` [function] (pyssp/lyrics.py:202)
- `_clean_text(value: str) -> str` [function] (pyssp/lyrics.py:210)
- `_read_text_with_fallback(file_path: str) -> str` [function] (pyssp/lyrics.py:214)
- `_count_cjk_chars(text: str) -> int` [function] (pyssp/lyrics.py:242)

## Classes

### `LyricLine`

- Defined at `pyssp/lyrics.py:11`
