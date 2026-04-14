from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from pyssp.ffmpeg_support import get_ffmpeg_executable

_LOSSY_EXTENSIONS = {".mp3", ".m4a", ".aac", ".ogg", ".wma"}
_DEFAULT_CODEC_BY_EXT = {
    ".mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    ".m4a": ["-c:a", "aac", "-b:a", "256k"],
    ".aac": ["-c:a", "aac", "-b:a", "256k"],
    ".ogg": ["-c:a", "libvorbis", "-q:a", "5"],
    ".flac": ["-c:a", "flac"],
    ".wav": ["-c:a", "pcm_s16le"],
}


def default_vocal_removed_output_path(input_audio_path: str) -> str:
    source = Path(str(input_audio_path or "").strip())
    if not source.name:
        return ""
    suffix = source.suffix or ".wav"
    return str(source.with_name(f"{source.stem}_pyssp_vocal_removal{suffix}"))


def vocal_removed_suffix_for_title() -> str:
    return "(VR)"


def ensure_spleeter_available() -> Optional[str]:
    try:
        _import_spleeter_cpu_only()
        return None
    except Exception as inprocess_exc:
        sidecar = _detect_sidecar_python_command()
        if sidecar:
            return None
        return (
            "Spleeter is unavailable in this Python runtime and no compatible sidecar "
            "Python interpreter (3.10/3.11 with Spleeter installed) was found. "
            f"In-process error: {inprocess_exc}"
        )


def generate_vocal_removed_file(input_audio_path: str, output_audio_path: str) -> str:
    source = str(input_audio_path or "").strip()
    output = str(output_audio_path or "").strip()
    if not source:
        raise ValueError("Input audio path is required.")
    if not output:
        raise ValueError("Output audio path is required.")
    if not os.path.exists(source):
        raise FileNotFoundError(source)
    source_ext = os.path.splitext(output)[1].lower()
    output_parent = os.path.dirname(output)
    if output_parent:
        os.makedirs(output_parent, exist_ok=True)

    try:
        return _generate_with_inprocess_spleeter(source, output, source_ext)
    except Exception:
        sidecar_python_cmd = _detect_sidecar_python_command()
        if not sidecar_python_cmd:
            raise
        return _generate_with_sidecar_spleeter(source, output, source_ext, sidecar_python_cmd)


def _generate_with_inprocess_spleeter(source: str, output: str, output_ext: str) -> str:
    Separator = _import_spleeter_cpu_only()
    with tempfile.TemporaryDirectory(prefix="pyssp_spleeter_") as temp_dir:
        separator = Separator("spleeter:2stems")
        separator.separate_to_file(
            source,
            temp_dir,
            codec="wav",
            filename_format="{filename}/{instrument}.{codec}",
            synchronous=True,
        )
        base_name = Path(source).stem
        accompaniment_path = os.path.join(temp_dir, base_name, "accompaniment.wav")
        if not os.path.exists(accompaniment_path):
            raise RuntimeError("Spleeter did not generate accompaniment.wav")
        if output_ext in {"", ".wav"}:
            shutil.copyfile(accompaniment_path, output)
            return output
        ffmpeg = get_ffmpeg_executable()
        if not ffmpeg:
            fallback = os.path.splitext(output)[0] + ".wav"
            shutil.copyfile(accompaniment_path, fallback)
            return fallback
        try:
            _ffmpeg_convert(accompaniment_path, output, output_ext, ffmpeg)
            return output
        except Exception:
            fallback = os.path.splitext(output)[0] + ".wav"
            shutil.copyfile(accompaniment_path, fallback)
            return fallback


