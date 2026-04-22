from __future__ import annotations

from .shared import *

__all__ = [
    "build_lock_icon",
    "_equal_power_crossfade_volume",
    "format_time",
    "format_clock_time",
    "format_set_time",
    "clean_set_value",
    "to_set_color_value",
    "elide_text",
]

def build_lock_icon(size: int = 18, color: str = "#202020") -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidth(2)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    body_w = max(8, int(size * 0.56))
    body_h = max(6, int(size * 0.42))
    body_x = int((size - body_w) / 2)
    body_y = int(size * 0.46)
    painter.drawRoundedRect(body_x, body_y, body_w, body_h, 2, 2)
    shackle_w = max(6, int(size * 0.38))
    shackle_h = max(5, int(size * 0.34))
    shackle_x = int((size - shackle_w) / 2)
    shackle_y = int(size * 0.16)
    painter.drawArc(shackle_x, shackle_y, shackle_w, shackle_h, 0, 180 * 16)
    painter.end()
    return pixmap


def _equal_power_crossfade_volume(start: int, end: int, ratio: float) -> int:
    clamped_ratio = max(0.0, min(1.0, float(ratio)))
    angle = clamped_ratio * (math.pi / 2.0)
    start_value = max(0, min(100, int(start)))
    end_value = max(0, min(100, int(end)))
    if end_value >= start_value:
        curve_ratio = math.sin(angle)
        value = start_value + ((end_value - start_value) * curve_ratio)
    else:
        curve_ratio = math.cos(angle)
        value = end_value + ((start_value - end_value) * curve_ratio)
    return max(0, min(100, int(value)))

def format_time(ms: int) -> str:
    total_seconds = max(0, ms // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def format_clock_time(ms: int) -> str:
    # Display transport using timecode-style frames.
    fps = 30
    total_ms = max(0, ms)
    total_seconds, remainder_ms = divmod(total_ms, 1000)
    minutes, seconds = divmod(total_seconds, 60)
    frames = min(fps - 1, int((remainder_ms / 1000.0) * fps))
    return f"{minutes:02d}:{seconds:02d}:{frames:02d}"


def format_set_time(ms: int) -> str:
    total_seconds = max(0, ms // 1000)
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def clean_set_value(value: str) -> str:
    return (value or "").replace("\r", " ").replace("\n", " ").strip()


def to_set_color_value(hex_color: Optional[str]) -> str:
    if not hex_color:
        return "clBtnFace"
    color = hex_color.strip()
    if len(color) != 7 or not color.startswith("#"):
        return "clBtnFace"
    try:
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)
    except ValueError:
        return "clBtnFace"
    return f"$00{blue:02X}{green:02X}{red:02X}"


def elide_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3] + "..."
