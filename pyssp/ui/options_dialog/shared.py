from __future__ import annotations

from copy import deepcopy
import json
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse

from PyQt5.QtCore import QMimeData, QPoint, QPointF, QRect, QRectF, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QDrag, QFont, QFontDatabase, QIcon, QKeySequence, QPainter, QPen, QPixmap, QPolygonF
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QFontComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QLineEdit,
    QScrollArea,
    QSlider,
    QSpacerItem,
    QSpinBox,
    QMessageBox,
    QStackedWidget,
    QStyle,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyssp.audio_engine import clear_waveform_disk_cache, get_waveform_cache_limit_bounds_mb, get_waveform_cache_usage_bytes
from pyssp.settings_store import (
    WINDOW_LAYOUT_FADE_GRID_COLS,
    WINDOW_LAYOUT_FADE_GRID_ROWS,
    WINDOW_LAYOUT_FADE_ORDER,
    WINDOW_LAYOUT_MAIN_GRID_COLS,
    WINDOW_LAYOUT_MAIN_GRID_ROWS,
    WINDOW_LAYOUT_MAIN_ORDER,
    default_companion_satellite_serial_suffix,
    default_quick_action_keys,
    default_window_layout,
    normalize_sound_button_list_hidden_columns,
    normalize_window_layout,
)
from pyssp.i18n import SOURCE_TEXT_ROLE, localize_widget_tree, normalize_language, tr
from pyssp.launchpad import (
    LAUNCHPAD_ACTION_NONE,
    LAUNCHPAD_ACTION_SHIFT_LAYER,
    LAUNCHPAD_SHIFT_CONTROL_INDEX,
    build_launchpad_action_options,
    is_launchpad_name,
    launchpad_action_slot_index,
    launchpad_layout_options,
    normalize_launchpad_layout,
)
from pyssp.midi_control import (
    list_midi_input_devices,
    midi_binding_to_display,
    midi_input_name_selector,
    midi_input_selector_name,
    normalize_midi_binding,
    split_midi_binding,
)
from pyssp.ndi_support import NDI_DOWNLOAD_URL, NDICapabilityStatus, probe_ndi_capability
from pyssp.timecode import (
    MIDI_OUTPUT_DEVICE_NONE,
    MTC_IDLE_KEEP_STREAM,
    TIMECODE_MODE_FOLLOW,
    TIMECODE_MODE_FOLLOW_FREEZE,
    TIMECODE_MODE_SYSTEM,
    TIMECODE_MODE_ZERO,
    TIME_CODE_BIT_DEPTHS,
    TIME_CODE_FPS_CHOICES,
    TIME_CODE_MTC_FPS_CHOICES,
    TIME_CODE_SAMPLE_RATES,
    list_midi_output_devices,
)
from pyssp.ui.system_info_dialog import detect_supported_audio_format_extensions
from pyssp.ui.stage_display import (
    STAGE_DISPLAY_GADGET_SPECS,
    StageDisplayLayoutEditor,
    available_display_font_families,
    bundled_display_font_family,
    gadgets_to_legacy_layout_visibility,
    normalize_stage_display_gadgets,
)


WINDOW_LAYOUT_DRAG_MIME = "application/x-pyssp-window-layout-item"
SOUND_BUTTON_LIST_COLUMN_KEYS: list[str] = [
    "ram",
    "index",
    "title",
    "notes",
    "status",
    "edit",
    "cue",
    "lyric",
    "automation",
    "script",
    "timecode",
]
SOUND_BUTTON_LIST_COLUMN_LABELS: dict[str, str] = {
    "ram": "RAM",
    "index": "#",
    "title": "Title",
    "notes": "Notes",
    "status": "Status",
    "edit": "Edit",
    "cue": "Cue",
    "lyric": "Lyric",
    "automation": "Automation",
    "script": "Script",
    "timecode": "Timecode",
}
