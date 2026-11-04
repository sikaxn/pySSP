"""Exercise a frozen Spleeter CLI with a short generated WAV (stdlib only)."""
from __future__ import annotations

import argparse
import array
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import wave


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    executable = args.executable.resolve(strict=True)
    rate, frame_count = 44100, 44100 * 2
    samples = array.array("h")
    for i in range(frame_count):
        value = int(3000 * math.sin(2 * math.pi * 440 * i / rate)
                    + 1000 * math.sin(2 * math.pi * 1700 * i / rate))
        samples.extend((value, value))
    if sys.byteorder != "little":
        samples.byteswap()
    with tempfile.TemporaryDirectory(prefix="pyssp-bundle-smoke-") as folder:
        source, output = Path(folder) / "input.wav", Path(folder) / "output.wav"
        with wave.open(str(source), "wb") as wav:
            wav.setparams((2, 2, rate, frame_count, "NONE", "not compressed"))
            wav.writeframes(samples.tobytes())
        env = dict(os.environ, TF_NUM_INTRAOP_THREADS="2", TF_NUM_INTEROP_THREADS="1",
                   CUDA_VISIBLE_DEVICES="-1")
        started = time.monotonic()
        subprocess.run([str(executable), "--input", str(source), "--output", str(output)],
                       env=env, check=True, timeout=args.timeout)
        with wave.open(str(output), "rb") as wav:
            actual = wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()
            assert actual == (2, 2, rate, frame_count), actual
            result = wav.readframes(frame_count)
        assert any(result), "Output is entirely silent"
        assert result != samples.tobytes(), "Model did not change the test waveform"
        print(f"PASS: frozen Spleeter model, stereo {rate} Hz, {frame_count} frames")
        print(f"Elapsed: {time.monotonic() - started:.1f} seconds")
        if sys.platform.startswith("linux"):
            import resource
            print(f"Child peak RSS: {resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024:.1f} MiB")


if __name__ == "__main__":
    main()
