from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List


@dataclass
class LyricLine:
    start_ms: int
    end_ms: int
    text: str


_LRC_TIMESTAMP_RE = re.compile(r"\[(\d+):(\d{1,2})(?:[.:](\d{1,3}))?\]")
_LRC_OFFSET_RE = re.compile(r"^\s*\[offset\s*:\s*([+-]?\d+)\s*\]\s*$", re.IGNORECASE)
_SRT_TIME_RANGE_RE = re.compile(
    r"^\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*$"
)


def parse_lyric_file(file_path: str) -> List[LyricLine]:
    ext = os.path.splitext(str(file_path or "").strip())[1].lower()
    text = _read_text_with_fallback(file_path)
    if ext == ".srt":
        return _parse_srt(text)
    return _parse_lrc(text)


def line_for_position(lines: List[LyricLine], position_ms: int) -> str:
    if not lines:
        return ""
    pos = max(0, int(position_ms))
    previous_text = ""
    for line in lines:
        if line.start_ms <= pos <= line.end_ms:
            return line.text
        if line.start_ms <= pos:
            previous_text = line.text
    return previous_text


def _parse_lrc(text: str) -> List[LyricLine]:
    offset_ms = 0
    for raw_line in text.splitlines():
        offset_match = _LRC_OFFSET_RE.match(raw_line)
        if offset_match:
            try:
                offset_ms = int(offset_match.group(1))
            except ValueError:
                offset_ms = 0
            break
    events: List[tuple[int, str]] = []
    for raw_line in text.splitlines():
        matches = list(_LRC_TIMESTAMP_RE.finditer(raw_line))
        if not matches:
            continue
        lyric_text = _clean_text(raw_line[matches[-1].end() :])
        for match in matches:
            start_ms = _lrc_timestamp_to_ms(match.group(1), match.group(2), match.group(3))
            start_ms = max(0, start_ms + offset_ms)
            events.append((start_ms, lyric_text))
    events.sort(key=lambda item: item[0])
    if not events:
        return []
    lines: List[LyricLine] = []
    for idx, (start_ms, content) in enumerate(events):
        if idx + 1 < len(events):
            end_ms = max(start_ms, events[idx + 1][0] - 1)
        else:
            end_ms = start_ms + 4_000
        lines.append(LyricLine(start_ms=start_ms, end_ms=end_ms, text=content))
    return lines


def _parse_srt(text: str) -> List[LyricLine]:
    lines: List[LyricLine] = []
    blocks = re.split(r"\r?\n\r?\n+", text.strip(), flags=re.MULTILINE)
    for block in blocks:
        raw_lines = [part.rstrip("\r") for part in block.splitlines() if part.strip()]
        if not raw_lines:
            continue
        time_row_index = 1 if len(raw_lines) >= 2 and raw_lines[0].strip().isdigit() else 0
        if time_row_index >= len(raw_lines):
            continue
        match = _SRT_TIME_RANGE_RE.match(raw_lines[time_row_index])
        if not match:
            continue
        start_ms = _srt_timestamp_to_ms(match.group(1), match.group(2), match.group(3), match.group(4))
        end_ms = _srt_timestamp_to_ms(match.group(5), match.group(6), match.group(7), match.group(8))
        if end_ms < start_ms:
            end_ms = start_ms
        text_lines = raw_lines[time_row_index + 1 :]
        content = _clean_text("\n".join(text_lines))
        lines.append(LyricLine(start_ms=start_ms, end_ms=end_ms, text=content))
    lines.sort(key=lambda item: item.start_ms)
    return lines


def _lrc_timestamp_to_ms(mm: str, ss: str, frac: str | None) -> int:
    minutes = int(mm)
    seconds = int(ss)
    fraction_ms = 0
    if frac:
        value = frac.strip()
        if len(value) == 1:
            fraction_ms = int(value) * 100
        elif len(value) == 2:
            fraction_ms = int(value) * 10
        else:
            fraction_ms = int(value[:3])
    return (minutes * 60 + seconds) * 1000 + fraction_ms


def _srt_timestamp_to_ms(hh: str, mm: str, ss: str, ms: str) -> int:
    hours = int(hh)
    minutes = int(mm)
    seconds = int(ss)
    millis = int(ms.ljust(3, "0")[:3])
    return ((hours * 3600) + (minutes * 60) + seconds) * 1000 + millis


def _clean_text(value: str) -> str:
    return str(value or "").strip()


def _read_text_with_fallback(file_path: str) -> str:
    raw = open(file_path, "rb").read()
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    gbk_text = ""
    cp1252_text = ""
    latin1_text = raw.decode("latin1", errors="replace")
    try:
        gbk_text = raw.decode("gbk")
    except UnicodeDecodeError:
        gbk_text = ""
    try:
        cp1252_text = raw.decode("cp1252")
    except UnicodeDecodeError:
        cp1252_text = ""
    if gbk_text and cp1252_text:
        # Prefer GBK only when decoded text clearly contains CJK content.
        return gbk_text if _count_cjk_chars(gbk_text) >= 4 else cp1252_text
    if cp1252_text:
        return cp1252_text
    if gbk_text:
        return gbk_text
    return latin1_text


def _count_cjk_chars(text: str) -> int:
    total = 0
    for ch in str(text or ""):
        code = ord(ch)
        if 0x4E00 <= code <= 0x9FFF:
            total += 1
    return total
