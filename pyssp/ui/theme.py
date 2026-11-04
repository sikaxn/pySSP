"""Application appearance and the two independently editable button colour sets."""

from __future__ import annotations

import subprocess
import sys

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication


DARK_BUTTON_COLORS = {
    "playing": "#397D30", "played": "#A34540", "unplayed": "#464B52",
    "highlight": "#316487", "lock": "#9B842D", "error": "#70439B",
    "place_marker": "#5B626B", "empty": "#176B70", "copied_to_cue": "#365DAE",
    "cue_indicator": "#48B9DB", "volume_indicator": "#D1A541",
    "vocal_removed_indicator": "#8972DD", "midi_indicator": "#D58743",
    "lyric_indicator": "#4BAE90", "automation_indicator": "#45A663",
    "automation_indicator_bypassed": "#777D84",
    "automation_script_indicator": "#3979D0",
    "automation_script_indicator_bypassed": "#637487",
    "sound_button_text_color": "#FFFFFF",
    "active_group_color": "#4D5360", "inactive_group_color": "#30343B",
}

BUTTON_COLOR_KEYS = tuple(DARK_BUTTON_COLORS)
BRIGHT_SETTINGS_KEYS = {key: f"color_{key}" for key in DARK_BUTTON_COLORS if key not in {
    "sound_button_text_color", "active_group_color", "inactive_group_color",
}}
BRIGHT_SETTINGS_KEYS.update({
    "sound_button_text_color": "sound_button_text_color",
    "active_group_color": "active_group_color",
    "inactive_group_color": "inactive_group_color",
})
STATE_TO_RUNTIME = {
    "unplayed": "assigned", "highlight": "highlighted", "lock": "locked",
    "error": "missing", "place_marker": "marker", "copied_to_cue": "copied",
}


def button_palette_from_settings(settings) -> dict[str, str]:
    return {key: getattr(settings, field) for key, field in BRIGHT_SETTINGS_KEYS.items()}


def normalized_dark_button_colors(colors) -> dict[str, str]:
    result = dict(DARK_BUTTON_COLORS)
    if isinstance(colors, dict):
        for key in BUTTON_COLOR_KEYS:
            value = colors.get(key)
            if isinstance(value, str) and len(value) == 7 and value.startswith("#"):
                try:
                    int(value[1:], 16)
                except ValueError:
                    continue
                result[key] = value.upper()
    return result


def normalize_ui_theme(value: str) -> str:
    theme = str(value or "").strip().lower()
    if theme not in {"bright", "dark", "system"}:
        return "bright"
    return "bright" if theme == "system" and sys.platform not in {"win32", "darwin"} else theme


def system_uses_dark_theme() -> bool:
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            with key:
                return int(winreg.QueryValueEx(key, "AppsUseLightTheme")[0]) == 0
        except (OSError, ValueError):
            return False
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=2, check=False,
            )
            return result.returncode == 0 and result.stdout.strip().lower() == "dark"
        except (OSError, subprocess.TimeoutExpired):
            return False
    return False


def effective_ui_theme(value: str) -> str:
    theme = normalize_ui_theme(value)
    return "dark" if theme == "system" and system_uses_dark_theme() else "bright" if theme == "system" else theme


def apply_ui_theme(app: QApplication, theme: str) -> None:
    """Use Fusion on all platforms so widgets honour an explicit light/dark palette."""
    dark = theme == "dark"
    foreground = "#F2F2F2" if dark else "#000000"
    disabled = "#858B94" if dark else "#777777"
    stylesheet = f"QWidget {{ color: {foreground}; }} QWidget:disabled {{ color: {disabled}; }}"
    if (app.property("_pyssp_applied_theme") == theme
            and app.palette().color(QPalette.WindowText).name().upper() == foreground
            and app.styleSheet() == stylesheet):
        return
    app.setStyle("Fusion")
    colors = {
        QPalette.Window: "#24272D" if dark else "#F0F0F0",
        QPalette.WindowText: "#F2F2F2" if dark else "#000000",
        QPalette.Base: "#1B1D22" if dark else "#FFFFFF",
        QPalette.AlternateBase: "#30343B" if dark else "#F5F5F5",
        QPalette.ToolTipBase: "#343942" if dark else "#FFFFDC",
        QPalette.ToolTipText: "#FFFFFF" if dark else "#000000",
        QPalette.Text: "#F2F2F2" if dark else "#000000",
        QPalette.Button: "#343942" if dark else "#F0F0F0",
        QPalette.ButtonText: "#F2F2F2" if dark else "#000000",
        QPalette.BrightText: "#FF6B6B" if dark else "#FF0000",
        QPalette.Link: "#82BCFF" if dark else "#0066CC",
        QPalette.Highlight: "#3B76B4" if dark else "#0078D7",
        QPalette.HighlightedText: "#FFFFFF",
    }
    palette = QPalette()
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText):
        palette.setColor(QPalette.Disabled, role, QColor("#858B94" if dark else "#777777"))
    app.setPalette(palette)
    # Qt keeps an old palette on widgets that already have a local stylesheet.
    # An application rule supplies our text colour to those widgets as well.
    app.setStyleSheet(stylesheet)
    app.setProperty("_pyssp_applied_theme", theme)
