from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LOSSY_EXTENSIONS = {".mp3", ".m4a", ".aac", ".ogg", ".wma"}
DEFAULT_CODEC_BY_EXT = {
    ".mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    ".m4a": ["-c:a", "aac", "-b:a", "256k"],
    ".aac": ["-c:a", "aac", "-b:a", "256k"],
    ".ogg": ["-c:a", "libvorbis", "-q:a", "5"],
    ".flac": ["-c:a", "flac"],
    ".wav": ["-c:a", "pcm_s16le"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="pySSP sidecar vocal removal with Spleeter.")
    parser.add_argument("--input", required=True, help="Input audio path")
    parser.add_argument("--output", required=True, help="Output audio path")
    parser.add_argument("--ffmpeg", default="", help="Optional ffmpeg executable path")
    parser.add_argument("--model-root", default="", help="Optional Spleeter model root path")
    args = parser.parse_args()

    input_path = str(args.input or "").strip()
    output_path = str(args.output or "").strip()
    ffmpeg_path = str(args.ffmpeg or "").strip()
    model_root = str(args.model_root or "").strip()

    if not input_path or not os.path.exists(input_path):
        raise FileNotFoundError(input_path or "(missing input)")
    if not output_path:
        raise ValueError("Output path is required.")
    output_parent = os.path.dirname(output_path)
    if output_parent:
        os.makedirs(output_parent, exist_ok=True)

    if model_root and os.path.isdir(model_root):
        os.environ["MODEL_PATH"] = model_root
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    _prepend_bundled_ffmpeg_dir(_resolve_bundled_ffmpeg_dir())

    import tensorflow as tf  # type: ignore
    from spleeter.separator import Separator  # type: ignore

    try:
        tf.config.set_visible_devices([], "GPU")
    except Exception:
        pass

    output_ext = os.path.splitext(output_path)[1].lower()
    with tempfile.TemporaryDirectory(prefix="pyssp_spleeter_sidecar_") as temp_dir:
        separator = Separator("spleeter:2stems")
        separator.separate_to_file(
            input_path,
            temp_dir,
            codec="wav",
            filename_format="{filename}/{instrument}.{codec}",
            synchronous=True,
        )
        base_name = Path(input_path).stem
        accompaniment_path = os.path.join(temp_dir, base_name, "accompaniment.wav")
        if not os.path.exists(accompaniment_path):
            raise RuntimeError("Spleeter did not generate accompaniment.wav")
        if output_ext in {"", ".wav"}:
            shutil.copyfile(accompaniment_path, output_path)
            return 0
        ffmpeg_path = _resolve_ffmpeg_path(ffmpeg_path)
        if ffmpeg_path:
            _ffmpeg_convert(accompaniment_path, output_path, output_ext, ffmpeg_path)
            return 0
        fallback = os.path.splitext(output_path)[0] + ".wav"
        shutil.copyfile(accompaniment_path, fallback)
        print(f"[pySSP] ffmpeg missing; wrote WAV fallback: {fallback}")
    return 0


def _ffmpeg_convert(source_wav: str, output_path: str, ext: str, ffmpeg_executable: str) -> None:
    codec_flags = DEFAULT_CODEC_BY_EXT.get(ext, [])
    if ext in LOSSY_EXTENSIONS and not codec_flags:
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


def _resolve_ffmpeg_path(preferred: str) -> str:
    path = str(preferred or "").strip()
    if path and os.path.exists(path):
        return path
    try:
        import imageio_ffmpeg  # type: ignore

        candidate = str(imageio_ffmpeg.get_ffmpeg_exe() or "").strip()
        if candidate and os.path.exists(candidate):
            return candidate
    except Exception:
        pass
    system_path = shutil.which("ffmpeg") or ""
    if system_path and os.path.exists(system_path):
        return system_path
    return ""


def _resolve_bundled_ffmpeg_dir() -> str:
    candidates = []
    script_dir = Path(__file__).resolve().parent
    candidates.append(str((script_dir.parent / "bin").resolve()))
    candidates.append(str((script_dir / "bin").resolve()))
    for candidate in candidates:
        ffmpeg_path = os.path.join(candidate, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        ffprobe_path = os.path.join(candidate, "ffprobe.exe" if os.name == "nt" else "ffprobe")
        if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
            return candidate
    return ""


def _prepend_bundled_ffmpeg_dir(directory: str) -> None:
    path = str(directory or "").strip()
    if not path or not os.path.isdir(path):
        return
    current = str(os.environ.get("PATH", "") or "")
    entries = current.split(os.pathsep) if current else []
    normalized = [os.path.normcase(os.path.abspath(entry)) for entry in entries if entry]
    target = os.path.normcase(os.path.abspath(path))
    if target in normalized:
        return
    os.environ["PATH"] = path + (os.pathsep + current if current else "")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[pySSP] sidecar failed: {exc}", file=sys.stderr)
        raise
