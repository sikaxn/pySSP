from __future__ import annotations

import os
import sys
from pathlib import Path


def preferred_python_executable() -> str:
    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable)

    prefix = Path(getattr(sys, "prefix", "") or "")
    candidates = []
    if os.name == "nt":
        candidates.extend(
            [
                prefix / "Scripts" / "python.exe",
                prefix / "python.exe",
            ]
        )
    else:
        candidates.extend(
            [
                prefix / "bin" / "python3",
                prefix / "bin" / "python",
            ]
        )

    for candidate in candidates:
        try:
            if candidate.exists():
                return str(candidate.resolve())
        except Exception:
            continue

    return os.path.abspath(sys.executable)


__all__ = ["preferred_python_executable"]
