from __future__ import annotations

import os
import sys
import time
import random
import queue
import html
import socket
import ipaddress
import subprocess
import re
import json
import shutil
import configparser
import tempfile
import zipfile
import math
from concurrent.futures import Future
from datetime import datetime
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from PyQt5.QtCore import QEvent, QRect, QSize, QTimer, Qt, QMimeData, QObject, pyqtSignal, pyqtSlot, QThread, QUrl
from PyQt5.QtGui import QColor, QTextDocument, QDrag, QKeySequence, QPainter, QFont, QDesktopServices, QPixmap, QPen, QIcon
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QProgressDialog,
    QInputDialog,
    QScrollArea,
    QTabWidget,
    QSpinBox,
    QSlider,
    QShortcut,
    QStyle,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pyssp.audio_format_support import build_audio_file_dialog_filter, normalize_supported_audio_extensions
from pyssp.audio_engine import (
    ExternalMediaPlayer,
    can_decode_with_ffmpeg,
    can_stream_without_preload,
    configure_audio_preload_cache_policy,
    configure_waveform_disk_cache,
    clear_waveform_disk_cache,
    ensure_audio_decoder_ready,
    enforce_audio_preload_limits,
    get_audio_preload_capacity_bytes,
    get_engine_output_meter_levels,
    get_audio_preload_runtime_status,
    get_preload_memory_limits_mb,
    get_media_ssp_units,
    is_audio_preloaded,
    list_output_devices,
    request_audio_preload,
    set_audio_preload_paused,
    set_output_device,
    shutdown_audio_preload,
)
from pyssp.audio_service import AudioPlayerProxy, AudioServiceController
from pyssp.audio_runtime import PlaybackRuntimeTracker
from pyssp.ffmpeg_support import get_ffmpeg_executable, media_has_audio_stream
from pyssp.dsp import DSPConfig, normalize_config
from pyssp.set_loader import (
    format_timecode_offset_hhmmss,
    load_set_file,
    normalize_slot_timecode_timeline_mode,
    parse_delphi_color,
    parse_time_string_to_ms,
    parse_timecode_offset_ms,
)
from pyssp.settings_store import (
    WINDOW_LAYOUT_FADE_ORDER,
    WINDOW_LAYOUT_MAIN_ORDER,
    AppSettings,
    get_settings_path,
    load_settings,
    normalize_window_layout,
    save_settings,
)
from pyssp.i18n import apply_application_font, localize_widget_tree, normalize_language, set_current_language, tr
from pyssp.launchpad import (
    LAUNCHPAD_ACTION_NONE,
    launchpad_control_bindings,
    launchpad_control_note,
    launchpad_action_slot_index,
    launchpad_find_matching_output,
    launchpad_led_rgb_sysex,
    launchpad_page_bindings,
    launchpad_page_slot_note,
    launchpad_programmer_toggle_sysex,
    normalize_launchpad_layout,
)
from pyssp.library_archive import (
    ArchiveOperationCancelled,
    PackAudioLibraryDialog,
    PackReportDialog,
    PackReportRow,
    PageSelectionItem,
    UnpackLibraryDialog,
    build_archive_audio_entries,
    build_archive_lyric_entries,
    build_manifest,
    default_unpack_directory,
    rewrite_packed_set_paths,
    unpack_pyssppak,
    write_manifest,
)
from pyssp.midi_control import (
    MidiPollingThread,
    MidiInputRouter,
    list_midi_input_devices,
    midi_input_name_selector,
    midi_input_selector_name,
    normalize_midi_binding,
    split_midi_binding,
)
from pyssp.vocal_removal_cli import find_bundled_spleeter_cli_executable, suggested_vocal_removed_output_path
from pyssp.path_safety import unsafe_path_reason
from pyssp.lyrics import LyricLine, line_for_position, parse_lyric_file
from pyssp.timecode import (
    LtcAudioOutput,
    MIDI_OUTPUT_DEVICE_NONE,
    MidiOutput,
    MtcMidiOutput,
    MTC_IDLE_ALLOW_DARK,
    MTC_IDLE_KEEP_STREAM,
    TIMECODE_MODE_FOLLOW,
    TIMECODE_MODE_FOLLOW_FREEZE,
    TIMECODE_MODE_SYSTEM,
    TIMECODE_MODE_ZERO,
    frame_to_timecode_string,
    list_midi_output_devices,
    ms_to_timecode_string,
    nominal_fps,
)
from pyssp.ui.dsp_window import DSPWindow
from pyssp.ui.cue_point_dialog import CuePointDialog
from pyssp.ui.edit_sound_button_dialog import EditSoundButtonDialog
from pyssp.ui.lyric_editor_dialog import LyricEditorDialog
from pyssp.ui.lyric_navigator import LyricNavigatorWindow
from pyssp.ui.options_dialog import OptionsDialog
from pyssp.ui.link_lyric_dialog import LinkLyricDialog
from pyssp.ui.lyric_display import LyricDisplayWindow
from pyssp.ui.timecode_setup_dialog import TimecodeSetupDialog
from pyssp.ui.stage_display import (
    StageDisplayWindow as GadgetStageDisplayWindow,
    gadgets_to_legacy_layout_visibility,
    normalize_stage_display_gadgets,
)
from pyssp.ui.search_window import SearchWindow
from pyssp.ui.audio_engine_insight_dialog import AudioEngineInsightDialog
from pyssp.ui.system_info_dialog import SystemInformationDialog
from pyssp.ui.menu_roles import configure_about_menu_actions, configure_preferences_menu_actions
from pyssp.ui.tips_window import TipsWindow
from pyssp.web_remote import WebRemoteServer
from pyssp.version import get_app_title_base, get_display_build_id, get_display_version
