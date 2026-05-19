from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ISOLATED_FILES = [
    "tests/test_companion_satellite_main_window.py",
    "tests/test_lyric_display_window.py",
    "tests/test_main_window_docking.py",
    "tests/test_main_window_import_compat.py",
    "tests/test_main_window_menu_roles.py",
    "tests/test_monkey_main_window.py",
    "tests/test_playback_control_integration.py",
]


def _run(command: list[str]) -> int:
    completed = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
    return int(completed.returncode)


def _collect_nodeids(pytest_args: list[str], file_path: str) -> list[str]:
    _ = pytest_args
    command = [sys.executable, "-m", "pytest", "--collect-only", "-q", file_path]
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise SystemExit(int(completed.returncode))
    nodeids: list[str] = []
    for line in completed.stdout.splitlines():
        text = line.strip()
        if not text or text.endswith("collected in 0.00s") or text.endswith("tests collected"):
            continue
        if (text.startswith("tests/") or text.startswith("tests\\")) and "::" in text:
            nodeids.append(text)
    return nodeids


def main(argv: list[str]) -> int:
    pytest_args = list(argv)
    has_explicit_target = any(arg.startswith("tests/") or arg.startswith("tests\\") or "::" in arg for arg in pytest_args)
    if has_explicit_target:
        return _run([sys.executable, "-m", "pytest", *pytest_args])

    ignore_args: list[str] = []
    for file_path in ISOLATED_FILES:
        ignore_args.extend(["--ignore", file_path])
    exit_code = _run([sys.executable, "-m", "pytest", *ignore_args, *pytest_args])
    if exit_code != 0:
        return exit_code

    for file_path in ISOLATED_FILES:
        exit_code = _run([sys.executable, "-m", "pytest", file_path, *pytest_args])
        if exit_code == 0:
            continue
        for nodeid in _collect_nodeids(pytest_args, file_path):
            exit_code = _run([sys.executable, "-m", "pytest", nodeid, *pytest_args])
            if exit_code != 0:
                return exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
