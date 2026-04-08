from __future__ import annotations

import re
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from pyssp.i18n import localize_widget_tree


class TimecodeOffsetEdit(QLineEdit):
    _PATTERN = re.compile(r"^\d{2}:\d{2}:\d{2}:\d{2}$")

    def __init__(self, offset_ms: Optional[int] = None, fps: float = 30.0, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._fps = max(1.0, float(fps))
        self.setPlaceholderText("HH:MM:SS:FF")
        self.setText(self.format_offset_ms(offset_ms, self._fps))
        self.setAlignment(Qt.AlignCenter)

    @classmethod
    def parse_offset_ms(cls, value: str, fps: float = 30.0) -> Optional[int]:
        text = str(value or "").strip()
        if not text:
            return 0
        if not cls._PATTERN.fullmatch(text):
            return None
        hh, mm, ss, ff = text.split(":")
        hour = int(hh)
        minute = int(mm)
        second = int(ss)
        frame = int(ff)
        if minute > 59 or second > 59 or frame > 59:
            return None
        safe_fps = max(1.0, float(fps))
        total_ms = ((hour * 3600) + (minute * 60) + second) * 1000
        total_ms += int((frame / safe_fps) * 1000)
        return max(0, total_ms)

    @classmethod
    def format_offset_ms(cls, offset_ms: Optional[int], fps: float = 30.0) -> str:
        total_ms = max(0, int(offset_ms or 0))
        safe_fps = max(1.0, float(fps))
        total_seconds = total_ms // 1000
        rem_ms = total_ms % 1000
        hh = total_seconds // 3600
        mm = (total_seconds % 3600) // 60
        ss = total_seconds % 60
        ff = int(round((rem_ms / 1000.0) * safe_fps))
        if ff >= int(round(safe_fps)):
            ff = 0
            ss += 1
            if ss >= 60:
                ss = 0
                mm += 1
                if mm >= 60:
                    mm = 0
                    hh += 1
        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"

    def set_offset_ms(self, offset_ms: Optional[int]) -> None:
        self.setText(self.format_offset_ms(offset_ms, self._fps))

    def offset_ms(self) -> Optional[int]:
        return self.parse_offset_ms(self.text(), self._fps)

    def keyPressEvent(self, event) -> None:
        key = int(event.key())
        if key in {Qt.Key_Up, Qt.Key_Down}:
            current = self.offset_ms()
            if current is None:
                current = 0
            delta = 1000 if key == Qt.Key_Up else -1000
            self.set_offset_ms(max(0, current + delta))
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event) -> None:
        parsed = self.offset_ms()
        if parsed is None:
            self.set_offset_ms(0)
        else:
            self.set_offset_ms(parsed)
        super().focusOutEvent(event)


class TimecodeSetupDialog(QDialog):
    def __init__(
        self,
        offset_ms: Optional[int],
        timeline_mode: str,
        fps: float = 30.0,
        language: str = "en",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Timecode Setup")
        self.resize(680, 190)

        root = QVBoxLayout(self)
        form = QFormLayout()

        offset_row = QWidget()
        offset_layout = QHBoxLayout(offset_row)
        offset_layout.setContentsMargins(0, 0, 0, 0)
        self.offset_edit = TimecodeOffsetEdit(offset_ms, fps=fps, parent=self)
        self.offset_up_btn = QPushButton("▲")
        self.offset_down_btn = QPushButton("▼")
        self.offset_up_btn.setToolTip("+1s")
        self.offset_down_btn.setToolTip("-1s")
        self.clear_btn = QPushButton("Clear")
        self.offset_up_btn.clicked.connect(lambda _=False: self._nudge_offset_ms(1000))
        self.offset_down_btn.clicked.connect(lambda _=False: self._nudge_offset_ms(-1000))
        self.clear_btn.clicked.connect(lambda _=False: self.offset_edit.set_offset_ms(0))
        offset_layout.addWidget(self.offset_edit, 1)
        offset_layout.addWidget(self.offset_up_btn)
        offset_layout.addWidget(self.offset_down_btn)
        offset_layout.addWidget(self.clear_btn)
        form.addRow("Offset", offset_row)

        self.timeline_mode_global_radio = QRadioButton("Respect global setting")
        self.timeline_mode_audio_file_radio = QRadioButton("Relative to actual audio file")
        self.timeline_mode_cue_region_radio = QRadioButton("Relative to cue set point")
        self.timeline_mode_group = QButtonGroup(self)
        self.timeline_mode_group.addButton(self.timeline_mode_global_radio)
        self.timeline_mode_group.addButton(self.timeline_mode_audio_file_radio)
        self.timeline_mode_group.addButton(self.timeline_mode_cue_region_radio)
        timeline_mode_row = QWidget()
        timeline_mode_layout = QHBoxLayout(timeline_mode_row)
        timeline_mode_layout.setContentsMargins(0, 0, 0, 0)
        timeline_mode_layout.setSpacing(14)
        timeline_mode_layout.addWidget(self.timeline_mode_global_radio)
        timeline_mode_layout.addWidget(self.timeline_mode_audio_file_radio)
        timeline_mode_layout.addWidget(self.timeline_mode_cue_region_radio)
        timeline_mode_layout.addStretch(1)
        mode = str(timeline_mode or "global").strip().lower()
        if mode not in {"global", "audio_file", "cue_region"}:
            mode = "global"
        if mode == "audio_file":
            self.timeline_mode_audio_file_radio.setChecked(True)
        elif mode == "cue_region":
            self.timeline_mode_cue_region_radio.setChecked(True)
        else:
            self.timeline_mode_global_radio.setChecked(True)
        form.addRow("Timecode Display Timeline", timeline_mode_row)

        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        localize_widget_tree(self, language)

    def _nudge_offset_ms(self, delta_ms: int) -> None:
        current = self.offset_edit.offset_ms()
        if current is None:
            current = 0
        self.offset_edit.set_offset_ms(max(0, int(current) + int(delta_ms)))

    def values(self) -> tuple[Optional[int], str]:
        offset_ms = self.offset_edit.offset_ms()
        if offset_ms is None or int(offset_ms) <= 0:
            offset_ms = None
        mode = "global"
        if self.timeline_mode_audio_file_radio.isChecked():
            mode = "audio_file"
        elif self.timeline_mode_cue_region_radio.isChecked():
            mode = "cue_region"
        return offset_ms, mode
