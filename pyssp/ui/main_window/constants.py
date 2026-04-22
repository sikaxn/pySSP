from __future__ import annotations

from typing import Dict, List

LOSSY_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".ogg", ".wma"}
FFMPEG_AUDIO_CODEC_FLAGS = {
    ".mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    ".m4a": ["-c:a", "aac", "-b:a", "256k"],
    ".aac": ["-c:a", "aac", "-b:a", "256k"],
    ".ogg": ["-c:a", "libvorbis", "-q:a", "5"],
    ".flac": ["-c:a", "flac"],
    ".wav": ["-c:a", "pcm_s16le"],
}

GROUPS = list("ABCDEFGHIJ")
PAGE_COUNT = 18
SLOTS_PER_PAGE = 48
GRID_ROWS = 6
GRID_COLS = 8

COLORS = {
    "empty": "#0B868A",
    "assigned": "#B0B0B0",
    "highlighted": "#A6D8FF",
    "playing": "#66FF33",
    "played": "#FF3B30",
    "missing": "#7B3FB3",
    "locked": "#F2D74A",
    "marker": "#D0D0D0",
    "copied": "#2E65FF",
    "cue_indicator": "#61D6FF",
    "volume_indicator": "#FFD45A",
    "midi_indicator": "#FF9E4A",
    "lyric_indicator": "#57C3A4",
}
TIMECODE_SLOT_INDICATOR_COLOR = "#9C4DFF"

HOTKEY_DEFAULTS: Dict[str, tuple[str, str]] = {
    "new_set": ("Ctrl+N", ""),
    "open_set": ("Ctrl+O", ""),
    "save_set": ("Ctrl+S", ""),
    "save_set_as": ("Ctrl+Shift+S", ""),
    "search": ("Ctrl+F", ""),
    "options": ("", ""),
    "play_selected_pause": ("", ""),
    "play_selected": ("", ""),
    "pause_toggle": ("P", ""),
    "stop_playback": ("Space", "Return"),
    "talk": ("Shift", ""),
    "next_group": ("", ""),
    "prev_group": ("", ""),
    "next_page": ("", ""),
    "prev_page": ("", ""),
    "next_sound_button": ("", ""),
    "prev_sound_button": ("", ""),
    "multi_play": ("", ""),
    "go_to_playing": ("", ""),
    "loop": ("", ""),
    "next": ("", ""),
    "rapid_fire": ("", ""),
    "shuffle": ("", ""),
    "reset_page": ("", ""),
    "play_list": ("", ""),
    "fade_in": ("", ""),
    "cross_fade": ("", ""),
    "fade_out": ("", ""),
    "mute": ("", ""),
    "volume_up": ("", ""),
    "volume_down": ("", ""),
    "lock_toggle": ("Ctrl+L", ""),
    "open_hide_lyric_navigator": ("", ""),
}

MIDI_HOTKEY_DEFAULTS: Dict[str, tuple[str, str]] = {key: ("", "") for key in HOTKEY_DEFAULTS.keys()}

SYSTEM_HOTKEY_ORDER_DEFAULT: List[str] = [
    "new_set",
    "open_set",
    "save_set",
    "save_set_as",
    "search",
    "options",
    "play_selected_pause",
    "play_selected",
    "pause_toggle",
    "stop_playback",
    "talk",
    "next_group",
    "prev_group",
    "next_page",
    "prev_page",
    "next_sound_button",
    "prev_sound_button",
    "multi_play",
    "go_to_playing",
    "loop",
    "next",
    "rapid_fire",
    "shuffle",
    "reset_page",
    "play_list",
    "fade_in",
    "cross_fade",
    "fade_out",
    "mute",
    "volume_up",
    "volume_down",
    "lock_toggle",
    "open_hide_lyric_navigator",
]


