from __future__ import annotations

import argparse
import ctypes as C
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


class NDIlib_source_t(C.Structure):
    _fields_ = [
        ("p_ndi_name", C.c_char_p),
        ("p_url_address", C.c_char_p),
    ]


class NDIlib_find_create_t(C.Structure):
    _fields_ = [
        ("show_local_sources", C.c_bool),
        ("p_groups", C.c_char_p),
        ("p_extra_ips", C.c_char_p),
    ]


class NDIlib_recv_create_v3_t(C.Structure):
    _fields_ = [
        ("source_to_connect_to", NDIlib_source_t),
        ("color_format", C.c_int),
        ("bandwidth", C.c_int),
        ("allow_video_fields", C.c_bool),
        ("p_ndi_recv_name", C.c_char_p),
    ]


class NDIlib_audio_frame_v3_t(C.Structure):
    _fields_ = [
        ("sample_rate", C.c_int),
        ("no_channels", C.c_int),
        ("no_samples", C.c_int),
        ("timecode", C.c_longlong),
        ("FourCC", C.c_int),
        ("p_data", C.POINTER(C.c_uint8)),
        ("channel_stride_in_bytes", C.c_int),
        ("p_metadata", C.c_char_p),
        ("timestamp", C.c_longlong),
    ]


class NDIlib_recv_performance_t(C.Structure):
    _fields_ = [
        ("video_frames", C.c_longlong),
        ("audio_frames", C.c_longlong),
        ("metadata_frames", C.c_longlong),
    ]


class NDIlib_recv_queue_t(C.Structure):
    _fields_ = [
        ("video_frames", C.c_int),
        ("audio_frames", C.c_int),
        ("metadata_frames", C.c_int),
    ]


@dataclass
class ProbeStats:
    expected_ms: float | None
    audio_frames: int
    none_frames: int
    silent_frames: int
    timestamp_undefined: int
    peak_max: float
    sample_counts: dict[int, int]
    wall_dt: dict[str, float | int] | None
    sender_dt: dict[str, float | int] | None
    sender_skew_ms: dict[str, float] | None
    queue_audio_max: int
    queue_audio_nonzero_polls: int
    queue_histogram_top: list[tuple[int, int]]
    perf_total_delta: dict[str, int]
    perf_drop_delta: dict[str, int]
    rounded_sender_dt_histogram_top: list[tuple[int, int]]
    sender_dt_band_counts: dict[str, int]


