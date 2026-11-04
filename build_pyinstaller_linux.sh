#!/usr/bin/env bash
# Step 2: freeze pySSP, bundle step 1, and create a Debian installer.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ "$(uname -s)" == Linux ]] || { echo 'Linux is required.' >&2; exit 1; }
ARCH="$(dpkg --print-architecture)"
[[ "$ARCH" == arm64 || "$ARCH" == amd64 ]] || { echo "Unsupported architecture: $ARCH" >&2; exit 1; }
BUILD="$ROOT/.build-linux/$ARCH"
CLI="$BUILD/spleeter-dist/spleeter-cli"
BUNDLE_SPLEETER="${PYSSP_BUNDLE_SPLEETER:-1}"
[[ "$BUNDLE_SPLEETER" == 0 || "$BUNDLE_SPLEETER" == 1 ]] || { echo 'PYSSP_BUNDLE_SPLEETER must be 0 or 1.' >&2; exit 1; }
if [[ "$BUNDLE_SPLEETER" == 1 ]]; then
[[ -x "$CLI/spleeter-cli" && -f "$CLI/build-architecture.txt" ]] || {
    echo 'Run bash spleeter-cli/build_pyinstaller_linux.sh first.' >&2; exit 1;
}
[[ "$(cat "$CLI/build-architecture.txt")" == "$ARCH" ]] || { echo 'CLI architecture mismatch.' >&2; exit 1; }
fi
PY="$BUILD/app-venv/bin/python"
if [[ ! -x "$PY" ]]; then
    "${PYSSP_PYTHON:-python3.11}" -m venv --system-site-packages "$BUILD/app-venv"
fi
"$PY" -c 'import sys; assert sys.version_info[:2] == (3, 11), "Python 3.11 required"; import PyQt5.QtWidgets'
"$PY" -m pip install --no-compile --disable-pip-version-check -r "$ROOT/packaging/linux/requirements.txt"
cd "$ROOT"
"$PY" scripts/generate_build_version.py --source version.json --output "$BUILD/version.json"
"$PY" -m sphinx -b html docs/source "$BUILD/docs"
# Keep wheel binaries intact: Debian 12 strip can invalidate ARM OpenBLAS LOAD alignment.
"$PY" -m PyInstaller --noconfirm --clean --name pySSP --noupx \
    --distpath "$BUILD/app-dist" --workpath "$BUILD/app-work" --specpath "$BUILD" \
    --collect-all pedalboard --collect-all pedalboard_native --collect-data imageio_ffmpeg \
    --add-data "$ROOT/pyssp/assets:pyssp/assets" --add-data "$BUILD/docs:docs/build/html" \
    --add-data "$BUILD/version.json:." --add-data "$ROOT/logo.png:." --add-data "$ROOT/logo2.png:." "$ROOT/main.py"
APP="$BUILD/app-dist/pySSP"
# Exercise frozen imports before producing an installer, even in a headless chroot.
QT_QPA_PLATFORM=offscreen "$APP/pySSP" --system-info-probe > "$BUILD/frozen-probe.log" 2>&1 || {
    cat "$BUILD/frozen-probe.log" >&2
    exit 1
}
mkdir -p "$APP/tools"
if [[ "$BUNDLE_SPLEETER" == 1 ]]; then
cp -a "$CLI" "$APP/tools/"
fi
"$PY" -m pip freeze --local > "$APP/requirements-build.txt"
REV="${PYSSP_SOURCE_REVISION:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}"
printf 'source=%s\narchitecture=%s\nspleeter=%s\n' "$REV" "$ARCH" "$BUNDLE_SPLEETER" > "$APP/BUILD-INFO.txt"
"$PY" - "$BUILD/version.json" "$APP/BUILD-INFO.txt" <<'PY'
import json, sys
from pathlib import Path
with Path(sys.argv[2]).open('a') as f:
    f.write(json.dumps(json.loads(Path(sys.argv[1]).read_text())) + '\n')
PY
VERSION="$("$PY" - "$BUILD/version.json" <<'PY'
import json, re, sys
p = json.load(open(sys.argv[1]))
version = re.sub(r'b(\d+)$', r'~b\1', p['version'])
assert re.fullmatch(r'[0-9][A-Za-z0-9.+~\-]*', version), version
print(version + '+' + p['build_number'].replace('-', '.'))
PY
)"
# A fresh staging directory prevents files from earlier versions leaking in.
STAGE="$(mktemp -d "$BUILD/deb-stage.XXXXXX")"
trap 'rm -rf -- "$STAGE"' EXIT
mkdir -p "$STAGE/opt/pyssp" "$STAGE/usr/bin" "$STAGE/usr/share/applications" \
    "$STAGE/usr/share/icons/hicolor/256x256/apps" "$STAGE/usr/share/doc/pyssp" "$STAGE/DEBIAN"
cp -a "$APP/." "$STAGE/opt/pyssp/"
install -m 755 packaging/linux/pyssp-launcher "$STAGE/usr/bin/pyssp"
install -m 644 packaging/linux/pyssp.desktop "$STAGE/usr/share/applications/pyssp.desktop"
install -m 644 logo.png "$STAGE/usr/share/icons/hicolor/256x256/apps/pyssp.png"
install -m 644 LICENSE "$STAGE/usr/share/doc/pyssp/copyright"
SIZE="$(du -sk "$STAGE/opt/pyssp" | cut -f1)"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: pyssp
Version: $VERSION
Architecture: $ARCH
Maintainer: pySSP contributors <noreply@users.noreply.github.com>
Section: sound
Priority: optional
Installed-Size: $SIZE
Depends: libc6 (>= 2.36), libstdc++6, libgcc-s1, libasound2, libportaudio2, libsndfile1, libgl1, libegl1, libxkbcommon-x11-0, libxcb-xinerama0, libxcb-cursor0, libdbus-1-3
Description: pySSP soundboard
 Frozen desktop soundboard. Spleeter bundle included: $BUNDLE_SPLEETER.
EOF
mkdir -p "$ROOT/dist/linux-$ARCH"
DEB="$ROOT/dist/linux-$ARCH/pyssp_${VERSION}_${ARCH}.deb"
dpkg-deb --root-owner-group --threads-max=2 -Zxz -z3 --build "$STAGE" "$DEB"
dpkg-deb --info "$DEB"
(cd "$(dirname "$DEB")" && sha256sum "$(basename "$DEB")" > "$(basename "$DEB").sha256")
echo "Built $DEB (installed application: $SIZE KiB)"
