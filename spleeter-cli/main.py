from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Standalone WAV-in/WAV-out Spleeter CLI for pySSP with automatic hardware acceleration detection."
    )
    parser.add_argument("--input", required=True, help="Input WAV path")
    parser.add_argument("--output", required=True, help="Output WAV path")
    parser.add_argument("--model-root", default="", help="Optional Spleeter model root override")
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda", "metal"),
        default="auto",
        help="Execution backend. Default: auto-detect CUDA or Metal and fall back to CPU.",
    )
    args = parser.parse_args()

    input_path = str(args.input or "").strip()
    output_path = str(args.output or "").strip()
    model_root = str(args.model_root or "").strip() or _bundled_model_root()
    requested_device = str(args.device or "auto").strip().lower() or "auto"

    if not input_path or not os.path.exists(input_path):
        raise FileNotFoundError(input_path or "(missing input)")
    if not output_path:
        raise ValueError("Output path is required.")
    if Path(input_path).suffix.lower() != ".wav":
        raise ValueError("Input must be a WAV file.")
    if Path(output_path).suffix.lower() != ".wav":
        raise ValueError("Output must be a WAV file.")
    output_parent = os.path.dirname(output_path)
    if output_parent:
        os.makedirs(output_parent, exist_ok=True)

    if model_root and os.path.isdir(model_root):
        os.environ["MODEL_PATH"] = model_root
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    if requested_device == "cpu":
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

    from scipy.io import wavfile  # type: ignore
    import tensorflow as tf  # type: ignore
    from spleeter.separator import Separator  # type: ignore

    device, device_detail = _select_backend(tf, requested_device)
    _configure_backend(tf, device)
    print(f"[spleeter-cli] backend={device} detail={device_detail}", file=sys.stderr)

    sample_rate, waveform = wavfile.read(input_path)
    waveform_f32 = _to_float32_stereo(waveform)

    separator = Separator("spleeter:2stems", multiprocess=False)
    sources = separator.separate(waveform_f32, audio_descriptor=input_path)
    accompaniment = sources.get("accompaniment")
    if accompaniment is None:
        raise RuntimeError("Spleeter did not produce accompaniment output.")
    wavfile.write(output_path, int(sample_rate), _to_int16_pcm(accompaniment))
    return 0


def _select_backend(tf: Any, requested_device: str) -> tuple[str, str]:
    requested = str(requested_device or "auto").strip().lower() or "auto"
    detected, detail = _detect_backend(tf)
    if requested == "auto":
        return detected, detail
    if requested == detected:
        return detected, detail
    if requested == "cpu":
        return "cpu", "forced by --device=cpu"
    return "cpu", f"requested {requested} unavailable; {detail}"


def _detect_backend(tf: Any) -> tuple[str, str]:
    try:
        gpus = list(tf.config.list_physical_devices("GPU"))
    except Exception as exc:
        return "cpu", f"gpu detection failed: {exc}"
    if not gpus:
        return "cpu", "no GPU devices reported by TensorFlow"

    if sys.platform == "darwin":
        return "metal", _describe_devices(gpus, fallback="TensorFlow GPU available on macOS")

    if _is_cuda_build(tf):
        return "cuda", _describe_devices(gpus, fallback="CUDA-capable TensorFlow GPU available")
    return "cpu", "GPU devices reported but TensorFlow build does not appear CUDA-enabled"


def _configure_backend(tf: Any, device: str) -> None:
    if device != "cpu":
        return
    try:
        tf.config.set_visible_devices([], "GPU")
    except Exception:
        pass


def _is_cuda_build(tf: Any) -> bool:
    try:
        build_info = tf.sysconfig.get_build_info()
    except Exception:
        build_info = {}
    if not isinstance(build_info, dict):
        build_info = {}

    flags = (
        build_info.get("is_cuda_build"),
        build_info.get("cuda_version"),
        build_info.get("cudnn_version"),
        build_info.get("cuda_compute_capabilities"),
    )
    return any(bool(flag) for flag in flags)


def _describe_devices(devices: list[Any], fallback: str) -> str:
    names: list[str] = []
    for device in devices:
        name = str(getattr(device, "name", "") or "").strip()
        device_type = str(getattr(device, "device_type", "") or "").strip()
        label = name or device_type
        if label:
            names.append(label)
    return ", ".join(names) if names else fallback


def _bundled_model_root() -> str:
    candidates = []
    meipass = str(getattr(sys, "_MEIPASS", "") or "").strip()
    if meipass:
        candidates.append(os.path.join(meipass, "models"))
    candidates.append(str((Path(__file__).resolve().parent / "models").resolve()))
    for candidate in candidates:
        if os.path.isdir(os.path.join(candidate, "2stems")):
            return candidate
    return ""


def _to_float32_stereo(waveform: np.ndarray) -> np.ndarray:
    array = np.asarray(waveform)
    if array.ndim == 1:
        array = np.stack([array, array], axis=1)
    elif array.ndim == 2 and array.shape[1] == 1:
        array = np.repeat(array, 2, axis=1)
    elif array.ndim != 2:
        raise ValueError(f"Unsupported WAV shape: {array.shape}")

    if np.issubdtype(array.dtype, np.floating):
        data = array.astype(np.float32, copy=False)
    elif np.issubdtype(array.dtype, np.integer):
        info = np.iinfo(array.dtype)
        scale = float(max(abs(info.min), abs(info.max)))
        if scale <= 0:
            scale = 1.0
        data = array.astype(np.float32) / scale
    else:
        raise ValueError(f"Unsupported WAV dtype: {array.dtype}")

    return np.clip(data, -1.0, 1.0)


def _to_int16_pcm(waveform: np.ndarray) -> np.ndarray:
    data = np.asarray(waveform, dtype=np.float32)
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)
    elif data.ndim == 2 and data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    return np.clip(np.rint(data * 32767.0), -32768.0, 32767.0).astype(np.int16)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[spleeter-cli] failed: {exc}", file=sys.stderr)
        raise