def _generate_with_sidecar_spleeter(source: str, output: str, output_ext: str, sidecar_python_cmd: List[str]) -> str:
    sidecar_script = _sidecar_script_path()
    if not sidecar_script:
        raise RuntimeError("Unable to locate spleeter sidecar script.")
    ffmpeg = get_ffmpeg_executable() or ""
    model_root = _bundled_spleeter_model_root()
    command = [
        *sidecar_python_cmd,
        sidecar_script,
        "--input",
        source,
        "--output",
        output,
        "--ffmpeg",
        ffmpeg,
        "--model-root",
        model_root,
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        if output_ext in {"", ".wav"} and os.path.exists(output):
            return output
        if os.path.exists(output):
            return output
        fallback = os.path.splitext(output)[0] + ".wav"
        if os.path.exists(fallback):
            return fallback
    message = (completed.stderr or completed.stdout or "Sidecar Spleeter execution failed").strip()
    raise RuntimeError(message)


def _import_spleeter_cpu_only():
    bundled_model_root = _bundled_spleeter_model_root()
    if bundled_model_root:
        os.environ["MODEL_PATH"] = bundled_model_root
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    try:
        import tensorflow as tf  # type: ignore

        try:
            tf.config.set_visible_devices([], "GPU")
        except Exception:
            pass
    except Exception:
        pass
    from spleeter.separator import Separator  # type: ignore

    return Separator


def _bundled_spleeter_model_root() -> str:
    candidates = []
    meipass = str(getattr(sys, "_MEIPASS", "") or "").strip()
    if meipass:
        candidates.append(os.path.join(meipass, "pyssp", "assets", "spleeter_models"))
        candidates.append(os.path.join(meipass, "spleeter_models"))
    module_root = Path(__file__).resolve().parent
    candidates.append(str(module_root / "assets" / "spleeter_models"))
    for candidate in candidates:
        model_dir = os.path.join(candidate, "2stems")
        if _is_valid_spleeter_model_dir(model_dir):
            return candidate
    return ""


def _is_valid_spleeter_model_dir(model_dir: str) -> bool:
    path = str(model_dir or "").strip()
    if not path or not os.path.isdir(path):
        return False
    required_markers = [
        os.path.join(path, ".probe"),
        os.path.join(path, "checkpoint"),
        os.path.join(path, "saved_model.pb"),
        os.path.join(path, "model.index"),
        os.path.join(path, "model.meta"),
    ]
    return any(os.path.exists(candidate) for candidate in required_markers)


def _sidecar_script_path() -> str:
    candidates: List[str] = []
    meipass = str(getattr(sys, "_MEIPASS", "") or "").strip()
    if meipass:
        candidates.append(os.path.join(meipass, "pyssp", "assets", "spleeter_sidecar.py"))
        candidates.append(os.path.join(meipass, "spleeter_sidecar.py"))
    module_root = Path(__file__).resolve().parent
    candidates.append(str(module_root / "assets" / "spleeter_sidecar.py"))
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return ""


def _detect_sidecar_python_command() -> List[str]:
    env_python = str(os.environ.get("PYSSP_SPLEETER_PYTHON", "")).strip()
    candidates: List[str] = []
    if env_python:
        candidates.append(env_python)
    for name in ["python3.11", "python3.10", "python311", "python310"]:
        resolved = shutil.which(name)
        if resolved:
            candidates.append(resolved)
    if os.name == "nt":
        py_launcher = shutil.which("py")
        if py_launcher:
            for version_flag in ("-3.11", "-3.10"):
                candidates.append(f"{py_launcher}|{version_flag}")
    for candidate in _unique(candidates):
        ok = _check_sidecar_candidate(candidate)
        if ok:
            return _candidate_to_python_command(candidate)
    return []


def _check_sidecar_candidate(candidate: str) -> bool:
    command = _candidate_to_python_command(candidate) + ["-c", "import spleeter; print('ok')"]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=8,
        )
    except Exception:
        return False
    return completed.returncode == 0 and "ok" in str(completed.stdout or "")


def _candidate_to_python_command(candidate: str) -> List[str]:
    if "|" in candidate:
        exe, flag = candidate.split("|", 1)
        return [exe, flag]
    return [candidate]


def _unique(values: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        token = str(value or "").strip()
        if not token:
            continue
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _ffmpeg_convert(source_wav: str, output_path: str, ext: str, ffmpeg_executable: str) -> None:
    codec_flags = _DEFAULT_CODEC_BY_EXT.get(ext, [])
    if ext in _LOSSY_EXTENSIONS and not codec_flags:
        codec_flags = ["-c:a", "libmp3lame", "-q:a", "2"]
    command = [
        ffmpeg_executable,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        source_wav,
        *codec_flags,
        output_path,
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode == 0 and os.path.exists(output_path):
        return
    raise RuntimeError((completed.stderr or completed.stdout or "ffmpeg conversion failed").strip())
