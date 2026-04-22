from __future__ import annotations

import os
import sys
from pathlib import Path


def find_bundled_spleeter_cli_dir() -> str:
    candidates: list[Path] = []
    meipass = str(getattr(sys, "_MEIPASS", "") or "").strip()
    if meipass:
        candidates.append(Path(meipass) / "tools" / "spleeter-cli")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "tools" / "spleeter-cli")
        candidates.append(exe_dir / "_internal" / "tools" / "spleeter-cli")
    module_root = Path(__file__).resolve().parent
    candidates.append(module_root.parent / "dist" / "spleeter-cli")
    candidates.append(module_root.parent / "spleeter-cli" / "dist" / "spleeter-cli")
    candidates.append(module_root / "assets" / "tools" / "spleeter-cli")
    for candidate in candidates:
        exe = candidate / ("spleeter-cli.exe" if os.name == "nt" else "spleeter-cli")
        if exe.exists():
            return str(candidate)
    return ""


def find_bundled_spleeter_cli_executable() -> str:
    root = find_bundled_spleeter_cli_dir()
    if not root:
        return ""
    exe = Path(root) / ("spleeter-cli.exe" if os.name == "nt" else "spleeter-cli")
    return str(exe) if exe.exists() else ""


def suggested_vocal_removed_output_path(input_path: str) -> str:
    source = Path(str(input_path or "").strip())
    if not source.name:
        return ""
    suffix = source.suffix if source.suffix else ".wav"
    return str(source.with_name(f"{source.stem}_pyssp_vocal_removal{suffix}"))
