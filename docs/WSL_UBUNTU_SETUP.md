# pySSP on Ubuntu WSL

This guide covers a clean Ubuntu WSL setup for running and testing `pySSP`.

## What this uses

- `Ubuntu 24.04` on `WSL2`
- `python3` from Ubuntu
- A separate Linux virtual environment at `.venv-wsl`

Do not reuse the checked-in Windows `.venv` from WSL. It is not compatible with Ubuntu.

## Install Ubuntu packages

Open Ubuntu in WSL and install the required packages:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv python3.12-venv libasound2t64 libportaudio2 libegl1 libgl1
sudo apt install -y libpulse0 libasound2-plugins libsdl2-2.0-0 pulseaudio-utils
```

Notes:

- On Ubuntu `24.04`, `libasound2` was replaced by `libasound2t64`.
- `WSLg` is recommended if you want to open the PyQt GUI from Ubuntu.
- `libpulse0` and `libasound2-plugins` matter for audio playback in WSL. Without them, `pygame` and `sounddevice` may initialize with no usable output device.
- If Qt reports that `xcb` was found but could not be loaded, install the extra runtime libraries:

```bash
sudo apt install -y libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0
```

## Open the repo from Ubuntu

If this repository lives on your Windows filesystem, the path from Ubuntu will look like this:

```bash
cd /mnt/c/Users/Nathan/Documents/GitHub/pySSP
```

## WSL launcher script

Use the WSL-specific launcher:

```bash
chmod +x run_ssp_wsl.sh
./run_ssp_wsl.sh setup
```

The script:

- Creates `.venv-wsl` if it does not exist
- Installs `requirements.txt` into `.venv-wsl`
- Keeps the WSL environment separate from the Windows `.venv`
- Detects `/mnt/wslg` and exports the Qt/Wayland environment automatically when WSLg sockets exist but the shell variables are missing
- Exports `PULSE_SERVER` and `SDL_AUDIODRIVER=pulseaudio` under WSLg so `pygame` and `sounddevice` target the WSL audio sink consistently
- Forces Qt and Mesa software rendering under WSLg by default to avoid common `ZINK` / `dri2` startup warnings
- Seeds first-run startup language to English in the WSL launcher so the app does not stall on a hidden first-run language dialog before the main window appears

## Run the app

```bash
./run_ssp_wsl.sh
```

You can pass normal app flags through to `main.py`:

```bash
./run_ssp_wsl.sh run --cleanstart
./run_ssp_wsl.sh run --debug
```

## Run tests

The WSL script forces Qt into offscreen mode for tests:

```bash
./run_ssp_wsl.sh test
```

You can also target specific tests:

```bash
./run_ssp_wsl.sh test test_http_5050_server.py
```

## Why not use `run_ssp_venv.sh`?

`run_ssp_venv.sh` expects a Linux `.venv` at `.venv/bin/python` and also checks for a Linux `spleeter-cli` binary before launching. This repo currently includes a Windows `dist/spleeter-cli/spleeter-cli.exe`, which does not run inside Ubuntu WSL.

`run_ssp_wsl.sh` avoids that blocker so the main app can still launch and tests can still run.

## Current limitation

The vocal-removal feature depends on a Linux `spleeter-cli` build. Until the repo has `dist/spleeter-cli/spleeter-cli` for Linux, that feature will be unavailable in Ubuntu WSL even though the rest of the app can run.

## Troubleshooting

If `python3 -m venv` fails:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv python3.12-venv
```

If the GUI does not open:

- Start Ubuntu from a normal WSLg-enabled Windows Terminal session
- Check that `echo $DISPLAY` or `echo $WAYLAND_DISPLAY` returns a value
- Run `./run_ssp_wsl.sh` rather than `python main.py` directly so the script can reconstruct the WSLg environment
- Use `./run_ssp_wsl.sh test` to verify the Python environment even if GUI forwarding is unavailable

If you launch `python main.py` directly and see:

```text
MESA: error: ZINK: failed to choose pdev
glx: failed to create drisw screen
```

use the WSL launcher instead, or export the same software-rendering variables manually:

```bash
export QT_QPA_PLATFORM=wayland
export QT_OPENGL=software
export LIBGL_ALWAYS_SOFTWARE=1
python main.py
```

If the app opens but no sound plays:

- Re-run `./run_ssp_wsl.sh` after installing the audio packages above
- Check that `pactl info` reports `Default Sink: RDPSink`
- Check that `pactl list short sinks` shows `RDPSink`
- In `pySSP` options, leave `audio_output_device` on the default device unless you have a confirmed alternate output listed
