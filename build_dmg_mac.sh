#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
BUILD_DIR="${ROOT_DIR}/build/dmg"
STAGE_DIR="${BUILD_DIR}/staging"
TMP_DMG="${BUILD_DIR}/pySSP-temp.dmg"
OUT_DMG="${DIST_DIR}/pySSP-macOS.dmg"
VOL_NAME="pySSP Installer"
BG_MAX_PX="${DMG_BG_MAX_PX:-900}"

required_apps=(
  "pySSP.app"
  "pySSP_cleanstart.app"
  "pySSP_debug.app"
)

echo "[INFO] Validating required files..."
for app in "${required_apps[@]}"; do
  if [[ ! -d "${DIST_DIR}/${app}" ]]; then
    echo "[ERROR] Missing app bundle: ${DIST_DIR}/${app}"
    echo "[INFO] Build apps first with: ./build_pyinstaller_mac.sh"
    exit 1
  fi
done

if [[ ! -f "${ROOT_DIR}/logo.png" ]]; then
  echo "[ERROR] Missing background image: ${ROOT_DIR}/logo.png"
  exit 1
fi

echo "[INFO] Preparing DMG staging directory..."
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}/pyssp" "${STAGE_DIR}/.background"

cp -R "${DIST_DIR}/pySSP.app" "${STAGE_DIR}/pyssp/"
cp -R "${DIST_DIR}/pySSP_cleanstart.app" "${STAGE_DIR}/pyssp/"
cp -R "${DIST_DIR}/pySSP_debug.app" "${STAGE_DIR}/pyssp/"

if command -v sips >/dev/null 2>&1; then
  echo "[INFO] Resizing DMG background to max ${BG_MAX_PX}px..."
  sips -Z "${BG_MAX_PX}" "${ROOT_DIR}/logo.png" --out "${STAGE_DIR}/.background/logo.png" >/dev/null
else
  cp "${ROOT_DIR}/logo.png" "${STAGE_DIR}/.background/logo.png"
fi

ln -s /Applications "${STAGE_DIR}/Applications"

cat > "${STAGE_DIR}/INSTALL.txt" <<'EOF'
pySSP macOS install
===================

1. Open the "pyssp" folder.
2. Drag the app(s) you want into Applications.

Included apps:
- pySSP.app
- pySSP_cleanstart.app
- pySSP_debug.app
EOF

if [[ -f "${OUT_DMG}" ]]; then
  rm -f "${OUT_DMG}"
fi
rm -f "${TMP_DMG}"

size_kb="$(du -sk "${STAGE_DIR}" | awk '{print $1}')"
dmg_size_kb="$((size_kb + 200000))"

echo "[INFO] Creating writable DMG..."
hdiutil create \
  -size "${dmg_size_kb}k" \
  -fs HFS+ \
  -volname "${VOL_NAME}" \
  -srcfolder "${STAGE_DIR}" \
  -format UDRW \
  "${TMP_DMG}" >/dev/null

echo "[INFO] Mounting DMG for Finder layout..."
attach_out="$(hdiutil attach -readwrite -noverify -noautoopen "${TMP_DMG}")"
device="$(echo "${attach_out}" | awk '/^\/dev\// {print $1; exit}')"
mount_point="/Volumes/${VOL_NAME}"

if [[ -z "${device}" || ! -d "${mount_point}" ]]; then
  echo "[ERROR] Failed to mount DMG."
  exit 1
fi

osascript >/dev/null 2>&1 <<EOF || true
tell application "Finder"
  tell disk "${VOL_NAME}"
    open
    set current view of container window to icon view
    set toolbar visible of container window to false
    set statusbar visible of container window to false
    set bounds of container window to {100, 100, 980, 650}
    set opts to the icon view options of container window
    set arrangement of opts to not arranged
    set icon size of opts to 96
    set text size of opts to 14
    set background picture of opts to file ".background:logo.png"
    set position of item "pyssp" to {180, 300}
    set position of item "Applications" to {740, 300}
    set position of item "INSTALL.txt" to {180, 120}
    close
    open
    update without registering applications
    delay 1
  end tell
end tell
EOF

echo "[INFO] Finalizing DMG..."
sync
hdiutil detach "${device}" >/dev/null
hdiutil convert "${TMP_DMG}" -format UDZO -imagekey zlib-level=9 -o "${OUT_DMG}" >/dev/null
rm -f "${TMP_DMG}"

echo
echo "[SUCCESS] DMG created:"
echo "  ${OUT_DMG}"
