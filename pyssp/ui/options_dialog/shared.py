from __future__ import annotations

from copy import deepcopy
import json
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse

from PyQt5.QtCore import QMimeData, QPoint, QPointF, QRect, QRectF, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QDrag, QFont, QIcon, QKeySequence, QPainter, QPen, QPixmap, QPolygonF
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
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
    default_quick_action_keys,
    default_window_layout,
    normalize_window_layout,
)
from pyssp.i18n import localize_widget_tree, normalize_language, tr
from pyssp.midi_control import (
    list_midi_input_devices,
    midi_binding_to_display,
    midi_input_name_selector,
    midi_input_selector_name,
    normalize_midi_binding,
    split_midi_binding,
)
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
    gadgets_to_legacy_layout_visibility,
    normalize_stage_display_gadgets,
)


WINDOW_LAYOUT_DRAG_MIME = "application/x-pyssp-window-layout-item"


