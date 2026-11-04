#!/usr/bin/env bash
# Step 1: run inside the target-architecture Debian build environment.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$(uname -s)" == Linux ]] || { echo 'Linux is required.' >&2; exit 1; }
ARCH="$(dpkg --print-architecture)"
[[ "$ARCH" == arm64 || "$ARCH" == amd64 ]] || { echo "Unsupported architecture: $ARCH" >&2; exit 1; }
BUILD="$ROOT/.build-linux/$ARCH"
PY="$BUILD/spleeter-venv/bin/python"
mkdir -p "$BUILD"
# Do not let a failed rebuild advertise an older bundle as freshly validated.
rm -f "$BUILD/spleeter-dist/spleeter-cli/build-architecture.txt"
if [[ ! -x "$PY" ]]; then
    "${SPLEETER_PYTHON:-python3.11}" -m venv "$BUILD/spleeter-venv"
fi
"$PY" -c 'import sys; assert sys.version_info[:2] == (3, 11), "Python 3.11 required"'
"$PY" -m pip install --no-compile --disable-pip-version-check -r "$ROOT/spleeter-cli/requirements-linux.txt"
"$PY" -m pip check
MODEL="$ROOT/spleeter-cli/models/2stems"
for file in checkpoint model.index model.meta model.data-00000-of-00001; do
    [[ -s "$MODEL/$file" ]] || { echo "Missing model file: $MODEL/$file" >&2; exit 1; }
done
export CUDA_VISIBLE_DEVICES=-1 TF_CPP_MIN_LOG_LEVEL=2
export TF_NUM_INTRAOP_THREADS="${TF_NUM_INTRAOP_THREADS:-2}"
export TF_NUM_INTEROP_THREADS="${TF_NUM_INTEROP_THREADS:-1}"
cd "$ROOT"
"$PY" -c 'import tensorflow as tf; from scipy.io import wavfile; from spleeter.separator import Separator; print(tf.__version__)'
"$PY" -m unittest discover -s spleeter-cli/tests -v
"$PY" -m PyInstaller --noconfirm --clean --distpath "$BUILD/spleeter-dist" \
    --workpath "$BUILD/spleeter-work" packaging/linux/spleeter.spec
"$BUILD/spleeter-dist/spleeter-cli/spleeter-cli" --help
"$PY" -m pip freeze > "$BUILD/spleeter-dist/spleeter-cli/requirements-build.txt"
printf '%s\n' "$ARCH" > "$BUILD/spleeter-dist/spleeter-cli/build-architecture.txt"
echo "Built $BUILD/spleeter-dist/spleeter-cli"
