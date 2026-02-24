#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
BUILD_DIR="${ROOT_DIR}/build/dmg"
STAGE_DIR="${BUILD_DIR}/staging"
TMP_DMG="${BUILD_DIR}/pySSP-temp.dmg"
APP_VERSION="0.0.0"
OUT_DMG=""
VOL_NAME="pySSP Installer"
BG_MAX_PX="${DMG_BG_MAX_PX:-900}"
ABOUT_SRC=""
ABOUT_RENDERED="${BUILD_DIR}/about.rendered.md"
LICENSE_SRC=""
SLA_XML="${BUILD_DIR}/sla.xml"

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

if [[ -f "${ROOT_DIR}/version.json" ]]; then
  APP_VERSION="$(python3 -c 'import json; print(json.load(open("version.json","r",encoding="utf-8")).get("version","0.0.0"))')"
fi
APP_VERSION_SAFE="$(printf '%s' "${APP_VERSION}" | tr -cs '[:alnum:]._-+' '_')"
OUT_DMG="${DIST_DIR}/pySSP-macOS-${APP_VERSION_SAFE}.dmg"

if [[ -f "${ROOT_DIR}/pyssp/assets/about/about.md" ]]; then
  ABOUT_SRC="${ROOT_DIR}/pyssp/assets/about/about.md"
else
  echo "[ERROR] Missing about source file: ${ROOT_DIR}/pyssp/assets/about/about.md"
  exit 1
fi

if [[ -f "${ROOT_DIR}/pyssp/assets/about/license.md" ]]; then
  LICENSE_SRC="${ROOT_DIR}/pyssp/assets/about/license.md"
elif [[ -f "${ROOT_DIR}/LICENSE" ]]; then
  LICENSE_SRC="${ROOT_DIR}/LICENSE"
else
  echo "[ERROR] Missing license source file (expected pyssp/assets/about/license.md or LICENSE)."
  exit 1
fi

mkdir -p "${BUILD_DIR}"
python3 - "${ABOUT_SRC}" "${ABOUT_RENDERED}" "${APP_VERSION}" <<'PY'
import pathlib
import sys

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
version = sys.argv[3]
text = src.read_text(encoding="utf-8", errors="replace")
dst.write_text(text.replace("{{VERSION}}", version), encoding="utf-8")
PY

echo "[INFO] Preparing DMG staging directory..."
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}/pyssp" "${STAGE_DIR}/.background"

cp -R "${DIST_DIR}/pySSP.app" "${STAGE_DIR}/pyssp/"
cp -R "${DIST_DIR}/pySSP_cleanstart.app" "${STAGE_DIR}/pyssp/"
cp -R "${DIST_DIR}/pySSP_debug.app" "${STAGE_DIR}/pyssp/"
cp "${ABOUT_RENDERED}" "${STAGE_DIR}/about.md"
cp "${LICENSE_SRC}" "${STAGE_DIR}/license.md"

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

Also included:
- about.md
- license.md
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
    set position of item "about.md" to {360, 120}
    set position of item "license.md" to {740, 120}
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

echo "[INFO] Embedding DMG license agreement resources..."
python3 - "${ABOUT_RENDERED}" "${SLA_XML}" <<'PY'
import base64
import pathlib
import sys

license_path = pathlib.Path(sys.argv[1])
out_xml = pathlib.Path(sys.argv[2])

default_lpic = [
    0x0002, 0x0011, 0x0003, 0x0001, 0x0000, 0x0000, 0x0002, 0x0000,
    0x0008, 0x0003, 0x0000, 0x0001, 0x0004, 0x0000, 0x0004, 0x0005,
    0x0000, 0x000E, 0x0006, 0x0001, 0x0005, 0x0007, 0x0000, 0x0007,
    0x0008, 0x0000, 0x0047, 0x0009, 0x0000, 0x0034, 0x000A, 0x0001,
    0x0035, 0x000B, 0x0001, 0x0020, 0x000C, 0x0000, 0x0011, 0x000D,
    0x0000, 0x005B, 0x0004, 0x0000, 0x0033, 0x000F, 0x0001, 0x000C,
    0x0010, 0x0000, 0x000B, 0x000E, 0x0000,
]
default_menu = [
    "English",
    "Agree",
    "Disagree",
    "Print",
    "Save...",
    'You agree to the License Agreement terms when you click the "Agree" button.',
    "Software License Agreement",
    "This text cannot be saved.  This disk may be full or locked, or the file may be locked.",
    "Unable to print.  Make sure you have selected a printer.",
]

def break_long_line(line: str) -> list[str]:
    max_len = 255
    out = []
    i = 0
    while i < len(line):
        n = min(max_len, len(line) - i)
        if i + n < len(line):
            while n > 0 and line[i + n - 1] != " ":
                n -= 1
        if n == 0:
            raise SystemExit("license contains a token longer than 255 characters")
        out.append(line[i:i+n])
        i += n
    if not line:
        out.append("")
    return out

raw = license_path.read_text(encoding="utf-8", errors="replace")
lines: list[str] = []
for src_line in raw.splitlines():
    lines.extend(break_long_line(src_line))

license_data = bytearray()
for l in lines:
    license_data.extend(l.encode("utf-8"))
    license_data.append(0x0D)
license_data.append(0x0D)

lpic_data = bytearray()
for n in default_lpic:
    lpic_data.extend(n.to_bytes(2, "big"))

menu_data = bytearray()
menu_data.extend(len(default_menu).to_bytes(2, "big"))
for l in default_menu:
    b = l.encode("utf-8")
    if len(b) > 255:
        raise SystemExit("menu line too long for STR# resource")
    menu_data.append(len(b))
    menu_data.extend(b)

def entry(data: bytes, rid: int, name: str) -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return (
        "<dict>"
        "<key>Attributes</key><string>0x0000</string>"
        "<key>Data</key><data>" + b64 + "</data>"
        "<key>ID</key><string>" + str(rid) + "</string>"
        "<key>Name</key><string>" + name + "</string>"
        "</dict>"
    )

license_key = "RTF " if license_path.suffix.lower() == ".rtf" else "TEXT"
xml = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
    '<plist version="1.0"><dict>'
    '<key>LPic</key><array>' + entry(bytes(lpic_data), 5000, "") + "</array>"
    '<key>STR#</key><array>' + entry(bytes(menu_data), 5002, "English") + "</array>"
    f"<key>{license_key}</key><array>" + entry(bytes(license_data), 5002, "English") + "</array>"
    "</dict></plist>"
)
out_xml.parent.mkdir(parents=True, exist_ok=True)
out_xml.write_text(xml, encoding="utf-8")
PY

hdiutil udifrez -xml "${SLA_XML}" "FIXME_WHY_IS_THIS_ARGUMENT_NEEDED" "${OUT_DMG}" >/dev/null
rm -f "${SLA_XML}"

echo
echo "[SUCCESS] DMG created:"
echo "  ${OUT_DMG}"
