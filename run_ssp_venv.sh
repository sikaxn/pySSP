#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="${ROOT_DIR}/.venv/bin/python"
SPLEETER_CLI_EXE="${ROOT_DIR}/dist/spleeter-cli/spleeter-cli"
SPLEETER_CLI_BUILD="${ROOT_DIR}/spleeter-cli/build_pyinstaller.bat"

if [[ ! -x "${VENV_PY}" ]]; then
  echo '[ERROR] Virtual environment not found at ".venv/bin/python"'
  echo
  echo "Create it with:"
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

if [[ ! -x "${SPLEETER_CLI_EXE}" ]]; then
  echo "[WARN] Prebuilt spleeter-cli not found:"
  echo "[WARN]   ${SPLEETER_CLI_EXE}"
  echo
  read -r -p "Build spleeter-cli now? [y/N]: " BUILD_SPLEETER
  if [[ "${BUILD_SPLEETER}" =~ ^[Yy]$ ]]; then
    if [[ ! -f "${SPLEETER_CLI_BUILD}" ]]; then
      echo "[ERROR] Missing build script:"
      echo "[ERROR]   ${SPLEETER_CLI_BUILD}"
      exit 1
    fi
    (
      cd "${ROOT_DIR}/spleeter-cli"
      cmd.exe /c build_pyinstaller.bat
    )
    if [[ ! -x "${SPLEETER_CLI_EXE}" ]]; then
      echo "[ERROR] spleeter-cli build completed but executable is still missing."
      echo "[ERROR]   ${SPLEETER_CLI_EXE}"
      exit 1
    fi
  else
    echo "[INFO] Aborting launch until spleeter-cli is built."
    exit 0
  fi
fi

cd "${ROOT_DIR}"
"${VENV_PY}" main.py
