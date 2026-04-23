#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_DIR="${ROOT_DIR}/spleeter-cli"
DIST_DIR="${ROOT_DIR}/dist"
MODEL_DIR="${CLI_DIR}/models/2stems"
SPLEETER_VENV_DIR="${ROOT_DIR}/.venv-spleeter"
SPLEETER_PYTHON="${SPLEETER_VENV_DIR}/bin/python"
MACOS_REQUIREMENTS_FILE="${CLI_DIR}/requirements-macos.txt"
PYINSTALLER_BUILD_DIR="${ROOT_DIR}/build/spleeter-cli"
PYINSTALLER_WORK_DIR="${PYINSTALLER_BUILD_DIR}/work"
PYINSTALLER_SPEC_DIR="${PYINSTALLER_BUILD_DIR}/spec"

cd "${ROOT_DIR}"

find_python310() {
  local candidates=(
    "$(command -v python3.10 2>/dev/null || true)"
    "/opt/homebrew/bin/python3.10"
    "/usr/local/bin/python3.10"
  )
  local candidate=""
  for candidate in "${candidates[@]}"; do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

ensure_spleeter_venv() {
  local bootstrap_python=""
  if [[ -x "${SPLEETER_PYTHON}" ]]; then
    return 0
  fi

  if ! bootstrap_python="$(find_python310)"; then
    echo "[ERROR] Python 3.10 is required on macOS for spleeter-cli."
    echo "[ERROR] Install it with:"
    echo "[ERROR]   brew install python@3.10"
    exit 1
  fi

  echo "[INFO] Creating .venv-spleeter with ${bootstrap_python}..."
  "${bootstrap_python}" -m venv "${SPLEETER_VENV_DIR}"
}

ensure_spleeter_packages() {
  if "${SPLEETER_PYTHON}" -c "import importlib.util, ffmpeg, httpx, norbert, pandas, scipy, spleeter, tensorflow, typer; assert importlib.util.find_spec('tensorflow_metal') is not None" >/dev/null 2>&1; then
    return 0
  fi

  if [[ ! -f "${MACOS_REQUIREMENTS_FILE}" ]]; then
    echo "[ERROR] Missing macOS requirements file:"
    echo "[ERROR]   ${MACOS_REQUIREMENTS_FILE}"
    exit 1
  fi

  echo "[INFO] Installing macOS-compatible Spleeter dependencies into .venv-spleeter..."
  "${SPLEETER_PYTHON}" -m pip install --upgrade pip setuptools wheel
  "${SPLEETER_PYTHON}" -m pip install -r "${MACOS_REQUIREMENTS_FILE}"
  "${SPLEETER_PYTHON}" -m pip install --no-deps "spleeter==2.4.2"
  "${SPLEETER_PYTHON}" -c "import importlib.util, ffmpeg, httpx, norbert, pandas, scipy, spleeter, tensorflow, typer; assert importlib.util.find_spec('tensorflow_metal') is not None" >/dev/null 2>&1
}

if [[ ! -f "${CLI_DIR}/main.py" ]]; then
  echo "[ERROR] Missing spleeter-cli/main.py"
  exit 1
fi

ensure_spleeter_venv

PYTHON_VERSION="$("${SPLEETER_PYTHON}" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
if [[ "${PYTHON_VERSION}" != "3.10" ]]; then
  echo "[ERROR] .venv-spleeter must use Python 3.10 on macOS."
  echo "[ERROR] Current version: ${PYTHON_VERSION}"
  echo "[ERROR] Recreate it with:"
  echo "[ERROR]   rm -rf .venv-spleeter"
  echo "[ERROR]   /opt/homebrew/bin/python3.10 -m venv .venv-spleeter"
  exit 1
fi

ensure_spleeter_packages

if ! "${SPLEETER_PYTHON}" -m PyInstaller --version >/dev/null 2>&1; then
  echo "[INFO] Installing PyInstaller into .venv-spleeter..."
  if ! "${SPLEETER_PYTHON}" -m pip install "pyinstaller>=6.0"; then
    echo "[ERROR] Failed to install PyInstaller into .venv-spleeter."
    exit 1
  fi
fi

if [[ -f "${MODEL_DIR}/checkpoint" && -f "${MODEL_DIR}/model.index" && -f "${MODEL_DIR}/model.meta" ]]; then
  echo "[INFO] Using checked-in Spleeter model:"
  echo "[INFO]   ${MODEL_DIR}"
else
  echo "[INFO] Preparing bundled Spleeter model..."
  if ! "${SPLEETER_PYTHON}" "${CLI_DIR}/prepare_spleeter_model.py" --output "${CLI_DIR}/models"; then
    echo "[ERROR] Failed to prepare Spleeter model."
    exit 1
  fi
fi

rm -rf "${DIST_DIR}/spleeter-cli"
rm -rf "${PYINSTALLER_BUILD_DIR}"
mkdir -p "${DIST_DIR}" "${PYINSTALLER_WORK_DIR}" "${PYINSTALLER_SPEC_DIR}"

echo "[INFO] Building spleeter-cli with PyInstaller..."
if ! "${SPLEETER_PYTHON}" -m PyInstaller \
  --noconfirm \
  --clean \
  --distpath "${DIST_DIR}" \
  --workpath "${PYINSTALLER_WORK_DIR}" \
  --specpath "${PYINSTALLER_SPEC_DIR}" \
  --name "spleeter-cli" \
  --paths "${CLI_DIR}" \
  --collect-all "spleeter" \
  --collect-all "tensorflow" \
  --collect-all "tensorflow_metal" \
  --collect-all "scipy" \
  --collect-all "imageio_ffmpeg" \
  --add-data "${CLI_DIR}/models:models" \
  "${CLI_DIR}/main.py"; then
  echo "[ERROR] PyInstaller build failed for spleeter-cli."
  exit 1
fi

if [[ ! -x "${DIST_DIR}/spleeter-cli/spleeter-cli" ]]; then
  echo "[ERROR] Expected output not found:"
  echo "[ERROR]   ${DIST_DIR}/spleeter-cli/spleeter-cli"
  exit 1
fi

chmod +x "${DIST_DIR}/spleeter-cli/spleeter-cli" || true

echo
echo "[SUCCESS] Built:"
echo "  ${DIST_DIR}/spleeter-cli/spleeter-cli"
