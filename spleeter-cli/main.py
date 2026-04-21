from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone CPU-only WAV-in/WAV-out Spleeter CLI for pySSP.")
    parser.add_argument("--input", required=True, help="Input WAV path")
    parser.add_argument("--output", required=True, help="Output WAV path")
    parser.add_argument("--model-root", default="", help="Optional Spleeter model root override")
    args = parser.parse_args()

    input_path = str(args.input or "").strip()
    output_path = str(args.output or "").strip()
    model_root = str(args.model_root or "").strip() or _bundled_model_root()

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
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

    from scipy.io import wavfile  # type: ignore
    import tensorflow as tf  # type: ignore
    from spleeter.separator import Separator  # type: ignore

    try:
        tf.config.set_visible_devices([], "GPU")
    except Exception:
        pass

    sample_rate, waveform = wavfile.read(input_path)
    waveform_f32 = _to_float32_stereo(waveform)

    separator = Separator("spleeter:2stems")
    sources = separator.separate(waveform_f32, audio_descriptor=input_path)
    accompaniment = sources.get("accompaniment")
    if accompaniment is None:
        raise RuntimeError("Spleeter did not produce accompaniment output.")
    wavfile.write(output_path, int(sample_rate), _to_int16_pcm(accompaniment))
    return 0


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
