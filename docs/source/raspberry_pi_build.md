# Build the Raspberry Pi Debian installer in WSL

The Linux build has two entry points, run in order:

1. `bash spleeter-cli/build_pyinstaller_linux.sh`: freeze the standalone Spleeter
   CLI, including its TensorFlow runtime and offline 2stems model.
2. `bash build_pyinstaller_linux.sh`: freeze pySSP, include the CLI, and build an
   `arm64` Debian installer under `dist/linux-arm64/`.

To prioritize the main app or save space, skip step 1 and explicitly build without
Spleeter: `PYSSP_BUNDLE_SPLEETER=0 bash build_pyinstaller_linux.sh`.
The default remains a combined package and requires a completed CLI build.
An app-only package cannot generate vocal-removed tracks. `BUILD-INFO.txt` records
whether Spleeter was included.

The October 9 deployment prioritizes the **app-only package**. The separate
Spleeter build recipe is provided for follow-up work; its frozen model inference
has not yet passed validation. Do not treat CLI `--help` success as a working
separation test.

Do the build on the development machine, not the Pi's small SD card. The build
environment below uses an ARM64 Debian 12 userspace under QEMU in Ubuntu WSL2.
The resulting binaries target ARM64 Linux and can run on the tested Debian 13 Pi.
An ordinary x86-64 WSL build would produce the wrong binaries: PyInstaller
[does not cross-build between these architectures](https://github.com/pyinstaller/pyinstaller/issues/7142).

The scripts also support native Debian ARM64. On an x86-64 Debian environment they
produce `amd64` artifacts, which must not be installed on a Pi. The architecture
of the build userspace, not a filename or command-line label, determines the output.

## Prepare WSL from scratch

These are build-machine operations. The tested WSL distribution is **Ubuntu
24.04**, named `Ubuntu`, with substantial free disk space. Allow at least 15 GB
for the ARM root filesystem, two venvs, PyInstaller intermediates, and package
staging. QEMU builds are slower than native ARM builds.

From Windows PowerShell, open a root shell in that distribution:

```powershell
wsl --list --verbose
wsl -d Ubuntu -u root
```

Run the following commands **inside that WSL root shell**. Root is needed for the
chroot, apt, and mount operations; it is not a request to change the Windows account.

```sh
apt-get update
apt-get install -y qemu-user-static binfmt-support debootstrap rsync

# WSL may have a read-only overlay on binfmt_misc/status. Register only ARM64
# directly rather than relying on update-binfmts/systemd-binfmt to enable it.
if [ ! -e /proc/sys/fs/binfmt_misc/qemu-aarch64 ]; then
    cat /usr/lib/binfmt.d/qemu-aarch64.conf > /proc/sys/fs/binfmt_misc/register
fi
cat /proc/sys/fs/binfmt_misc/qemu-aarch64
```

The registration should say `enabled` and include the `F` flag, which keeps the
emulator accessible after entering a chroot. If the `binfmt_misc` filesystem is
not mounted, mount it first with
`mount -t binfmt_misc binfmt_misc /proc/sys/fs/binfmt_misc`. Do not delete WSL's
existing `WSLInterop` registration.

Create the dedicated ARM build root. The following bootstrap commands are for a
**new** `/opt/pyssp-arm64` directory; do not re-bootstrap over an existing build:

```sh
debootstrap --arch=arm64 --foreign --variant=minbase \
    bookworm /opt/pyssp-arm64 http://deb.debian.org/debian
chroot /opt/pyssp-arm64 /debootstrap/debootstrap --second-stage
```

Prepare mounts and DNS (repeat after restarting WSL):

```sh
mountpoint -q /opt/pyssp-arm64/proc || mount -t proc proc /opt/pyssp-arm64/proc
if ! mountpoint -q /opt/pyssp-arm64/dev; then
    mount --rbind /dev /opt/pyssp-arm64/dev
    mount --make-rslave /opt/pyssp-arm64/dev
fi
cp /etc/resolv.conf /opt/pyssp-arm64/etc/resolv.conf
chroot /opt/pyssp-arm64 uname -m
```

The last command must print `aarch64`. Install dependencies **inside the chroot**:

```sh
chroot /opt/pyssp-arm64 /bin/bash
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 python3-venv python3-dev python3-pyqt5 python3-pyqt5.qtmultimedia \
    libportaudio2 libsndfile1 ffmpeg binutils ca-certificates build-essential \
    git file xz-utils libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0
python3 --version
dpkg --print-architecture
exit
```

Debian 12 supplies Python 3.11. The CLI needs a separate environment because
Spleeter 2.4.2/TensorFlow 2.12.1 use NumPy 1.24, while this pySSP build uses NumPy
2.2.6. Spleeter's published Python requirement excludes Python 3.12 and newer.
The main app is frozen with Python 3.11 here, so it does not need the Python 3.13
`aifc` compatibility workaround from the original source installation.

## Put the latest source in the build root

Keep source and build intermediates on WSL's Linux filesystem for better
performance. Do not build directly in the Windows checkout or reuse its Windows
venvs. To build committed `main`, from the WSL root shell:

```sh
git clone --branch main https://github.com/sikaxn/pySSP.git /opt/pyssp-arm64/src
git -C /opt/pyssp-arm64/src rev-parse HEAD
```

If the destination already exists, inspect its changes before updating it; do not
overwrite local work. Cloning GitHub excludes uncommitted Windows edits, including
new build scripts until they have been committed.

For development, the alternative is a working-tree snapshot. From PowerShell in
the Windows repository, create a TAR with tracked files and non-ignored new files:

```powershell
@'
import pathlib, subprocess, tarfile, tempfile
paths = subprocess.check_output([
    "git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"
]).decode().split("\0")
destination = pathlib.Path(tempfile.gettempdir()) / "pyssp-linux-source.tar"
with tarfile.open(destination, "w") as archive:
    for path in sorted(set(paths)):
        if path and pathlib.Path(path).is_file():
            archive.add(path, arcname=path, recursive=False)
print(destination)
'@ | python -
git rev-parse HEAD
git status --short
```

Review `git status` first: non-ignored new files are included. Extract into a new
or deliberately refreshed source directory from the WSL root shell, substituting
your Windows username/path:

```sh
mkdir -p /opt/pyssp-arm64/src
tar -xf /mnt/c/Users/Nathan/AppData/Local/Temp/pyssp-linux-source.tar \
    -C /opt/pyssp-arm64/src
# Normalize shell files from older Windows working-tree snapshots.
sed -i 's/\r$//' /opt/pyssp-arm64/src/build_pyinstaller_linux.sh \
    /opt/pyssp-arm64/src/spleeter-cli/build_pyinstaller_linux.sh \
    /opt/pyssp-arm64/src/packaging/linux/pyssp-launcher
```

This snapshot has no `.git`; pass its recorded commit and `+working-tree` via
`PYSSP_SOURCE_REVISION` during step 2. The initial build used current main at
`5f6522b` plus the local audio-buffer fix and packaging changes.

## Run the two builds

Enter the ARM environment from the WSL root shell:

```sh
chroot /opt/pyssp-arm64 /bin/bash
cd /src
bash spleeter-cli/build_pyinstaller_linux.sh
PYSSP_SOURCE_REVISION=5f6522b+working-tree bash build_pyinstaller_linux.sh
```

Replace that revision with the source actually being built. For a Git checkout,
omit the override to let the script read `HEAD`. Run `git status --short` and
include a working-tree qualifier yourself if it contains edits.

Step 1 checks the model's checkpoint/index/meta/data files, installs its pinned
direct dependencies, runs the standalone unit tests, and checks the frozen CLI's
`--help`. Step 2 requires step 1's architecture marker, builds the HTML docs,
generates version/build metadata, freezes pySSP, and stages a Debian package.
It first runs the frozen application's `--system-info-probe` to catch import or
shared-library failures. Wheel binaries are not stripped: stripping the ARM64
NumPy OpenBLAS library with Debian 12 binutils produced misaligned ELF load
segments and failed on the Pi with `ELF load command address/offset not page-aligned`.
An actual model inference and an on-device application check are still needed;
`--help` alone does not import TensorFlow or exercise the model.

Build products are separated by architecture:

| Path under `/src` | Purpose |
| --- | --- |
| `.build-linux/arm64/spleeter-venv` | CLI build dependencies |
| `.build-linux/arm64/spleeter-dist/spleeter-cli` | Frozen CLI and model |
| `.build-linux/arm64/app-venv` | pySSP build dependencies, using system Qt |
| `.build-linux/arm64/app-dist/pySSP` | Application; `tools/spleeter-cli` only when enabled |
| `dist/linux-arm64/*.deb` | Installable package |
| `dist/linux-arm64/*.deb.sha256` | Package checksum |

The venvs and work directories can be reused for subsequent builds. Each package
uses a fresh staging directory. The top-level version remains the version from
`version.json`; its Debian version gets a timestamp, and `b1` becomes `~b1` so
Debian sorts the prerelease before the final version. `BUILD-INFO.txt` records
the supplied source revision and generated build ID. Direct dependency pins are
in the two Linux requirements files; the bundles also record resolved packages.

## Inspect and copy the installer

Inside the ARM build root:

```sh
dpkg-deb -f dist/linux-arm64/*.deb Architecture Version Installed-Size
file .build-linux/arm64/app-dist/pySSP/pySSP
file .build-linux/arm64/spleeter-dist/spleeter-cli/spleeter-cli
ls -lh dist/linux-arm64/*.deb
```

If multiple builds exist, select the intended `.deb` explicitly instead of using
the wildcard. The architecture must be `arm64`, and both executables must be
AArch64 ELF files. Exit the chroot before copying over SSH.

Check free space on the Pi. Budget for **both** the compressed `.deb` and its
`Installed-Size` (KiB), plus runtime working space. Do not copy the build venvs,
intermediate files, or WSL root filesystem to the SD card.

```sh
ssh ubuntu@10.0.0.166 'df -h /'
scp /opt/pyssp-arm64/src/dist/linux-arm64/SELECTED_PACKAGE.deb \
    ubuntu@10.0.0.166:/home/ubuntu/
ssh ubuntu@10.0.0.166
sudo apt-get install ./SELECTED_PACKAGE.deb
```

Credentials should be entered interactively, not stored in scripts or docs.
Installation adds `/opt/pyssp`, `/usr/bin/pyssp`, an application-menu entry, and an
icon. It preserves `~/.config/pySSP/settings.ini` and existing sound libraries.
The package does not enable autostart or delete the old source installation.

Close the old application before starting `/usr/bin/pyssp`. The old
`~/.local/bin/pyssp` and user-local desktop entry can take precedence over the
package's launcher. Back them up, then point them to `/usr/bin/pyssp` or remove
only those obsolete launcher files once the packaged installation is verified.
Keep the original source/venv until the new build has been tested.

The packaged launcher automatically applies the tested audio-buffer settings on
Raspberry Pi hardware (2,048 frames, requested 150 ms; about 186 ms measured on
the tested headphone driver). Environment overrides are preserved. It also limits
TensorFlow to two compute threads and one inter-op thread by default.

## Verify on the Pi

```sh
/usr/bin/pyssp --system-info-probe
/usr/bin/pyssp
```

Verify the title shows the intended version/build, play sound buttons through the
actual output device, and test fullscreen. The following Spleeter checks apply
only to a combined package; skip them for an app-only installation.
To exercise the offline model, use a
short stereo WAV first:

```sh
TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=1 \
    /opt/pyssp/tools/spleeter-cli/spleeter-cli \
    --input /path/to/short.wav --output /tmp/short-no-vocals.wav
```

Then test **Generate vocal removed track** in pySSP to cover FFmpeg conversion,
the subprocess handoff, and output encoding. Spleeter runs locally on the CPU;
bundling it does not make separation a real-time process or remove its memory
requirements. Keep an eye on RAM and disk space when processing long files.

For a repeatable test without supplying an audio file, the source repository also
provides a standard-library-only smoke runner. It generates a two-second stereo
WAV, executes the frozen CLI, and verifies the output rate, frame count, and that
the model changed the samples:

```sh
python3 scripts/smoke_spleeter_bundle.py /opt/pyssp/tools/spleeter-cli/spleeter-cli
```

After validation, the copied installer can be removed from the Pi while retaining
the original `.deb` in WSL. Uninstall with `sudo apt-get remove pyssp`; user settings
and sound libraries are not package-owned and are retained.

## Resume or stop the build environment

After a WSL restart, check ARM binfmt registration again and restore the mounts
and DNS before entering the chroot. Do not run two builds in the same source tree
at once. If a build fails, fix the reported dependency/runtime issue and rerun the
same step; step 2 does not silently omit Spleeter when step 1 is missing.

When no build processes or shells remain inside the chroot, unmount only its
dedicated mounts from the WSL root shell:

```sh
umount -R /opt/pyssp-arm64/dev
umount /opt/pyssp-arm64/proc
```

Never recursively delete a chroot while its `/dev` or `/proc` mounts are attached.

## October 9, 2026 deployment results

The app-only package was built in WSL and installed on `ubuntu@10.0.0.166`:

| Item | Result |
| --- | --- |
| Source | `5f6522b+working-tree`, including the audio-buffer and packaging changes |
| Debian version | `1.1.4~b1+20261009.200232` |
| Application build | `20261009-200232-DBAC70` |
| Architecture | ARM64, verified AArch64 ELF |
| Installer | `pyssp_1.1.4~b1+20261009.200232_arm64.deb` |
| Compressed size | 96,342,876 bytes, approximately 92 MiB |
| Installed application | 289,416 KiB, approximately 283 MiB |
| Remaining Pi root filesystem space | 2.3 GiB reported by `df -h /` after cleanup |
| Spleeter | Not included; model validation deferred |

SHA-256:

```text
93b5a788e07092fb77a22bb480809fbaf764ceef788b94290973ff284e34d833
```

The installer and checksum are retained in the Windows checkout's
`dist/linux-arm64/` and the WSL source tree. Temporary installers were removed
from the Pi. The rejected build ending in `195604` was removed after replacement.

The frozen decoder probe passed in the ARM build environment and on the Pi:
WAV, AIFF, MP3, OGG, and FLAC samples loaded, with bundled FFmpeg 7.0.2 detected.
The GUI loaded the existing library, started and stopped a library track, and
successfully entered and left fullscreen using the button beside Lock.
The running process had `PYSSP_AUDIO_BLOCKSIZE=2048` and
`PYSSP_AUDIO_LATENCY=0.15`. This package smoke test did not record headphone
output or count underruns; the earlier instrumented audio results are documented
in [Raspberry Pi installation](raspberry_pi.md).

The old source app was terminated at the user's request. `~/.local/bin/pyssp`
now links to `/usr/bin/pyssp`, and both user-local desktop entries use the package
launcher. Old source and venv directories remain available for rollback. Settings
and the old launcher were backed up under
`~/pyssp-diagnostics/before-deb-install/`. The running application was started
with a transient user service named `pyssp-packaged`; it does not enable autostart.
Its log is `~/pyssp-packaged.log`, and decoder results are in
`~/pyssp-package-probe.log`.

The desktop displayed a low-voltage warning during verification.
`vcgencmd get_throttled` returned `0x50000`: undervoltage and throttling had
occurred earlier in the current boot, with neither active at the sampled moment.
These bits are defined in the [Raspberry Pi documentation](https://www.raspberrypi.com/documentation/usage/raspberry-pi.html#get_throttled).
This is a new observation relative to the earlier audio investigation. Check the
Pi's power supply and cable if crackling persists; this deployment did not
establish whether those power events coincided with audible glitches.
