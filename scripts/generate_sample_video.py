from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyssp.ffmpeg_support import get_ffmpeg_executable


DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "video_samples"


@dataclass(frozen=True)
class SampleSpec:
    key: str
    filename: str
    width: int
    height: int
    fps: int
    duration_sec: int
    audio_enabled: bool
    description: str


DEFAULT_SAMPLES: tuple[SampleSpec, ...] = (
    SampleSpec(
        key="720p30-av",
        filename="pyssp_sync_720p30_av.mp4",
        width=1280,
        height=720,
        fps=30,
        duration_sec=12,
        audio_enabled=True,
        description="Baseline 720p30 sample with sync beeps.",
    ),
    SampleSpec(
        key="1080p30-av",
        filename="pyssp_sync_1080p30_av.mp4",
        width=1920,
        height=1080,
        fps=30,
        duration_sec=12,
        audio_enabled=True,
        description="Primary 1080p30 sample with sync beeps.",
    ),
    SampleSpec(
        key="1080p60-av",
        filename="pyssp_sync_1080p60_av.mp4",
        width=1920,
        height=1080,
        fps=60,
        duration_sec=12,
        audio_enabled=True,
        description="Stress sample for 60 fps playback.",
    ),
    SampleSpec(
        key="1080p30-video-only",
        filename="pyssp_sync_1080p30_video_only.mp4",
        width=1920,
        height=1080,
        fps=30,
        duration_sec=12,
        audio_enabled=False,
        description="Video-only sample for mute-path testing.",
    ),
)


def _platform_subprocess_kwargs() -> dict:
    if __import__("os").name != "nt":
        return {}
    kwargs: dict = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    try:
        startup = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
        startup.wShowWindow = 0
        kwargs["startupinfo"] = startup
    except Exception:
        pass
    return kwargs


def _escape_filter_value(value: str) -> str:
    return str(value or "").replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def _find_font_file() -> str:
    candidates = [
        Path(r"C:\Windows\Fonts\consola.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/Library/Fonts/Menlo.ttc"),
        Path("/System/Library/Fonts/Supplemental/Menlo.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return _escape_filter_value(str(candidate))
    raise RuntimeError("Could not find a usable font for FFmpeg drawtext.")


def _build_video_filter(spec: SampleSpec, font_file: str) -> str:
    title_size = max(28, spec.height // 20)
    body_size = max(22, spec.height // 28)
    return ",".join(
        [
            "format=yuv420p",
            "drawgrid=width=160:height=90:thickness=1:color=white@0.18",
            (
                "drawbox="
                "x='(iw-max(iw/9,96))*abs(sin(t*1.7))':"
                "y='ih*0.12':"
                "w='max(iw/9,96)':"
                "h='max(ih/8,72)':"
                "color=yellow@0.70:"
                "t=fill"
            ),
            "drawbox=x=0:y='ih*0.82':w=iw:h='ih*0.18':color=white@0.72:t=fill:enable='lt(mod(t,1),0.06)'",
            (
                "drawtext="
                f"fontfile='{font_file}':"
                "text='pySSP Sync Probe':"
                f"fontsize={title_size}:"
                "fontcolor=white:"
                "box=1:"
                "boxcolor=0x00000088:"
                "x=40:y=32"
            ),
            (
                "drawtext="
                f"fontfile='{font_file}':"
                f"text='Profile {spec.width}x{spec.height} @ {spec.fps} fps':"
                f"fontsize={body_size}:"
                "fontcolor=white:"
                "box=1:"
                "boxcolor=0x00000066:"
                "x=40:y=92"
            ),
            (
                "drawtext="
                f"fontfile='{font_file}':"
                "text='Frame %{n}':"
                f"fontsize={body_size}:"
                "fontcolor=white:"
                "box=1:"
                "boxcolor=0x00000066:"
                "x=40:y=140"
            ),
            (
                "drawtext="
                f"fontfile='{font_file}':"
                "text='PTS %{pts\\:hms}':"
                f"fontsize={body_size}:"
                "fontcolor=white:"
                "box=1:"
                "boxcolor=0x00000066:"
                "x=40:y=188"
            ),
            (
                "drawtext="
                f"fontfile='{font_file}':"
                "text='Flash + beep at each whole second':"
                f"fontsize={body_size}:"
                "fontcolor=white:"
                "box=1:"
                "boxcolor=0x00000066:"
                "x=40:y=236"
            ),
        ]
    )


def _run_ffmpeg(command: list[str], *, verbose: bool) -> None:
    if verbose:
        print(" ".join(command))
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **_platform_subprocess_kwargs(),
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "FFmpeg command failed").strip())


def generate_sample(spec: SampleSpec, *, output_dir: Path, overwrite: bool, verbose: bool = False) -> Path:
    ffmpeg = str(get_ffmpeg_executable() or "").strip()
    if not ffmpeg:
        raise RuntimeError("FFmpeg executable is not available.")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / spec.filename
    overwrite_args = ["-y"] if overwrite else ["-n"]
    font_file = _find_font_file()
    video_filter = _build_video_filter(spec, font_file)
    command = [
        ffmpeg,
        "-hide_banner",
        *overwrite_args,
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size={spec.width}x{spec.height}:rate={spec.fps}:duration={spec.duration_sec}",
    ]
    if spec.audio_enabled:
        command.extend(
            [
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=1320:sample_rate=48000:duration={spec.duration_sec}",
            ]
        )
    command.extend(
        [
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
        ]
    )
    if spec.audio_enabled:
        command.extend(
            [
                "-af",
                "volume='if(lt(mod(t,1),0.06),0.92,0)':eval=frame",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ac",
                "2",
            ]
        )
    else:
        command.extend(["-an"])
    command.append(str(output_path))
    _run_ffmpeg(command, verbose=verbose)
    return output_path


def generate_default_samples(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    overwrite: bool = False,
    include_soak: bool = False,
    soak_seconds: int = 180,
    verbose: bool = False,
) -> list[Path]:
    output_paths = [
        generate_sample(spec, output_dir=output_dir, overwrite=overwrite, verbose=verbose)
        for spec in DEFAULT_SAMPLES
    ]
    if include_soak:
        soak_spec = SampleSpec(
            key="720p30-av-soak",
            filename=f"pyssp_sync_720p30_av_{int(max(30, soak_seconds))}s.mp4",
            width=1280,
            height=720,
            fps=30,
            duration_sec=int(max(30, soak_seconds)),
            audio_enabled=True,
            description="Long-running 720p30 sample for soak tests.",
        )
        output_paths.append(generate_sample(soak_spec, output_dir=output_dir, overwrite=overwrite, verbose=verbose))
    return output_paths


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic pySSP video sync samples.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files.",
    )
    parser.add_argument(
        "--include-soak",
        action="store_true",
        help="Also generate a longer 720p30 soak sample.",
    )
    parser.add_argument(
        "--soak-seconds",
        type=int,
        default=180,
        help="Length of the optional soak sample in seconds.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print FFmpeg commands while generating samples.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_paths = generate_default_samples(
        output_dir=args.output_dir,
        overwrite=bool(args.overwrite),
        include_soak=bool(args.include_soak),
        soak_seconds=int(args.soak_seconds),
        verbose=bool(args.verbose),
    )
    print("Generated sample videos:")
    for path in output_paths:
        print(f"- {path}")
    print("")
    print("Playback checks:")
    print("- Flash bar and audio beep should line up on each whole second.")
    print("- Frame counter and PTS overlay should advance smoothly without stalls.")
    print("- Use the 1080p60 sample to stress-test older CPUs before enabling NDI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
