## spleeter-cli

Standalone Spleeter command-line tool for pySSP.

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
- default runtime mode is `auto`: prefer `CUDA`, then macOS `Metal`, then `CPU`
- pass `--device cpu`, `--device cuda`, or `--device metal` to override auto selection
- it writes the accompaniment stem as the vocal-removed track
- ffmpeg conversion is handled inside the CLI
- Windows native CUDA builds use Python 3.10 plus `tensorflow==2.10.1`
- Windows target machines still need the matching NVIDIA CUDA/cuDNN runtime for TensorFlow GPU to activate; otherwise the CLI falls back to CPU
- macOS Apple Silicon uses Python 3.10 plus `tensorflow-macos==2.12.0`
- macOS Apple Silicon also installs `tensorflow-metal` so TensorFlow can use the Metal backend
- `build_pyinstaller_mac.sh` will create `.venv-spleeter` and install the macOS dependency set automatically
