#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PIPENV_IGNORE_VIRTUALENVS=1
export PIPENV_VENV_IN_PROJECT=1
cd "${ROOT_DIR}"

run_pipenv() {
  if command -v pipenv >/dev/null 2>&1; then
    pipenv "$@"
  else
    python3 -m pipenv "$@"
  fi
}

if ! command -v pipenv >/dev/null 2>&1 && ! python3 -m pipenv --version >/dev/null 2>&1; then
  echo "[INFO] pipenv not found. Installing with python3..."
  python3 -m pip install --user pipenv
fi

echo "[INFO] Ensuring pipenv uses Python 3.12..."
if ! run_pipenv --python 3.12; then
  echo "[ERROR] Could not create/select a Python 3.12 pipenv."
  exit 1
fi

PY_OK="$(run_pipenv run python -c 'import sys; print("ok" if sys.version_info[:2] == (3, 12) else "bad")')"
if [[ "${PY_OK}" != "ok" ]]; then
  echo "[WARN] Existing pipenv is not using Python 3.12. Recreating environment..."
  run_pipenv --rm || true
  if ! run_pipenv --python 3.12; then
    echo "[ERROR] Failed to recreate pipenv with Python 3.12."
    exit 1
  fi
fi

echo "[INFO] Installing dependencies from Pipfile.lock/Pipfile..."
if ! run_pipenv install --dev; then
  echo "[WARN] Locked dependency install failed. Retrying without lock..."
  if ! run_pipenv install --dev --skip-lock; then
    echo "[ERROR] pipenv install failed."
    exit 1
  fi
fi

echo "[INFO] Cleaning previous PyInstaller output..."
rm -rf build
find dist -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
mkdir -p dist

ICON_ARG=()
if [[ -f "pyssp/assets/app_icon.png" ]] && command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
  TMP_ICONSET="$(mktemp -d)/pyssp.iconset"
  mkdir -p "${TMP_ICONSET}"

  sips -z 16 16 pyssp/assets/app_icon.png --out "${TMP_ICONSET}/icon_16x16.png" >/dev/null
  sips -z 32 32 pyssp/assets/app_icon.png --out "${TMP_ICONSET}/icon_16x16@2x.png" >/dev/null
  sips -z 32 32 pyssp/assets/app_icon.png --out "${TMP_ICONSET}/icon_32x32.png" >/dev/null
  sips -z 64 64 pyssp/assets/app_icon.png --out "${TMP_ICONSET}/icon_32x32@2x.png" >/dev/null
  sips -z 128 128 pyssp/assets/app_icon.png --out "${TMP_ICONSET}/icon_128x128.png" >/dev/null
  sips -z 256 256 pyssp/assets/app_icon.png --out "${TMP_ICONSET}/icon_128x128@2x.png" >/dev/null
  sips -z 256 256 pyssp/assets/app_icon.png --out "${TMP_ICONSET}/icon_256x256.png" >/dev/null
  sips -z 512 512 pyssp/assets/app_icon.png --out "${TMP_ICONSET}/icon_256x256@2x.png" >/dev/null
  sips -z 512 512 pyssp/assets/app_icon.png --out "${TMP_ICONSET}/icon_512x512.png" >/dev/null
  cp pyssp/assets/app_icon.png "${TMP_ICONSET}/icon_512x512@2x.png"

  ICON_PATH="${ROOT_DIR}/build/app_icon.icns"
  mkdir -p "${ROOT_DIR}/build"
  iconutil -c icns "${TMP_ICONSET}" -o "${ICON_PATH}"
  ICON_ARG=(--icon "${ICON_PATH}")
fi

echo "[INFO] Building app (no terminal) with PyInstaller..."
if ! run_pipenv run pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name pySSP \
  "${ICON_ARG[@]}" \
  --add-data "pyssp/assets:pyssp/assets" \
  main.py; then
  echo "[ERROR] PyInstaller GUI build failed."
  exit 1
fi

APP_BIN="${ROOT_DIR}/dist/pySSP.app/Contents/MacOS/pySSP"
if [[ -x "${APP_BIN}" ]]; then
  if [[ -d "${ROOT_DIR}/dist/pySSP" ]]; then
    echo "[INFO] Removing redundant onedir output (dist/pySSP)..."
    rm -rf "${ROOT_DIR}/dist/pySSP"
  fi

  create_wrapper_app() {
    local app_name="$1"
    local run_arg="$2"
    local bundle_id="$3"
    local launch_mode="${4:-direct}"
    local wrapper_app="${ROOT_DIR}/dist/${app_name}.app"
    local wrapper_exec="${wrapper_app}/Contents/MacOS/${app_name}"
    local wrapper_icon="${wrapper_app}/Contents/Resources/app_icon.icns"
    local main_icon="${ROOT_DIR}/dist/pySSP.app/Contents/Resources/app_icon.icns"

    mkdir -p "${wrapper_app}/Contents/MacOS" "${wrapper_app}/Contents/Resources"

    cat > "${wrapper_app}/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDisplayName</key>
  <string>${app_name}</string>
  <key>CFBundleExecutable</key>
  <string>${app_name}</string>
  <key>CFBundleIdentifier</key>
  <string>${bundle_id}</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>${app_name}</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
</dict>
</plist>
EOF

    cat > "${wrapper_exec}" <<EOF
#!/usr/bin/env bash
set -euo pipefail

DIST_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")/../../.." && pwd)"
MAIN_APP="\${DIST_DIR}/pySSP.app"
MAIN_BIN="\${MAIN_APP}/Contents/MacOS/pySSP"

if [[ ! -x "\${MAIN_BIN}" ]]; then
  MSG="Required app is missing: \${MAIN_APP}"
  echo "[ERROR] \${MSG}" >&2
  if command -v osascript >/dev/null 2>&1; then
    osascript - "\${MSG}" <<'APPLESCRIPT'
on run argv
  display alert "pySSP launcher error" message (item 1 of argv) as critical
end run
APPLESCRIPT
  fi
  exit 1
fi

if [[ "${launch_mode}" == "terminal" ]]; then
  CMD="\"\${MAIN_BIN}\" ${run_arg}"
  if command -v osascript >/dev/null 2>&1; then
    osascript - "\${CMD}" <<'APPLESCRIPT'
on run argv
  set cmd to item 1 of argv
  tell application "Terminal"
    activate
    do script cmd
  end tell
end run
APPLESCRIPT
    exit 0
  fi
fi

exec "\${MAIN_BIN}" ${run_arg}
EOF

    chmod +x "${wrapper_exec}"
    if [[ -f "${main_icon}" ]]; then
      cp "${main_icon}" "${wrapper_icon}"
      /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string app_icon.icns" "${wrapper_app}/Contents/Info.plist" >/dev/null 2>&1 || true
    fi
  }

  echo "[INFO] Adding cleanstart launcher app..."
  create_wrapper_app "pySSP_cleanstart" "--cleanstart" "com.pyssp.cleanstart" "direct"

  echo "[INFO] Adding debug launcher app..."
  create_wrapper_app "pySSP_debug" "-debug" "com.pyssp.debug" "terminal"
fi

echo
echo "[SUCCESS] Build complete:"
echo "  ${ROOT_DIR}/dist/pySSP.app"
if [[ -d "${ROOT_DIR}/dist/pySSP_cleanstart.app" ]]; then
  echo "  ${ROOT_DIR}/dist/pySSP_cleanstart.app"
fi
if [[ -d "${ROOT_DIR}/dist/pySSP_debug.app" ]]; then
  echo "  ${ROOT_DIR}/dist/pySSP_debug.app"
fi
