# Raspberry Pi installation

This guide records the source installation tested on October 7, 2026, including
the adjustments needed for the Pi's Python version. It is a tested configuration,
not a packaged Raspberry Pi release or a claim that every feature works on Linux.

## Tested configuration

| Component | Installed configuration |
| --- | --- |
| Hardware | Raspberry Pi 4 Model B Rev 1.2, approximately 2 GB RAM |
| OS | 64-bit Debian 13 (trixie), aarch64 |
| Desktop | Existing Wayland session, with XWayland display `:0` |
| Account and host | `ubuntu` at `10.0.0.166` |
| Python | 3.13.5 |
| Source | Local branch `vocal_removal_sample_rate_fix`, commit `cd72856`, plus the fullscreen changes |
| Configured version | `1.1.4b1` in `version.json` |
| Application directory | `/home/ubuntu/pySSP` |
| Virtual environment | `/home/ubuntu/pyssp-venv`, also linked as `pySSP/.venv` |

The local branch was newer than the GitHub default branch at installation time.
The source was copied from the working tree so the uncommitted fullscreen changes
were included. Source runs deliberately display `0.0.0 dev` in the title bar;
this does not identify which source commit was installed.

## Connect and check the machine

From another computer:

```sh
ssh ubuntu@10.0.0.166
```

Use the account's password when prompted. Credentials are not stored in this guide.
The original Windows installation session used PuTTY's `plink` and `pscp` for SSH
and file transfer; OpenSSH can perform the equivalent steps below.

On the Pi, inspect the environment before installing:

```sh
uname -m
cat /etc/os-release
python3 --version
df -h /
free -h
loginctl list-sessions
systemctl --user show-environment | grep -E 'DISPLAY|WAYLAND|XDG_RUNTIME'
```

The tested machine already had a logged-in desktop, Git, FFmpeg, Python's venv
support, development headers, and system PyQt5. Only `libportaudio2` needed to be
added from apt. For a similar machine, ensure the prerequisites are present:

```sh
sudo apt-get update
sudo apt-get install -y git ffmpeg python3-venv python3-dev python3-pyqt5 libportaudio2
```

## Copy the intended source

For the tested installation, a ZIP contained the working-tree contents of all
Git-tracked files, plus the new fullscreen test. It excluded local virtual
environments and `.git`. This preserves edits that `git archive HEAD` would omit.

To create the same kind of snapshot, run this Python code from the source
repository on the development computer:

```python
from pathlib import Path
import subprocess
import tempfile
import zipfile

destination = Path(tempfile.gettempdir()) / "pyssp-pi-install.zip"
tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
files = {name for name in tracked if name and Path(name).is_file()}
extra = Path("tests/test_main_window_fullscreen.py")
if extra.is_file():
    files.add(extra.as_posix())
with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
    for name in sorted(files):
        archive.write(name, name)
print(destination)
```

Transfer the resulting file, substituting the printed local path:

```sh
scp /path/to/pyssp-pi-install.zip ubuntu@10.0.0.166:/home/ubuntu/
```

On the Pi, extract into a new directory:

```sh
test ! -e "$HOME/pySSP" && mkdir "$HOME/pySSP" && \
    python3 -m zipfile -e "$HOME/pyssp-pi-install.zip" "$HOME/pySSP"
```

If `~/pySSP` already exists, stop and decide how to preserve that installation
before replacing it. This snapshot is not a Git checkout, so `git pull` cannot
update it. Future updates need another source transfer or a separate Git checkout.

## Install the Python runtime

The repository targets Python 3.12 and pins `pedalboard==0.9.6`. That version was
not available as a wheel for the Pi's Python 3.13. The tested installation used
`pedalboard==0.9.26` instead, without changing the repository's requirements file.

Create a venv that can use Debian's PyQt5 and NumPy packages:

```sh
python3 -m venv --system-site-packages "$HOME/pyssp-venv"
ln -s "$HOME/pyssp-venv" "$HOME/pySSP/.venv"
```

Install the runtime packages and pytest. These are the direct package versions
used in the successful installation; NumPy 2.2.4 and PyQt5 5.15.11 came from Debian:

```sh
~/pyssp-venv/bin/pip install --only-binary=:all: \
    'pygame-ce==2.5.8' 'numpy>=1.26' 'sounddevice==0.5.6' \
    'pedalboard==0.9.26' 'Flask==3.1.3' 'simple-websocket==1.1.0' \
    'websockets==17.2' 'Werkzeug==3.1.9' 'imageio-ffmpeg==0.6.0' \
    'pytest==9.1.1'
```

The first attempt to launch `main.py` failed because `system_info_probe.py` imports
`aifc`, which is absent from Python 3.13. Installing its compatibility package fixed
the entry point. `standard-sunau` was also installed, although no missing `sunau`
error was observed:

```sh
~/pyssp-venv/bin/pip install 'standard-aifc==3.13.0' 'standard-sunau==3.13.0'
cd ~/pySSP
.venv/bin/python -c 'import pyssp.app; print("Entry point import OK")'
.venv/bin/pip freeze --local > installed-packages.txt
```

`standard-aifc` also installed `standard-chunk` and `audioop-lts`. The package
record above captures venv-local packages, not the inherited Debian packages.
Pip reported an unrelated inherited `types-flask-migrate` dependency warning;
the pySSP checks below passed despite it.

