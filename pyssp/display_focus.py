from __future__ import annotations

DISPLAY_FOCUS_NONE = "none"
DISPLAY_FOCUS_VIDEO = "video"
DISPLAY_FOCUS_IMAGE = "image"
DISPLAY_FOCUS_LYRIC = "lyric_display"
DISPLAY_FOCUS_STAGE = "stage_display"
DISPLAY_FOCUS_BACKDROP = "backdrop"
DISPLAY_FOCUS_WHITE = "white_screen"
DISPLAY_FOCUS_COLOUR_BARS = "colour_bars"
DISPLAY_FOCUS_METRONOME = "metronome_display"
DISPLAY_FOCUS_FOLLOW = "follow_sound_button"

DISPLAY_FOCUS_ROUTE_MODES = {
    DISPLAY_FOCUS_VIDEO,
    DISPLAY_FOCUS_IMAGE,
    DISPLAY_FOCUS_LYRIC,
    DISPLAY_FOCUS_STAGE,
    DISPLAY_FOCUS_BACKDROP,
    DISPLAY_FOCUS_WHITE,
    DISPLAY_FOCUS_COLOUR_BARS,
    DISPLAY_FOCUS_METRONOME,
}
DISPLAY_FOCUS_VALUES = DISPLAY_FOCUS_ROUTE_MODES | {DISPLAY_FOCUS_NONE}
DISPLAY_FOCUS_OUTPUT_MODES = DISPLAY_FOCUS_ROUTE_MODES - {DISPLAY_FOCUS_VIDEO}

DISPLAY_FOCUS_LABELS = {
    DISPLAY_FOCUS_NONE: "None (Audio Only)",
    DISPLAY_FOCUS_VIDEO: "Video",
    DISPLAY_FOCUS_IMAGE: "Image",
    DISPLAY_FOCUS_LYRIC: "Lyric Display",
    DISPLAY_FOCUS_STAGE: "Stage Display",
    DISPLAY_FOCUS_BACKDROP: "Backdrop",
    DISPLAY_FOCUS_WHITE: "White Screen",
    DISPLAY_FOCUS_COLOUR_BARS: "Colour Bars",
    DISPLAY_FOCUS_METRONOME: "Metronome Display",
}
DISPLAY_FOCUS_OVERRIDE_LABELS = {
    DISPLAY_FOCUS_FOLLOW: "Follow Sound Button Display Focus",
    **DISPLAY_FOCUS_LABELS,
}
DISPLAY_ROUTE_SOURCE_BLANK = "blank"
DISPLAY_ROUTE_SOURCE_VALUES = DISPLAY_FOCUS_ROUTE_MODES | {DISPLAY_ROUTE_SOURCE_BLANK}
DISPLAY_ROUTE_SOURCE_LABELS = {
    DISPLAY_FOCUS_VIDEO: DISPLAY_FOCUS_LABELS[DISPLAY_FOCUS_VIDEO],
    DISPLAY_FOCUS_IMAGE: DISPLAY_FOCUS_LABELS[DISPLAY_FOCUS_IMAGE],
    DISPLAY_FOCUS_LYRIC: DISPLAY_FOCUS_LABELS[DISPLAY_FOCUS_LYRIC],
    DISPLAY_FOCUS_STAGE: DISPLAY_FOCUS_LABELS[DISPLAY_FOCUS_STAGE],
    DISPLAY_FOCUS_METRONOME: DISPLAY_FOCUS_LABELS[DISPLAY_FOCUS_METRONOME],
    DISPLAY_FOCUS_BACKDROP: DISPLAY_FOCUS_LABELS[DISPLAY_FOCUS_BACKDROP],
    DISPLAY_ROUTE_SOURCE_BLANK: "Blank",
    DISPLAY_FOCUS_WHITE: DISPLAY_FOCUS_LABELS[DISPLAY_FOCUS_WHITE],
    DISPLAY_FOCUS_COLOUR_BARS: DISPLAY_FOCUS_LABELS[DISPLAY_FOCUS_COLOUR_BARS],
}


def normalize_display_focus(value: str, *, allow_empty: bool = False, default: str = DISPLAY_FOCUS_NONE) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return "" if allow_empty else default
    alias_map = {
        "blank": DISPLAY_FOCUS_NONE,
        "lyric": DISPLAY_FOCUS_LYRIC,
        "stage": DISPLAY_FOCUS_STAGE,
        "color_bars": DISPLAY_FOCUS_COLOUR_BARS,
        "metronome": DISPLAY_FOCUS_METRONOME,
    }
    token = alias_map.get(token, token)
    if token in DISPLAY_FOCUS_VALUES:
        return token
    return "" if allow_empty else default


def normalize_display_output_mode(value: str, *, allow_video: bool, default: str) -> str:
    token = normalize_display_focus(value, allow_empty=False, default=default)
    valid = DISPLAY_FOCUS_ROUTE_MODES if allow_video else DISPLAY_FOCUS_OUTPUT_MODES
    return token if token in valid else default


def normalize_display_focus_override(
    value: str,
    *,
    allow_empty: bool = False,
    default: str = DISPLAY_FOCUS_FOLLOW,
) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return "" if allow_empty else default
    if token in {"follow", "follow_sound", "follow_focus", "sound_button"}:
        return DISPLAY_FOCUS_FOLLOW
    if token == DISPLAY_FOCUS_FOLLOW:
        return token
    if token == "blank":
        token = DISPLAY_FOCUS_NONE
    return normalize_display_focus(token, allow_empty=allow_empty, default=default)


def normalize_display_route_source(
    value: str,
    *,
    allow_empty: bool = False,
    default: str = DISPLAY_ROUTE_SOURCE_BLANK,
) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return "" if allow_empty else default
    if token in {DISPLAY_FOCUS_NONE, DISPLAY_ROUTE_SOURCE_BLANK}:
        token = DISPLAY_ROUTE_SOURCE_BLANK
    else:
        token = normalize_display_focus(token, allow_empty=True, default=DISPLAY_FOCUS_NONE) or token
    if token in DISPLAY_ROUTE_SOURCE_VALUES:
        return token
    return "" if allow_empty else default


def display_focus_label(value: str) -> str:
    token = normalize_display_focus(value, allow_empty=False, default=DISPLAY_FOCUS_NONE)
    return DISPLAY_FOCUS_LABELS.get(token, DISPLAY_FOCUS_LABELS[DISPLAY_FOCUS_NONE])
