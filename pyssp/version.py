from __future__ import annotations

import json
import sys
from pathlib import Path

DEV_VERSION = "0.0.0 dev"
FALLBACK_BUILD_VERSION = "0.0.0"


def _candidate_version_paths() -> list[Path]:
    paths: list[Path] = []
    if getattr(sys, "frozen", False):
        exe_dir = Path(getattr(sys, "executable", "")).resolve().parent
        paths.append(exe_dir / "version.json")
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            paths.append(Path(meipass) / "version.json")
    else:
        repo_root = Path(__file__).resolve().parent.parent
        paths.append(repo_root / "version.json")
    return paths


def get_configured_version() -> str:
    for path in _candidate_version_paths():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            version = str(raw.get("version", "")).strip()
            if version:
                return version
        except Exception:
            continue
    return FALLBACK_BUILD_VERSION


def get_display_version() -> str:
    if getattr(sys, "frozen", False):
        return get_configured_version()
    return DEV_VERSION


def get_app_title_base() -> str:
    return f"pySSP {get_display_version()}"