Build and documentation dependencies such as PyInstaller and Sphinx were not
installed on the Pi. The optional `spleeter-cli` vocal-separation backend was not
installed either.

## Create the launcher and desktop shortcut

The existing `run_ssp_venv.sh` stopped if `spleeter-cli` was missing and offered to
run a Windows batch build through `cmd.exe`. A dedicated launcher avoided this
blocker for the main application:

```sh
mkdir -p ~/.local/bin ~/.local/share/applications ~/Desktop
cat > ~/.local/bin/pyssp <<'EOF'
#!/bin/sh
cd /home/ubuntu/pySSP || exit 1
export QT_QPA_PLATFORM=xcb
export ALSA_CONFIG_PATH=/usr/share/alsa/alsa.conf
exec /home/ubuntu/pyssp-venv/bin/python /home/ubuntu/pySSP/main.py "$@"
EOF
chmod +x ~/.local/bin/pyssp

cat > ~/.local/share/applications/pyssp.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=pySSP
Comment=pySSP soundboard
Exec=/home/ubuntu/.local/bin/pyssp
Path=/home/ubuntu/pySSP
Icon=/home/ubuntu/pySSP/logo.png
Terminal=false
Categories=AudioVideo;Audio;
StartupNotify=true
EOF
cp ~/.local/share/applications/pyssp.desktop ~/Desktop/pyssp.desktop
chmod +x ~/.local/share/applications/pyssp.desktop ~/Desktop/pyssp.desktop
```

Adjust `/home/ubuntu` for a different account. `QT_QPA_PLATFORM=xcb` uses the
desktop's XWayland support. The ALSA setting points to Debian's configuration;
the initial smoke run had logged a lookup for the nonexistent
`/usr/local/share/alsa/alsa.conf`.

Open **pySSP** from the desktop or application menu. From a terminal within the
desktop session, run `~/.local/bin/pyssp`.

To start it from SSH in the existing desktop session, the installation used a
transient user service:

```sh
systemd-run --user --unit=pyssp \
    -p StandardOutput=append:/home/ubuntu/pyssp.log \
    -p StandardError=append:/home/ubuntu/pyssp.log \
    /home/ubuntu/.local/bin/pyssp --debug
systemctl --user status pyssp --no-pager
tail -50 ~/pyssp.log
```

The user service manager already had `DISPLAY=:0`, `WAYLAND_DISPLAY=wayland-0`,
and `XDG_RUNTIME_DIR=/run/user/1000`. Check those values on another machine; this
command does not create a desktop session. If the transient unit already exists,
use `systemctl --user restart pyssp`. Use `systemctl --user stop pyssp` to stop it.
This is not a boot-time or login autostart installation.

## Verification performed

The following focused tests passed on the Pi (9 tests):

```sh
cd ~/pySSP
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q \
    tests/test_main_window_fullscreen.py \
    tests/test_main_window_import_compat.py \
    tests/test_dsp_pedalboard.py \
    tests/test_dsp_output_headroom.py \
    tests/test_audio_runtime.py
```

Additional runtime checks on the Pi:

- Imported the real application entry point after installing the `aifc` backport.
- Enumerated audio devices with `sounddevice.query_devices()`; ALSA exposed the
  Pi's `bcm2835 Headphones` and default output.
- Created the real Pedalboard processing chain with EQ and reverb enabled,
  processed a stereo buffer, and checked its shape and finite values.
- Opened an output stream and played a silent buffer successfully. This verifies
  stream operation, not audible sound quality or performance under load.
- Opened the full `MainWindow` on display `:0`, clicked the fullscreen button,
  captured the window, returned to windowed mode, and captured it again.
- Launched `main.py` through the desktop launcher, confirmed the user service
  remained active, and inspected a screenshot of the running desktop.

On Windows, the fullscreen, import-compatibility, and menu-role tests also passed
(9 tests). The fullscreen tests cover normal and maximized restoration, button
state synchronization, and the lock guard. The full test suite was not run as
part of this installation.

The fullscreen button is beside Lock at the top right on Linux and Windows.
Click it again to restore the previous window state. It is disabled while locked.
On macOS the two buttons are placed in the status bar; that platform was not
tested in this session.

## Installed files and limitations

| Path | Purpose |
| --- | --- |
| `~/pySSP` | Source snapshot including fullscreen changes |
| `~/pyssp-venv` | Python runtime and added dependencies |
| `~/.local/bin/pyssp` | Launcher |
| `~/.local/share/applications/pyssp.desktop` | Application-menu entry |
| `~/Desktop/pyssp.desktop` | Desktop shortcut |
| `~/.config/pySSP/settings.ini` | Application settings |
| `~/pyssp.log` | Output from the transient user service |
| `~/pySSP/INSTALLATION-PI.txt` | Installation provenance and compatibility notes |
| `~/pySSP/installed-packages.txt` | Venv-local dependency versions |

The smoke check created initial settings and disabled startup tips before the
final launch. A fresh installation may instead present language selection and
the Getting Started window.

The installed app supports the tested desktop, fullscreen, and audio/DSP paths.
Vocal separation through Spleeter is unavailable until its optional backend is
installed. MIDI hardware, NDI/video, external plugins, sustained playback, and
performance under production workloads were not validated in this session.
