## spleeter-cli

Standalone CPU-only Spleeter command-line tool for pySSP.

Purpose:
- keep Spleeter out of the main pySSP Python 3.12 runtime
- build a separate PyInstaller executable that pySSP can call
- bundle the Spleeter model with the CLI itself

Expected output:
- root `dist\spleeter-cli\`
- executable `dist\spleeter-cli\spleeter-cli.exe`

Typical flow:
1. Build this CLI from a Python environment that can install Spleeter.
2. Run root `build_pyinstaller.bat`.
3. The root build copies `dist\spleeter-cli\` into the pySSP app bundle.

Notes:
- this CLI is CPU-only
- it writes the accompaniment stem as the vocal-removed track
- ffmpeg conversion is handled inside the CLI
