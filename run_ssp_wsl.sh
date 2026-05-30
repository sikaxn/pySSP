#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-wsl"
VENV_PY="${VENV_DIR}/bin/python"
ACTION="run"

if [[ $# -gt 0 ]]; then
  ACTION="$1"
  shift
fi

usage() {
  cat <<'EOF'
Usage: ./run_ssp_wsl.sh [setup|run|test|help] [args...]

Commands:
  setup  Create .venv-wsl and install requirements.txt
  run    Launch pySSP from .venv-wsl
  test   Run pytest in offscreen Qt mode from .venv-wsl
  help   Show this message

Examples:
  ./run_ssp_wsl.sh setup
  ./run_ssp_wsl.sh
  ./run_ssp_wsl.sh run --cleanstart
  ./run_ssp_wsl.sh test test_http_5050_server.py
EOF
}

require_command() {
  local cmd="$1"
  if command -v "${cmd}" >/dev/null 2>&1; then
    return 0
  fi
  echo "[ERROR] Required command not found: ${cmd}"
  exit 1
}

print_apt_hint() {
  cat <<'EOF'
[INFO] Install the required Ubuntu packages with:
  sudo apt update
  sudo apt install -y python3-pip python3-venv python3.12-venv libasound2t64 libportaudio2 libegl1 libgl1
  sudo apt install -y libpulse0 libasound2-plugins libsdl2-2.0-0 pulseaudio-utils
  sudo apt install -y libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0
EOF
}

ensure_venv() {
  if [[ -x "${VENV_PY}" ]]; then
    return 0
  fi

  require_command python3

  echo "[INFO] Creating WSL virtual environment at ${VENV_DIR}"
  if ! python3 -m venv "${VENV_DIR}"; then
    echo "[ERROR] Failed to create ${VENV_DIR}"
    print_apt_hint
    exit 1
  fi
}

install_requirements() {
  ensure_venv

  echo "[INFO] Installing Python dependencies into ${VENV_DIR}"
  "${VENV_PY}" -m pip install --upgrade pip
  "${VENV_PY}" -m pip install -r "${ROOT_DIR}/requirements.txt"
}

ensure_requirements() {
  ensure_venv

  if "${VENV_PY}" -c "import PyQt5, pygame, numpy, sounddevice, pedalboard, flask" >/dev/null 2>&1; then
    return 0
  fi

  install_requirements
}

warn_if_gui_env_missing() {
  if [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]; then
    return 0
  fi

  cat <<'EOF'
[WARN] DISPLAY and WAYLAND_DISPLAY are both unset.
[WARN] GUI launch may fail unless WSLg is active in this shell session.
[WARN] Headless tests still work with: ./run_ssp_wsl.sh test
EOF
}

configure_wslg_env() {
  if [[ ! -S /mnt/wslg/runtime-dir/wayland-0 ]]; then
    return 0
  fi

  local uid runtime_dir
  uid="$(id -u)"
  runtime_dir="/run/user/${uid}"

  if [[ -d "${runtime_dir}" ]]; then
    export XDG_RUNTIME_DIR="${runtime_dir}"
  else
    export XDG_RUNTIME_DIR="/mnt/wslg/runtime-dir"
  fi

  export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
  export DISPLAY="${DISPLAY:-:0}"
  export PULSE_SERVER="${PULSE_SERVER:-unix:/mnt/wslg/PulseServer}"
  export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-pulseaudio}"

  if [[ -z "${QT_QPA_PLATFORM:-}" ]]; then
    export QT_QPA_PLATFORM=wayland
  fi

  if [[ -z "${QT_OPENGL:-}" ]]; then
    export QT_OPENGL=software
  fi

  if [[ -z "${LIBGL_ALWAYS_SOFTWARE:-}" ]]; then
    export LIBGL_ALWAYS_SOFTWARE=1
  fi

  if [[ -z "${PYSSP_DEFAULT_LANGUAGE:-}" ]]; then
    export PYSSP_DEFAULT_LANGUAGE=en
  fi

  echo "[INFO] Detected WSLg runtime; exported GUI and audio environment."
}

check_xcb_runtime() {
  local plugin missing
  plugin="${VENV_DIR}/lib/python3.12/site-packages/PyQt5/Qt5/plugins/platforms/libqxcb.so"

  if [[ ! -f "${plugin}" ]]; then
    return 0
  fi

  missing="$(ldd "${plugin}" 2>/dev/null | awk '/=> not found/{print $1}' | sort -u)"
  if [[ -z "${missing}" ]]; then
    return 0
  fi

  cat <<EOF
[WARN] Qt xcb runtime dependencies are missing:
${missing}
[WARN] If you force Qt to use xcb, install:
  sudo apt install -y libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0
EOF
}

warn_about_spleeter() {
  local linux_spleeter="${ROOT_DIR}/dist/spleeter-cli/spleeter-cli"
  local windows_spleeter="${ROOT_DIR}/dist/spleeter-cli/spleeter-cli.exe"

  if [[ -x "${linux_spleeter}" || ! -f "${windows_spleeter}" ]]; then
    return 0
  fi

  cat <<'EOF'
[WARN] Only the Windows spleeter-cli build is present in this checkout.
[WARN] pySSP can still launch in WSL, but the vocal-removal tooling will stay unavailable
[WARN] until a Linux spleeter-cli binary is added.
EOF
}

run_app() {
  ensure_requirements
  configure_wslg_env
  warn_if_gui_env_missing
  check_xcb_runtime
  warn_about_spleeter

  cd "${ROOT_DIR}"
  exec "${VENV_PY}" main.py "$@"
}

run_tests() {
  ensure_requirements
  export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"

  cd "${ROOT_DIR}"
  echo "[INFO] Running pytest with ${VENV_PY}"
  exec "${VENV_PY}" -m pytest "$@"
}

case "${ACTION}" in
  setup)
    install_requirements
    ;;
  run)
    run_app "$@"
    ;;
  test)
    run_tests "$@"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "[ERROR] Unknown command: ${ACTION}"
    echo
    usage
    exit 2
    ;;
esac
