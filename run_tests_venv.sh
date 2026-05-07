#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "${VENV_PY}" ]]; then
  echo '[ERROR] Virtual environment not found at ".venv/bin/python"'
  echo
  echo "Create it with:"
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"

cd "${ROOT_DIR}"
echo "[INFO] Running full pytest suite with \"${VENV_PY}\""
set +e
"${VENV_PY}" -m pytest "$@"
EXIT_CODE=$?
set -e
if [[ ${EXIT_CODE} -eq 0 ]]; then
  echo "[INFO] Pytest completed successfully. Exit code: 0"
else
  echo "[ERROR] Pytest exited with code ${EXIT_CODE}"
fi
exit ${EXIT_CODE}

