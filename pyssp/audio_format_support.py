from __future__ import annotations

from typing import Callable, List, Optional

from PyQt5.QtWidgets import QMessageBox

from pyssp.i18n import tr
from pyssp.settings_store import load_settings, save_settings
from pyssp.ui.system_info_dialog import detect_supported_audio_format_extensions


def normalize_supported_audio_extensions(values: List[str]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for raw in list(values or []):
        token = str(raw or "").strip().lower()
        if not token:
            continue
        if not token.startswith("."):
            token = f".{token.lstrip('.')}"
        if token in seen:
            continue
        seen.add(token)
        output.append(token)
    return output


def build_audio_file_dialog_filter(
    supported_audio_format_extensions: List[str],
    allow_other_unsupported_audio_files: bool,
) -> str:
    supported = normalize_supported_audio_extensions(supported_audio_format_extensions)
    if supported and (not allow_other_unsupported_audio_files):
        patterns = " ".join(f"*{token}" for token in supported)
        return f"Supported Audio Files ({patterns})"
    base = "Audio Files (*.wav *.aiff *.mp3 *.ogg *.flac *.m4a)"
    if allow_other_unsupported_audio_files:
        return f"{base};;All Files (*.*)"
    return base


def ensure_supported_audio_formats_ready(
    *,
    timeout_sec: float = 10.0,
    set_status: Optional[Callable[[str], None]] = None,
    before_prompt: Optional[Callable[[], None]] = None,
    after_prompt: Optional[Callable[[], None]] = None,
) -> bool:
    settings = load_settings()
    configured = normalize_supported_audio_extensions(
        list(getattr(settings, "supported_audio_format_extensions", []))
    )
    if configured:
        return True

    if set_status is not None:
        set_status("Detecting audio formats...")

    detected = normalize_supported_audio_extensions(
        detect_supported_audio_format_extensions(timeout_sec=timeout_sec)
    )
    if detected:
        settings.supported_audio_format_extensions = list(detected)
        save_settings(settings)
        return True

    if before_prompt is not None:
        before_prompt()
    answer = QMessageBox.question(
        None,
        tr("Audio Format Detection"),
        tr("Could not detect supported audio formats within 10 seconds.\n\nAllow other unsupported files for now?"),
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes,
    )
    settings.allow_other_unsupported_audio_files = answer == QMessageBox.Yes
    save_settings(settings)
    if after_prompt is not None:
        after_prompt()
    return True
