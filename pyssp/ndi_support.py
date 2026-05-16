from __future__ import annotations

import importlib
import importlib.metadata
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


NDI_DOWNLOAD_URL = "https://ndi.video/for-developers/ndi-sdk/download/"
NDI_RUNTIME_DOWNLOAD_URL = "https://ndi.link/NDIRedistV5"


@dataclass(frozen=True)
class NDICapabilityStatus:
    ndi_python_available: bool = False
    ndi_python_version: str = "not installed"
    ndi_module_importable: bool = False
    ndi_runtime_or_sdk_detected: bool = False
    runtime_env_var: str = ""
    runtime_env_value: str = ""
    runtime_paths: List[str] = field(default_factory=list)
    sdk_paths: List[str] = field(default_factory=list)
    availability_reason: str = "NDI Python binding is not installed."
    import_error: str = ""
    platform_name: str = ""
    download_url: str = NDI_DOWNLOAD_URL
    runtime_download_url: str = NDI_RUNTIME_DOWNLOAD_URL

    @property
    def ready(self) -> bool:
        return bool(
            self.ndi_python_available
            and self.ndi_module_importable
            and self.ndi_runtime_or_sdk_detected
        )


_NDI_STATUS_CACHE: NDICapabilityStatus | None = None


def _package_version(package_name: str) -> str:
    try:
        return str(importlib.metadata.version(package_name) or "").strip() or "unknown"
    except Exception:
        return "not installed"


def _existing_paths(candidates: List[str]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for raw in candidates:
        candidate = str(raw or "").strip()
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if not path.exists():
            continue
        normalized = os.path.normcase(str(path.resolve()))
        if normalized in seen:
            continue
        seen.add(normalized)
        output.append(str(path.resolve()))
    return output


def _env_dir(var_name: str) -> str:
    value = str(os.environ.get(var_name, "") or "").strip()
    if not value:
        return ""
    try:
        path = Path(value).expanduser()
        if path.exists():
            return str(path.resolve())
    except Exception:
        return value
    return value


def _runtime_candidates() -> tuple[str, List[str]]:
    system = platform.system().lower()
    env_var = "NDI_RUNTIME_DIR_V5"
    env_candidates = [_env_dir("NDI_RUNTIME_DIR_V6"), _env_dir("NDI_RUNTIME_DIR_V5")]
    if _env_dir("NDI_RUNTIME_DIR_V6"):
        env_var = "NDI_RUNTIME_DIR_V6"
    if system == "windows":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        candidates = [
            *env_candidates,
            os.path.join(program_files, "NDI", "NDI 6 Runtime"),
            os.path.join(program_files, "NDI", "NDI 6 Runtime", "v6"),
            os.path.join(program_files, "NDI", "NDI 5 Runtime"),
            os.path.join(program_files, "NDI", "NDI 5 Runtime", "v5"),
            os.path.join(program_files_x86, "NDI", "NDI 6 Runtime"),
            os.path.join(program_files_x86, "NDI", "NDI 5 Runtime"),
        ]
        return env_var, candidates
    if system == "darwin":
        return env_var, [
            *env_candidates,
            "/usr/local/lib",
            "/usr/local/lib/libndi.dylib",
            "/Library/NDI SDK for Apple",
            "/Library/NDI SDK for Apple/lib/macOS",
        ]
    return env_var, [
        *env_candidates,
        "/usr/local/lib",
        "/usr/local/lib/libndi.so",
        "/usr/lib/libndi.so",
        "/usr/lib64/libndi.so",
        "/opt/ndi/lib",
    ]


def _sdk_candidates() -> List[str]:
    system = platform.system().lower()
    env_candidates = [_env_dir("NDI_SDK_DIR"), _env_dir("NDI_SDK_HOME")]
    if system == "windows":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        return [
            *env_candidates,
            os.path.join(program_files, "NDI", "NDI 6 SDK"),
            os.path.join(program_files, "NDI", "NDI 5 SDK"),
            os.path.join(program_files_x86, "NDI", "NDI 6 SDK"),
            os.path.join(program_files_x86, "NDI", "NDI 5 SDK"),
        ]
    if system == "darwin":
        return [
            *env_candidates,
            "/Library/NDI SDK for Apple",
        ]
    return [
        *env_candidates,
        "/opt/ndi",
        "/usr/local/include/Processing.NDI.Lib.h",
        "/usr/include/Processing.NDI.Lib.h",
    ]


def probe_ndi_capability(force_refresh: bool = False) -> NDICapabilityStatus:
    global _NDI_STATUS_CACHE
    if _NDI_STATUS_CACHE is not None and not force_refresh:
        return _NDI_STATUS_CACHE

    version = _package_version("ndi-python")
    ndi_python_available = version != "not installed"
    import_error = ""
    module_importable = False
    if ndi_python_available:
        try:
            importlib.import_module("NDIlib")
            module_importable = True
        except Exception as exc:
            import_error = str(exc).strip()
    runtime_env_var, runtime_candidates = _runtime_candidates()
    runtime_paths = _existing_paths(runtime_candidates)
    sdk_paths = _existing_paths(_sdk_candidates())
    runtime_env_value = _env_dir(runtime_env_var)
    runtime_or_sdk_detected = bool(runtime_paths or sdk_paths)

    if not ndi_python_available:
        if runtime_or_sdk_detected:
            reason = "NDI SDK/runtime was detected, but the NDI Python binding is not installed in this Python environment."
        else:
            reason = "NDI Python binding is not installed."
    elif not module_importable:
        reason = f"NDI Python binding is installed but could not be imported: {import_error or 'unknown error'}"
    elif not runtime_or_sdk_detected:
        reason = "NDI runtime/SDK was not detected on this machine."
    else:
        reason = "NDI output is ready."

    _NDI_STATUS_CACHE = NDICapabilityStatus(
        ndi_python_available=ndi_python_available,
        ndi_python_version=version,
        ndi_module_importable=module_importable,
        ndi_runtime_or_sdk_detected=runtime_or_sdk_detected,
        runtime_env_var=runtime_env_var,
        runtime_env_value=runtime_env_value,
        runtime_paths=runtime_paths,
        sdk_paths=sdk_paths,
        availability_reason=reason,
        import_error=import_error,
        platform_name=platform.system(),
    )
    return _NDI_STATUS_CACHE


def ndi_status_lines(status: NDICapabilityStatus | None = None) -> List[str]:
    resolved = status if status is not None else probe_ndi_capability()
    runtime_paths = ", ".join(resolved.runtime_paths) if resolved.runtime_paths else "none"
    sdk_paths = ", ".join(resolved.sdk_paths) if resolved.sdk_paths else "none"
    return [
        f"NDI python installed: {'yes' if resolved.ndi_python_available else 'no'}",
        f"NDI python version: {resolved.ndi_python_version}",
        f"NDI module importable: {'yes' if resolved.ndi_module_importable else 'no'}",
        f"NDI runtime/sdk detected: {'yes' if resolved.ndi_runtime_or_sdk_detected else 'no'}",
        f"NDI status: {resolved.availability_reason}",
        f"NDI runtime env: {resolved.runtime_env_var or '(none)'} = {resolved.runtime_env_value or '(unset)'}",
        f"NDI runtime paths: {runtime_paths}",
        f"NDI sdk paths: {sdk_paths}",
        f"NDI download: {resolved.download_url}",
    ]


__all__ = [
    "NDI_DOWNLOAD_URL",
    "NDI_RUNTIME_DOWNLOAD_URL",
    "NDICapabilityStatus",
    "ndi_status_lines",
    "probe_ndi_capability",
]
