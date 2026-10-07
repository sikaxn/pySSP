## spleeter-cli

Standalone CPU-only Spleeter command-line tool for pySSP.

Purpose:
- keep Spleeter out of the main pySSP Python 3.12 runtime
- build a separate PyInstaller executable that pySSP can call
- bundle the Spleeter model with the CLI itself

Expected output:
- root `dist\spleeter-cli\`
- executable `dist\spleeter-cli\spleeter-cli.exe`
- macOS executable `dist/spleeter-cli/spleeter-cli`

Typical flow:
1. Build this CLI from a Python environment that can install Spleeter.
2. Run `spleeter-cli/build_pyinstaller.bat` on Windows or `spleeter-cli/build_pyinstaller_mac.sh` on macOS.
3. The root build copies `dist\spleeter-cli\` into the pySSP app bundle.

Notes:
- this CLI is CPU-only
- it subtracts the estimated vocals from the original waveform to create the
  vocal-removed track. The default model's accompaniment zeros frequencies above
  its modeled band (about 11 kHz at 44.1 kHz), making full-rate output sound
  bandwidth-limited. Subtraction preserves that upper band, including any vocal
  content the model cannot estimate there.
- pySSP handles ffmpeg conversion before/after this WAV-only CLI; decoding uses
  floating-point WAV without forcing a sample rate
- the input WAV's sample rate is used in the separator configuration and output;
  no stage explicitly resamples the audio
- the bundled pretrained model uses fixed STFT dimensions trained at 44.1 kHz;
  preserving other input rates does not guarantee equivalent separation quality
  (changing the configured rate does not retrain the model or scale its STFT)
- the output WAV remains 16-bit PCM; final encoding explicitly requires the
  original sample rate and fails if the codec cannot support it
- macOS Apple Silicon uses Python 3.10 plus `tensorflow-macos==2.12.0`
- `build_pyinstaller_mac.sh` will create `.venv-spleeter` and install the macOS dependency set automatically

Tests (run from the repository root):
- `.venv-spleeter/Scripts/python.exe -m unittest discover -s spleeter-cli/tests -v`
  runs standalone CLI tests without pySSP or pytest dependencies. Set
  `SPLEETER_MODEL_TEST=1` to also exercise the bundled model at 22,050 and 48,000 Hz.
- `.venv/Scripts/python.exe -m pytest spleeter-cli/tests/integration -q`
  checks pySSP's ffmpeg handoff and final encoding using the main app environment.
- On macOS/Linux, use the corresponding environment's `bin/python` path.

These changes concern generated files. pySSP playback separately converts audio
to the shared mixer/device rate; it does not modify the generated file. Rebuild
the standalone CLI and regenerate existing tracks to apply CLI changes.
