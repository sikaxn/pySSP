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
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
from PyQt5.QtCore import QEvent, QRect, QSize, QTimer, Qt, QMimeData, QObject, QByteArray, pyqtSignal, pyqtSlot, QThread, QUrl
from PyQt5.QtGui import QColor, QTextDocument, QDrag, QKeySequence, QPainter, QFont, QDesktopServices, QPixmap, QPen, QIcon, QImage
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
    QFormLayout,
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
    QStackedWidget,
    QStyle,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pyssp.audio_format_support import (
    build_audio_file_dialog_filter,
    effective_audio_file_extensions,
    normalize_supported_audio_extensions,
)
from pyssp.audio_engine import (
    append_output_monitor_frames,
    consume_output_monitor_chunk,
    ExternalMediaPlayer,
    can_decode_with_ffmpeg,
    can_stream_without_preload,
    clear_output_monitor_frames,
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
    list_output_monitor_players,
    list_output_devices,
    mix_output_monitor_chunk,
    output_monitor_frame_counts,
    request_audio_preload,
    set_audio_preload_paused,
    set_output_device,
    shutdown_audio_preload,
    take_output_monitor_frames,
)
from pyssp.audio_service import AudioPlayerProxy, AudioServiceController
from pyssp.ffmpeg_support import (
    MediaProbeInfo,
    ffmpeg_available,
    ffmpeg_source,
    ffmpeg_version_text,
    get_ffmpeg_executable,
    get_ffprobe_executable,
    media_has_audio_stream,
    media_has_video_stream,
    probe_media_info,
)
from pyssp.dsp import DSPConfig, normalize_config
from pyssp.display_focus import (
    DISPLAY_FOCUS_BACKDROP,
    DISPLAY_FOCUS_COLOUR_BARS,
    DISPLAY_FOCUS_FOLLOW,
    DISPLAY_FOCUS_IMAGE,
    DISPLAY_FOCUS_LABELS,
    DISPLAY_FOCUS_LYRIC,
    DISPLAY_FOCUS_METRONOME,
    DISPLAY_FOCUS_NONE,
    DISPLAY_FOCUS_OVERRIDE_LABELS,
    DISPLAY_FOCUS_OUTPUT_MODES,
    DISPLAY_FOCUS_ROUTE_MODES,
    DISPLAY_FOCUS_STAGE,
    DISPLAY_FOCUS_VIDEO,
    DISPLAY_FOCUS_WHITE,
    display_focus_label,
    normalize_display_focus,
    normalize_display_focus_override,
    normalize_display_output_mode,
)
from pyssp.set_loader import (
    format_timecode_offset_hhmmss,
    load_set_file,
    normalize_slot_timecode_timeline_mode,
    parse_delphi_color,
    parse_time_string_to_ms,
    parse_timecode_offset_ms,
)
from pyssp.settings_store import (
    DEFAULT_SOUND_BUTTON_LIST_COLUMN_WIDTHS,
    DEFAULT_SOUND_BUTTON_LIST_HIDDEN_COLUMNS,
    WINDOW_LAYOUT_FADE_ORDER,
    WINDOW_LAYOUT_MAIN_ORDER,
    AppSettings,
    default_companion_satellite_serial_suffix,
    get_settings_path,
    load_settings,
    normalize_sound_button_list_column_widths,
    normalize_sound_button_list_hidden_columns,
    normalize_window_layout,
    save_settings,
)
from pyssp.companion_available_commands import (
    clear_companion_available_commands,
    load_companion_available_commands,
    record_companion_available_command,
)
from pyssp.i18n import apply_application_font, localize_widget_tree, normalize_language, set_current_language, tr
from pyssp.launchpad import (
    LAUNCHPAD_ACTION_NONE,
    LAUNCHPAD_ACTION_SHIFT_LAYER,
    LAUNCHPAD_SHIFT_CONTROL_INDEX,
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
    build_archive_automation_script_entries,
    build_archive_lyric_entries,
    build_archive_vocal_removed_entries,
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
from pyssp.lyrics import (
    LyricLine,
    line_for_position,
    lyric_segments_around_position,
    lyric_segments_to_html,
    lyric_text_around_position,
    parse_lyric_file,
)
from pyssp.ndi_output import NDIOutputConfig, NDIOutputDispatcher
from pyssp.ndi_support import NDI_DOWNLOAD_URL, ndi_status_lines, probe_ndi_capability
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
from pyssp.ui.automation_script_navigator import AutomationScriptNavigatorWindow
from pyssp.ui.options_dialog import OptionsDialog
from pyssp.ui.link_lyric_dialog import LinkLyricDialog
from pyssp.ui.lyric_display import LyricDisplayWindow
from pyssp.ui.timecode_setup_dialog import TimecodeSetupDialog
from pyssp.ui.stage_display import (
    StageDisplayWindow as GadgetStageDisplayWindow,
    gadgets_to_legacy_layout_visibility,
    normalize_stage_display_gadgets,
)
from pyssp.ui.video_display import VideoDisplayWindow
from pyssp.ui.search_window import SearchWindow
from pyssp.ui.audio_engine_insight_dialog import AudioEngineInsightDialog
from pyssp.ui.companion_available_commands_dialog import CompanionAvailableCommandsDialog
from pyssp.ui.getting_started_dialog import GettingStartedDialog
from pyssp.ui.system_info_dialog import SystemInformationDialog
from pyssp.ui.menu_roles import configure_about_menu_actions, configure_preferences_menu_actions
from pyssp.ui.tips_window import TipsWindow
from pyssp.web_remote import WebRemoteServer
from pyssp.version import get_app_title_base, get_display_build_id, get_display_version, is_beta_version
