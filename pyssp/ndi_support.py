from __future__ import annotations

import glob
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from pyssp.ndi_runtime import probe_runtime_version


NDI_DOWNLOAD_URL = "https://ndi.video/tools/"
NDI_RUNTIME_DOWNLOAD_URL = "https://ndi.link/NDIRedistV6"
_NDI_BACKEND_NAME = "ndi-runtime"


@dataclass(frozen=True)
class NDICapabilityStatus:
    ndi_backend_name: str = _NDI_BACKEND_NAME
    ndi_python_available: bool = True
    ndi_python_version: str = "builtin"
    ndi_module_importable: bool = True
    ndi_runtime_or_sdk_detected: bool = False
    runtime_env_var: str = ""
    runtime_env_value: str = ""
    runtime_paths: List[str] = field(default_factory=list)
    sdk_paths: List[str] = field(default_factory=list)
    bundled_runtime_paths: List[str] = field(default_factory=list)
    availability_reason: str = "NDI runtime library was not detected."
    import_error: str = ""
    platform_name: str = ""
    download_url: str = NDI_DOWNLOAD_URL
    runtime_download_url: str = NDI_RUNTIME_DOWNLOAD_URL
    runtime_library_path: str = ""
    ndi_runtime_version: str = ""

    @property
    def ready(self) -> bool:
        return bool(self.ndi_runtime_or_sdk_detected and self.runtime_library_path)


_NDI_STATUS_CACHE: NDICapabilityStatus | None = None


def _existing_paths(candidates: List[str]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for raw in candidates:
        candidate = str(raw or "").strip()
        if not candidate:
            continue
        try:
            path = Path(candidate).expanduser()
            if not path.exists():
                continue
            resolved = str(path.resolve())
        except Exception:
            continue
        normalized = os.path.normcase(resolved)
        if normalized in seen:
            continue
        seen.add(normalized)
        output.append(resolved)
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


def _macos_bundle_framework_candidates() -> List[str]:
    patterns = [
        "/Applications/NDI*.app/Contents/Frameworks",
        "/Applications/NDI*.app/Contents/Frameworks/*/Versions/A/Frameworks",
        "/Library/CoreMediaIO/Plug-Ins/DAL/*.plugin/Contents/Frameworks",
        "/Library/Audio/Plug-Ins/HAL/*.driver/Contents/Frameworks",
    ]
    output: List[str] = []
    for pattern in patterns:
        output.extend(glob.glob(pattern))
    return output


def _runtime_candidates() -> tuple[str, List[str]]:
    env_var = "NDI_RUNTIME_DIR_V6"
    env_candidates = [_env_dir("NDI_RUNTIME_DIR_V6"), _env_dir("NDI_RUNTIME_DIR_V5")]
    if _env_dir("NDI_RUNTIME_DIR_V5") and not _env_dir("NDI_RUNTIME_DIR_V6"):
        env_var = "NDI_RUNTIME_DIR_V5"
    system = platform.system().lower()
    if system == "windows":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        return env_var, [
            *env_candidates,
            os.path.join(program_files, "NDI", "NDI 6 Runtime"),
            os.path.join(program_files, "NDI", "NDI 6 Runtime", "v6"),
            os.path.join(program_files, "NDI", "NDI 5 Runtime"),
            os.path.join(program_files, "NDI", "NDI 5 Runtime", "v5"),
            os.path.join(program_files_x86, "NDI", "NDI 6 Runtime"),
            os.path.join(program_files_x86, "NDI", "NDI 5 Runtime"),
        ]
    if system == "darwin":
        return env_var, [
            *env_candidates,
            "/Library/NDI SDK for Apple",
            "/Library/NDI SDK for Apple/lib/macOS",
            *_macos_bundle_framework_candidates(),
            "/usr/local/lib",
            "/opt/homebrew/lib",
        ]
    return env_var, [
        *env_candidates,
        "/usr/local/lib",
        "/usr/lib",
        "/usr/lib64",
        "/opt/ndi/lib",
    ]


def _sdk_candidates() -> List[str]:
    env_candidates = [_env_dir("NDI_SDK_DIR"), _env_dir("NDI_SDK_HOME")]
    system = platform.system().lower()
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
        "/usr/local/include",
        "/usr/include",
    ]


