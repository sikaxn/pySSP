from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from glob import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List

from pyssp.settings_store import default_vst_directories


def is_vst_supported() -> bool:
    return sys.platform.startswith("win")


PLUGIN_REF_SEPARATOR = "\t"


def normalize_vst_directories(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    output: List[str] = []
    for raw in values:
        token = str(raw or "").strip().strip('"')
        if not token:
            continue
        normalized = os.path.normpath(token)
        fold = os.path.normcase(normalized)
        if fold in seen:
            continue
        seen.add(fold)
        output.append(normalized)
    return output


def effective_vst_directories(values: Iterable[str]) -> List[str]:
    normalized = normalize_vst_directories(values)
    if normalized:
        return normalized
    return normalize_vst_directories(default_vst_directories())


def make_plugin_ref(file_path: str, plugin_name: str = "") -> str:
    path = str(file_path or "").strip()
    name = str(plugin_name or "").strip()
    if not name:
        return path
    return f"{path}{PLUGIN_REF_SEPARATOR}{name}"


def parse_plugin_ref(plugin_ref: str) -> tuple[str, str]:
    token = str(plugin_ref or "").strip()
    if not token:
        return "", ""
    parts = token.split(PLUGIN_REF_SEPARATOR, 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0].strip(), parts[1].strip()


def plugin_display_name(path: str) -> str:
    file_path, plugin_name = parse_plugin_ref(path)
    if plugin_name:
        return plugin_name
    if not file_path:
        return ""
    return Path(file_path).stem


def _parse_plugin_names_from_error(error_text: str) -> List[str]:
    text = str(error_text or "")
    if "plugin_name" not in text:
        return []
    names: List[str] = []
    for match in re.finditer(r'"([^"\r\n]+)"', text):
        value = str(match.group(1) or "").strip()
        if not value or value in {"plugin_name", "__pyssp_probe_nonexistent_plugin__"}:
            continue
        names.append(value)
    output: List[str] = []
    seen: set[str] = set()
    for name in names:
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(name)
    return output


def discover_plugins_in_file(file_path: str) -> List[str]:
    normalized = os.path.normpath(str(file_path or "").strip())
    if not normalized:
        return []
    cmd = [sys.executable, "-m", "pyssp.vst_probe", "--file", normalized]
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15.0,
            creationflags=creationflags,
        )
        payload_text = ""
        for line in reversed(str(completed.stdout or "").splitlines()):
            token = str(line or "").strip()
            if token.startswith("PYSSP_VST_PROBE_JSON:"):
                payload_text = token[len("PYSSP_VST_PROBE_JSON:") :].strip()
                break
        if not payload_text:
            return []
        payload = json.loads(payload_text)
        names = payload.get("names", []) if isinstance(payload, dict) else []
        valid_names = [str(v).strip() for v in names if str(v).strip()]
        if valid_names:
            return [make_plugin_ref(normalized, name) for name in valid_names]
    except Exception:
        pass
    return []


def _discover_single_file(file_path: str) -> List[str]:
    try:
        return discover_plugins_in_file(file_path)
    except Exception:
        return []


def scan_vst_plugins(directories: Iterable[str]) -> List[str]:
    if not is_vst_supported():
        return []
    candidates: List[str] = []
    for root in effective_vst_directories(directories):
        base = Path(root)
        if not base.exists() or not base.is_dir():
            continue
        try:
            for pattern in ("*.dll", "*.vst3"):
                for plugin_path in base.rglob(pattern):
                    try:
                        normalized = os.path.normpath(str(plugin_path))
                    except Exception:
                        continue
                    candidates.append(normalized)
        except Exception:
            continue

    # Add common Waves shell locations explicitly (outside regular VST dirs)
    # so all installed shells can be expanded.
    if os.name == "nt":
        roots = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ]
        waves_globs = [
            os.path.join(root, "Common Files", "VST3", "WaveShell*-VST3*.vst3")
            for root in roots
        ]
        waves_globs.extend(
            [
                os.path.join(root, "Waves", "WaveShells V*", "**", "WaveShell*.dll")
                for root in roots
            ]
        )
        waves_globs.extend(
            [
                os.path.join(root, "Waves", "WaveShells V*", "**", "WaveShell*-VST3*.vst3")
                for root in roots
            ]
        )
        waves_globs.extend(
            [
                os.path.join(root, "Common Files", "WPAPI", "**", "WaveShell*.dll")
                for root in roots
            ]
        )
        for pattern in waves_globs:
            try:
                matches = glob(pattern, recursive=True)
            except Exception:
                continue
            for path in matches:
                try:
                    if not os.path.isfile(path):
                        continue
                    normalized = os.path.normpath(str(path))
                except Exception:
                    continue
                candidates.append(normalized)

    # Normalize/dedupe candidate list.
    dedup_candidates: List[str] = []
    seen_paths: set[str] = set()
    for path in candidates:
        key = os.path.normcase(str(path))
        if key in seen_paths:
            continue
        seen_paths.add(key)
        dedup_candidates.append(path)

    found: List[str] = []
    seen: set[str] = set()
    max_workers = 1  # Keep vendor scanners isolated; avoids hangs/crashes.
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pyssp-vst-scan") as pool:
        futures = [pool.submit(_discover_single_file, path) for path in dedup_candidates]
        for future in as_completed(futures):
            refs = future.result()
            for plugin_ref in refs:
                plugin_fold = os.path.normcase(plugin_ref)
                if plugin_fold in seen:
                    continue
                seen.add(plugin_fold)
                found.append(plugin_ref)
    # Deduplicate mirrored WaveShell entries (same shell filename + plugin name
    # discovered in multiple folders) while keeping one stable reference.
    shell_name_index: dict[tuple[str, str], str] = {}
    for plugin_ref in found:
        file_path, plugin_name = parse_plugin_ref(plugin_ref)
        shell_name = Path(file_path).name.lower()
        key = (plugin_name.casefold(), shell_name)
        if key not in shell_name_index:
            shell_name_index[key] = plugin_ref
            continue
        existing = shell_name_index[key]
        existing_path, _ = parse_plugin_ref(existing)
        existing_pref = "\\common files\\vst3\\" in existing_path.lower()
        current_pref = "\\common files\\vst3\\" in file_path.lower()
        if current_pref and not existing_pref:
            shell_name_index[key] = plugin_ref

    result = list(shell_name_index.values())
    result.sort(key=lambda p: (plugin_display_name(p).lower(), p.lower()))
    return result
