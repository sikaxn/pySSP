from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
for candidate in (REPO_ROOT, SCRIPT_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import generate_sample_video as sample_video
from pyssp.ffmpeg_support import MediaProbeInfo, probe_media_info
from pyssp.engine import video_session as video_session_module


DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "video_samples"


@contextmanager
def _forced_backend(mode: str):
    original_pyav = video_session_module._pyav
    if mode == "ffmpeg":
        video_session_module._pyav = None
    elif mode == "pyav" and original_pyav is None:
        raise RuntimeError("PyAV is not available on this machine.")
    try:
        yield
    finally:
        video_session_module._pyav = original_pyav


def _pick_sample(sample_key: str) -> sample_video.SampleSpec:
    for spec in sample_video.DEFAULT_SAMPLES:
        if spec.key == sample_key:
            return spec
    raise ValueError(f"Unknown sample key: {sample_key}")


def _resolve_input_path(args: argparse.Namespace) -> Path:
    if args.path is not None:
        return Path(args.path).resolve()
    spec = _pick_sample(str(args.sample))
    generated = sample_video.generate_sample(
        spec,
        output_dir=Path(args.output_dir),
        overwrite=bool(args.overwrite),
        verbose=bool(args.verbose),
    )
    return generated.resolve()


def _benchmark_dimensions(info: MediaProbeInfo, args: argparse.Namespace) -> tuple[int, int]:
    width = int(args.width or 0)
    height = int(args.height or 0)
    if width > 0 and height > 0:
        return width, height
    width = max(2, int(getattr(info, "width", 0) or 0))
    height = max(2, int(getattr(info, "height", 0) or 0))
    if width <= 0 or height <= 0:
        return 1280, 720
    return width, height


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * percentile))))
    return float(ordered[index])


def run_benchmark(args: argparse.Namespace) -> int:
    input_path = _resolve_input_path(args)
    if not input_path.exists():
        raise RuntimeError(f"Input video was not found: {input_path}")
    info = probe_media_info(str(input_path))
    width, height = _benchmark_dimensions(info, args)
    target_fps = float(args.fps or 0.0)
    if target_fps <= 0.0:
        target_fps = float(getattr(info, "fps", 0.0) or 0.0) or 30.0
    target_fps = max(1.0, min(120.0, target_fps))
    frame_budget_ms = 1000.0 / target_fps
    max_duration_ms = int(getattr(info, "duration_ms", 0) or 0)
    benchmark_seconds = float(args.seconds or 0.0)
    if benchmark_seconds <= 0.0:
        benchmark_seconds = min(12.0, max_duration_ms / 1000.0 if max_duration_ms > 0 else 12.0)
    frame_count = max(1, int(round(benchmark_seconds * target_fps)))
    frame_step_ms = max(1, int(round(1000.0 / target_fps)))

    latencies_ms: list[float] = []
    pts_drifts_ms: list[float] = []
    late_frames = 0
    decode_failures = 0

    with _forced_backend(str(args.backend)):
        frame_source = video_session_module._create_frame_source(str(input_path), width, height)
    try:
        backend_name = str(getattr(frame_source, "backend_name", "") or "unknown")
        for frame_index in range(frame_count):
            target_ms = frame_index * frame_step_ms
            if max_duration_ms > 0:
                target_ms = min(target_ms, max(0, max_duration_ms - frame_step_ms))
            start = time.perf_counter()
            try:
                image, pts_ms = frame_source.frame_at(target_ms)
            except Exception:
                decode_failures += 1
                continue
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies_ms.append(elapsed_ms)
            pts_drifts_ms.append(abs(float(pts_ms) - float(target_ms)))
            if elapsed_ms > frame_budget_ms:
                late_frames += 1
            if image.isNull():
                decode_failures += 1
    finally:
        close = getattr(frame_source, "close", None)
        if callable(close):
            close()

    if not latencies_ms:
        raise RuntimeError("No frames were decoded during the benchmark.")

    print(f"Input: {input_path}")
    print(f"Backend: {backend_name}")
    print(f"Decode size: {width}x{height}")
    print(f"Target cadence: {target_fps:.2f} fps ({frame_budget_ms:.2f} ms budget)")
    print(f"Frames requested: {frame_count}")
    print(f"Decode failures: {decode_failures}")
    print(f"Late frames: {late_frames} / {len(latencies_ms)}")
    print(f"Mean decode: {statistics.fmean(latencies_ms):.2f} ms")
    print(f"P95 decode: {_percentile(latencies_ms, 0.95):.2f} ms")
    print(f"Max decode: {max(latencies_ms):.2f} ms")
    print(f"Mean PTS drift: {statistics.fmean(pts_drifts_ms):.2f} ms")
    print(f"P95 PTS drift: {_percentile(pts_drifts_ms, 0.95):.2f} ms")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark pySSP video decode backends on a local machine.")
    parser.add_argument("path", nargs="?", help="Optional path to an existing sample video.")
    parser.add_argument(
        "--sample",
        default="720p30-av",
        choices=[spec.key for spec in sample_video.DEFAULT_SAMPLES],
        help="Sample profile to auto-generate when no path is provided.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Auto-generated sample directory. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the auto-generated sample when needed.",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "pyav", "ffmpeg"),
        default="auto",
        help="Decode backend to benchmark.",
    )
    parser.add_argument("--width", type=int, default=0, help="Decode width override.")
    parser.add_argument("--height", type=int, default=0, help="Decode height override.")
    parser.add_argument("--fps", type=float, default=0.0, help="Target playback fps override.")
    parser.add_argument("--seconds", type=float, default=0.0, help="How long to benchmark.")
    parser.add_argument("--verbose", action="store_true", help="Print sample-generation FFmpeg commands.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    return run_benchmark(args)


if __name__ == "__main__":
    raise SystemExit(main())