def _runtime_library_file_candidates(root: str) -> List[str]:
    candidate = str(root or "").strip()
    if not candidate:
        return []
    system = platform.system().lower()
    if system == "windows":
        names = ["Processing.NDI.Lib.x64.dll", "Processing.NDI.Lib.x86.dll"]
        paths = [candidate]
        for relative in ("", "v6", "v5", os.path.join("Bin", "x64"), os.path.join("Bin", "x86")):
            paths.append(os.path.join(candidate, relative))
        output: List[str] = []
        for base in paths:
            for name in names:
                output.append(os.path.join(base, name))
        return output
    if system == "darwin":
        names = ["libndi.dylib", "libndi_advanced.dylib"]
        paths = [
            candidate,
            os.path.join(candidate, "lib"),
            os.path.join(candidate, "lib", "macOS"),
            os.path.join(candidate, "Contents", "Frameworks"),
            os.path.join(candidate, "Contents", "Frameworks", "NDICommon.framework"),
            os.path.join(candidate, "Contents", "Frameworks", "NDICommon.framework", "Versions", "A"),
        ]
        return [os.path.join(base, name) for base in paths for name in names]
    names = ["libndi.so.6", "libndi.so"]
    paths = [candidate, os.path.join(candidate, "lib"), os.path.join(candidate, "lib64")]
    return [os.path.join(base, name) for base in paths for name in names]


def _resolve_runtime_library_path(runtime_paths: List[str], sdk_paths: List[str]) -> str:
    exact_files: List[str] = []
    roots: List[str] = []
    for candidate in [*runtime_paths, *sdk_paths]:
        path = Path(candidate)
        if path.is_file():
            exact_files.append(str(path))
        else:
            roots.append(str(path))
    for file_candidate in exact_files:
        if Path(file_candidate).exists():
            return str(Path(file_candidate).resolve())
    file_candidates: List[str] = []
    for root in roots:
        file_candidates.extend(_runtime_library_file_candidates(root))
    for candidate in _existing_paths(file_candidates):
        if Path(candidate).is_file():
            return candidate
    return ""


def probe_ndi_capability(force_refresh: bool = False) -> NDICapabilityStatus:
    global _NDI_STATUS_CACHE
    if _NDI_STATUS_CACHE is not None and not force_refresh:
        return _NDI_STATUS_CACHE

    runtime_env_var, runtime_candidates = _runtime_candidates()
    runtime_paths = _existing_paths(runtime_candidates)
    sdk_paths = _existing_paths(_sdk_candidates())
    runtime_library_path = _resolve_runtime_library_path(runtime_paths, sdk_paths)
    runtime_env_value = _env_dir(runtime_env_var)
    runtime_or_sdk_detected = bool(runtime_paths or sdk_paths)
    runtime_version = probe_runtime_version(runtime_library_path) if runtime_library_path else ""

    if not runtime_or_sdk_detected:
        reason = "NDI runtime/SDK was not detected."
    elif not runtime_library_path:
        reason = "NDI runtime/SDK was detected, but the runtime library file was not found."
    else:
        reason = "NDI runtime is ready."

    _NDI_STATUS_CACHE = NDICapabilityStatus(
        ndi_backend_name=_NDI_BACKEND_NAME,
        ndi_python_available=True,
        ndi_python_version="builtin",
        ndi_module_importable=True,
        ndi_runtime_or_sdk_detected=runtime_or_sdk_detected,
        runtime_env_var=runtime_env_var,
        runtime_env_value=runtime_env_value,
        runtime_paths=runtime_paths,
        sdk_paths=sdk_paths,
        bundled_runtime_paths=[],
        availability_reason=reason,
        import_error="",
        platform_name=platform.system(),
        runtime_library_path=runtime_library_path,
        ndi_runtime_version=runtime_version,
    )
    return _NDI_STATUS_CACHE


def ndi_status_lines(status: NDICapabilityStatus | None = None) -> List[str]:
    resolved = status if status is not None else probe_ndi_capability()
    runtime_paths = ", ".join(resolved.runtime_paths) if resolved.runtime_paths else "none"
    sdk_paths = ", ".join(resolved.sdk_paths) if resolved.sdk_paths else "none"
    return [
        f"NDI backend: {resolved.ndi_backend_name}",
        f"NDI runtime/sdk detected: {'yes' if resolved.ndi_runtime_or_sdk_detected else 'no'}",
        f"NDI runtime version: {resolved.ndi_runtime_version or 'unknown'}",
        f"NDI runtime status: {resolved.availability_reason}",
        f"NDI runtime env: {resolved.runtime_env_var or '(none)'} = {resolved.runtime_env_value or '(unset)'}",
        f"NDI runtime library: {resolved.runtime_library_path or 'none'}",
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