def _default_runtime_path() -> str:
    candidates = [
        Path(r"C:\Program Files\NDI\NDI 6 Runtime\v6\Processing.NDI.Lib.x64.dll"),
        Path(r"C:\Program Files\NDI\NDI 5 Runtime\v5\Processing.NDI.Lib.x64.dll"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return str(candidates[0])


def _bind(lib: C.WinDLL) -> None:
    lib.NDIlib_initialize.argtypes = []
    lib.NDIlib_initialize.restype = C.c_bool
    lib.NDIlib_destroy.argtypes = []
    lib.NDIlib_destroy.restype = None
    lib.NDIlib_find_create_v2.argtypes = [C.POINTER(NDIlib_find_create_t)]
    lib.NDIlib_find_create_v2.restype = C.c_void_p
    lib.NDIlib_find_wait_for_sources.argtypes = [C.c_void_p, C.c_uint32]
    lib.NDIlib_find_wait_for_sources.restype = C.c_bool
    lib.NDIlib_find_get_current_sources.argtypes = [C.c_void_p, C.POINTER(C.c_uint32)]
    lib.NDIlib_find_get_current_sources.restype = C.POINTER(NDIlib_source_t)
    lib.NDIlib_find_destroy.argtypes = [C.c_void_p]
    lib.NDIlib_find_destroy.restype = None
    lib.NDIlib_recv_create_v3.argtypes = [C.POINTER(NDIlib_recv_create_v3_t)]
    lib.NDIlib_recv_create_v3.restype = C.c_void_p
    lib.NDIlib_recv_capture_v3.argtypes = [
        C.c_void_p,
        C.c_void_p,
        C.POINTER(NDIlib_audio_frame_v3_t),
        C.c_void_p,
        C.c_uint32,
    ]
    lib.NDIlib_recv_capture_v3.restype = C.c_int
    lib.NDIlib_recv_free_audio_v3.argtypes = [C.c_void_p, C.POINTER(NDIlib_audio_frame_v3_t)]
    lib.NDIlib_recv_free_audio_v3.restype = None
    lib.NDIlib_recv_destroy.argtypes = [C.c_void_p]
    lib.NDIlib_recv_destroy.restype = None
    lib.NDIlib_recv_get_performance.argtypes = [
        C.c_void_p,
        C.POINTER(NDIlib_recv_performance_t),
        C.POINTER(NDIlib_recv_performance_t),
    ]
    lib.NDIlib_recv_get_performance.restype = None
    lib.NDIlib_recv_get_queue.argtypes = [C.c_void_p, C.POINTER(NDIlib_recv_queue_t)]
    lib.NDIlib_recv_get_queue.restype = None


def _stats(values: list[float], expected_ms: float | None) -> dict[str, float | int] | None:
    if not values:
        return None
    return {
        "count": len(values),
        "avg_ms": round(statistics.mean(values), 3),
        "stdev_ms": round(statistics.pstdev(values), 3),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
        "over_1_5x_expected": sum(1 for value in values if expected_ms and value > expected_ms * 1.5),
        "over_2x_expected": sum(1 for value in values if expected_ms and value > expected_ms * 2.0),
    }


def _find_source(lib: C.WinDLL, source_substring: str, timeout_sec: float) -> tuple[C.c_void_p, NDIlib_source_t]:
    finder = lib.NDIlib_find_create_v2(C.byref(NDIlib_find_create_t(True, None, None)))
    if not finder:
        raise RuntimeError("NDI finder create failed")
    deadline = time.time() + max(1.0, float(timeout_sec))
    source = None
    try:
        while time.time() < deadline:
            lib.NDIlib_find_wait_for_sources(finder, 1000)
            count = C.c_uint32()
            ptr = lib.NDIlib_find_get_current_sources(finder, C.byref(count))
            for index in range(count.value):
                name = ptr[index].p_ndi_name.decode("utf-8", errors="ignore") if ptr[index].p_ndi_name else ""
                if source_substring.lower() in name.lower():
                    source = NDIlib_source_t(ptr[index].p_ndi_name, ptr[index].p_url_address)
                    return finder, source
        raise RuntimeError(f"Could not find NDI source containing '{source_substring}'")
    except Exception:
        lib.NDIlib_find_destroy(finder)
        raise


def run_probe(
    runtime_path: str,
    *,
    source_substring: str,
    duration_sec: float,
    finder_timeout_sec: float,
    recv_name: str,
    queue_poll_interval_sec: float,
) -> tuple[str, ProbeStats]:
    lib = C.WinDLL(runtime_path)
    _bind(lib)
    if not lib.NDIlib_initialize():
        raise RuntimeError("NDIlib_initialize failed")

    finder = None
    recv = None
    try:
        finder, source = _find_source(lib, source_substring, finder_timeout_sec)
        recv_cfg = NDIlib_recv_create_v3_t(
            source_to_connect_to=source,
            color_format=0,
            bandwidth=10,
            allow_video_fields=False,
            p_ndi_recv_name=recv_name.encode("utf-8", errors="ignore"),
        )
        recv = lib.NDIlib_recv_create_v3(C.byref(recv_cfg))
        if not recv:
            raise RuntimeError("NDI receiver create failed")

        source_name = source.p_ndi_name.decode("utf-8", errors="ignore") if source.p_ndi_name else ""
        expected_ms = None
        last_wall = None
        last_sender_ts = None
        wall_dts: list[float] = []
        sender_dts: list[float] = []
        sender_skew: list[float] = []
        sample_counts: Counter[int] = Counter()
        queue_histogram: Counter[int] = Counter()
        sender_dt_rounded: Counter[int] = Counter()
        queue_audio_max = 0
        queue_audio_nonzero = 0
        audio_frames = 0
        none_frames = 0
        silent_frames = 0
        timestamp_undefined = 0
        peak_max = 0.0

        perf_total_start = NDIlib_recv_performance_t()
        perf_drop_start = NDIlib_recv_performance_t()
        lib.NDIlib_recv_get_performance(recv, C.byref(perf_total_start), C.byref(perf_drop_start))

        start = time.time()
        next_queue_poll = start
        while time.time() - start < duration_sec:
            now = time.time()
            if now >= next_queue_poll:
                queue = NDIlib_recv_queue_t()
                lib.NDIlib_recv_get_queue(recv, C.byref(queue))
                queue_histogram[queue.audio_frames] += 1
                queue_audio_max = max(queue_audio_max, int(queue.audio_frames))
                if queue.audio_frames > 0:
                    queue_audio_nonzero += 1
                next_queue_poll = now + max(0.01, float(queue_poll_interval_sec))

            audio_frame = NDIlib_audio_frame_v3_t()
            frame_type = lib.NDIlib_recv_capture_v3(recv, None, C.byref(audio_frame), None, 100)
            wall = time.perf_counter()
            if frame_type == 2:
                audio_frames += 1
                sample_counts[audio_frame.no_samples] += 1
                if expected_ms is None and audio_frame.sample_rate and audio_frame.no_samples:
                    expected_ms = audio_frame.no_samples / audio_frame.sample_rate * 1000.0
                if last_wall is not None:
                    wall_dts.append((wall - last_wall) * 1000.0)
                last_wall = wall
                if audio_frame.timestamp < 0:
                    timestamp_undefined += 1
                elif last_sender_ts is not None:
                    dt_ms = (audio_frame.timestamp - last_sender_ts) / 10000.0
                    sender_dts.append(dt_ms)
                    sender_dt_rounded[round(dt_ms)] += 1
                    if expected_ms is not None:
                        sender_skew.append(dt_ms - expected_ms)
                if audio_frame.timestamp >= 0:
                    last_sender_ts = audio_frame.timestamp
                if audio_frame.p_data and audio_frame.no_channels > 0 and audio_frame.no_samples > 0:
                    total_floats = audio_frame.no_channels * audio_frame.no_samples
                    float_ptr = C.cast(audio_frame.p_data, C.POINTER(C.c_float))
                    peak = 0.0
                    for index in range(min(total_floats, 4096)):
                        value = abs(float_ptr[index])
                        if value > peak:
                            peak = value
                    peak_max = max(peak_max, peak)
                    if peak < 1e-6:
                        silent_frames += 1
                lib.NDIlib_recv_free_audio_v3(recv, C.byref(audio_frame))
            elif frame_type == 0:
                none_frames += 1

        perf_total_end = NDIlib_recv_performance_t()
        perf_drop_end = NDIlib_recv_performance_t()
        lib.NDIlib_recv_get_performance(recv, C.byref(perf_total_end), C.byref(perf_drop_end))

        sender_skew_stats = None
        if sender_skew:
            sender_skew_stats = {
                "avg": round(statistics.mean(sender_skew), 3),
                "stdev": round(statistics.pstdev(sender_skew), 3),
                "min": round(min(sender_skew), 3),
                "max": round(max(sender_skew), 3),
            }

        band_counts = {
            "lt5ms": sum(1 for value in sender_dts if value < 5.0),
            "18to25ms": sum(1 for value in sender_dts if 18.0 <= value <= 25.0),
            "38to48ms": sum(1 for value in sender_dts if 38.0 <= value <= 48.0),
            "total": len(sender_dts),
        }

        return source_name, ProbeStats(
            expected_ms=round(expected_ms, 3) if expected_ms is not None else None,
            audio_frames=audio_frames,
            none_frames=none_frames,
            silent_frames=silent_frames,
            timestamp_undefined=timestamp_undefined,
            peak_max=round(peak_max, 6),
            sample_counts=dict(sample_counts),
            wall_dt=_stats(wall_dts, expected_ms),
            sender_dt=_stats(sender_dts, expected_ms),
            sender_skew_ms=sender_skew_stats,
            queue_audio_max=queue_audio_max,
            queue_audio_nonzero_polls=queue_audio_nonzero,
            queue_histogram_top=queue_histogram.most_common(10),
            perf_total_delta={
                "audio": int(perf_total_end.audio_frames - perf_total_start.audio_frames),
                "video": int(perf_total_end.video_frames - perf_total_start.video_frames),
                "metadata": int(perf_total_end.metadata_frames - perf_total_start.metadata_frames),
            },
            perf_drop_delta={
                "audio": int(perf_drop_end.audio_frames - perf_drop_start.audio_frames),
                "video": int(perf_drop_end.video_frames - perf_drop_start.video_frames),
                "metadata": int(perf_drop_end.metadata_frames - perf_drop_start.metadata_frames),
            },
            rounded_sender_dt_histogram_top=sender_dt_rounded.most_common(10),
            sender_dt_band_counts=band_counts,
        )
    finally:
        if recv:
            lib.NDIlib_recv_destroy(recv)
        if finder:
            lib.NDIlib_find_destroy(finder)
        lib.NDIlib_destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe an NDI audio source and report cadence/jitter metrics.")
    parser.add_argument("--runtime-path", default=_default_runtime_path(), help="Path to Processing.NDI.Lib.x64.dll")
    parser.add_argument("--source", default="pyssp-video", help="Case-insensitive substring to match source name")
    parser.add_argument("--duration", type=float, default=30.0, help="Probe duration in seconds")
    parser.add_argument("--find-timeout", type=float, default=10.0, help="Source discovery timeout in seconds")
    parser.add_argument("--recv-name", default="codex-audio-probe", help="NDI receiver name to present to the runtime")
    parser.add_argument("--queue-poll-interval", type=float, default=0.1, help="Seconds between queue depth samples")
    args = parser.parse_args()

    source_name, stats = run_probe(
        args.runtime_path,
        source_substring=args.source,
        duration_sec=args.duration,
        finder_timeout_sec=args.find_timeout,
        recv_name=args.recv_name,
        queue_poll_interval_sec=args.queue_poll_interval,
    )
    print("source", source_name)
    print("expected_ms", stats.expected_ms)
    print("audio_frames", stats.audio_frames)
    print("none_frames", stats.none_frames)
    print("sample_counts", stats.sample_counts)
    print("silent_frames", stats.silent_frames)
    print("timestamp_undefined", stats.timestamp_undefined)
    print("peak_max", stats.peak_max)
    print("wall_dt", stats.wall_dt)
    print("sender_dt", stats.sender_dt)
    print("sender_skew_ms", stats.sender_skew_ms)
    print("queue_audio_max", stats.queue_audio_max)
    print("queue_audio_nonzero_polls", stats.queue_audio_nonzero_polls)
    print("queue_histogram_top", stats.queue_histogram_top)
    print("perf_total_delta", stats.perf_total_delta)
    print("perf_drop_delta", stats.perf_drop_delta)
    print("rounded_sender_dt_histogram_top", stats.rounded_sender_dt_histogram_top)
    print("sender_dt_band_counts", stats.sender_dt_band_counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
