@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "CLI_DIR=%ROOT_DIR%\spleeter-cli"
set "DIST_DIR=%ROOT_DIR%\dist"
set "MODEL_DIR=%CLI_DIR%\models\2stems"
set "SPLEETER_VENV_DIR=%ROOT_DIR%\.venv-spleeter"
set "PY310_DEFAULT=%LocalAppData%\Programs\Python\Python310\python.exe"
set "PY310_ALT=%LocalAppData%\Programs\Python\Python310-64\python.exe"
set "SPLEETER_PYTHON=%SPLEETER_VENV_DIR%\Scripts\python.exe"
set "WINDOWS_REQUIREMENTS_FILE=%CLI_DIR%\requirements-windows.txt"
set "PYTHON_VERSION_FILE=%TEMP%\pyssp_spleeter_python_version.txt"
set "MODEL_OK="
set "BOOTSTRAP_PYTHON="

pushd "%ROOT_DIR%"

if not exist "%CLI_DIR%\main.py" (
    echo [ERROR] Missing spleeter-cli\main.py
    popd
    exit /b 1
)

for /f "delims=" %%i in ('py -3.10 -c "import sys; print(sys.executable)" 2^>nul') do set "BOOTSTRAP_PYTHON=%%i"
if not defined BOOTSTRAP_PYTHON if exist "%PY310_DEFAULT%" set "BOOTSTRAP_PYTHON=%PY310_DEFAULT%"
if not defined BOOTSTRAP_PYTHON if exist "%PY310_ALT%" set "BOOTSTRAP_PYTHON=%PY310_ALT%"

if not exist "%SPLEETER_PYTHON%" (
    if not defined BOOTSTRAP_PYTHON (
        echo [ERROR] Python 3.10 is required on Windows to build CUDA-capable spleeter-cli.
        echo [ERROR] Install Python 3.10 and retry.
        popd
        exit /b 1
    )
    "%BOOTSTRAP_PYTHON%" -m venv "%SPLEETER_VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv-spleeter with Python 3.10.
        echo [ERROR] Install Python 3.10 and retry.
        popd
        exit /b 1
    )
)

if exist "%PYTHON_VERSION_FILE%" del /q "%PYTHON_VERSION_FILE%" >nul 2>nul
set "PYTHON_VERSION="
"%SPLEETER_PYTHON%" -c "import sys; print('%%d.%%d' %% sys.version_info[:2])" > "%PYTHON_VERSION_FILE%" 2>nul
if exist "%PYTHON_VERSION_FILE%" set /p PYTHON_VERSION=<"%PYTHON_VERSION_FILE%"
if exist "%PYTHON_VERSION_FILE%" del /q "%PYTHON_VERSION_FILE%" >nul 2>nul
if not "%PYTHON_VERSION%"=="3.10" (
    echo [ERROR] .venv-spleeter must use Python 3.10 on Windows for native CUDA-capable TensorFlow builds.
    echo [ERROR] Current version: %PYTHON_VERSION%
    echo [ERROR] Recreate it with:
    echo [ERROR]   rmdir /s /q .venv-spleeter
    if defined BOOTSTRAP_PYTHON (
        echo [ERROR]   "%BOOTSTRAP_PYTHON%" -m venv .venv-spleeter
    ) else (
        echo [ERROR]   py -3.10 -m venv .venv-spleeter
    )
    popd
    exit /b 1
)

"%SPLEETER_PYTHON%" -c "import ffmpeg, httpx, norbert, pandas, scipy, spleeter, tensorflow as tf, typer; assert str(tf.__version__).startswith('2.10.')" >nul 2>nul
if errorlevel 1 (
    if not exist "%WINDOWS_REQUIREMENTS_FILE%" (
        echo [ERROR] Missing Windows requirements file:
        echo [ERROR]   %WINDOWS_REQUIREMENTS_FILE%
        popd
        exit /b 1
    )
    echo [INFO] Installing Windows-compatible Spleeter dependencies into .venv-spleeter...
    "%SPLEETER_PYTHON%" -m pip install --upgrade pip setuptools wheel
    if errorlevel 1 (
        echo [ERROR] Failed to upgrade pip tooling.
        popd
        exit /b 1
    )
    "%SPLEETER_PYTHON%" -m pip install -r "%WINDOWS_REQUIREMENTS_FILE%"
    if errorlevel 1 (
        echo [ERROR] Failed to install Windows requirements.
        popd
        exit /b 1
    )
    "%SPLEETER_PYTHON%" -m pip install --no-deps "spleeter==2.4.2"
    if errorlevel 1 (
        echo [ERROR] Failed to install spleeter==2.4.2.
        popd
        exit /b 1
    )
    "%SPLEETER_PYTHON%" -c "import ffmpeg, httpx, norbert, pandas, scipy, spleeter, tensorflow as tf, typer; assert str(tf.__version__).startswith('2.10.')" >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Windows build requires TensorFlow 2.10.x for native CUDA support.
        popd
        exit /b 1
    )
)

"%SPLEETER_PYTHON%" -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo [INFO] Installing PyInstaller into .venv-spleeter...
    "%SPLEETER_PYTHON%" -m pip install pyinstaller==6.10.0
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller into .venv-spleeter.
        popd
        exit /b 1
    )
)

if exist "%MODEL_DIR%\checkpoint" if exist "%MODEL_DIR%\model.index" if exist "%MODEL_DIR%\model.meta" set "MODEL_OK=yes"
if defined MODEL_OK (
    echo [INFO] Using checked-in Spleeter model:
    echo [INFO]   %MODEL_DIR%
) else (
    echo [INFO] Preparing bundled Spleeter model...
    "%SPLEETER_PYTHON%" "%CLI_DIR%\prepare_spleeter_model.py" --output "%CLI_DIR%\models"
    if errorlevel 1 (
        echo [ERROR] Failed to prepare Spleeter model.
        popd
        exit /b 1
    )
)

if exist "%DIST_DIR%\spleeter-cli" rmdir /s /q "%DIST_DIR%\spleeter-cli"
if exist "%ROOT_DIR%\build\spleeter-cli" rmdir /s /q "%ROOT_DIR%\build\spleeter-cli"

echo [INFO] Building spleeter-cli with PyInstaller...
"%SPLEETER_PYTHON%" -m PyInstaller --noconfirm --clean "%CLI_DIR%\spleeter-cli.spec"
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed for spleeter-cli.
    popd
    exit /b 1
)

echo.
echo [SUCCESS] Built:
echo   %DIST_DIR%\spleeter-cli\spleeter-cli.exe
echo [INFO] Runtime backend selection inside the bundled CLI is automatic: CUDA if available, otherwise CPU.
echo [INFO] Native Windows CUDA requires TensorFlow 2.10.x with CUDA 11.2 and cuDNN 8.1 installed on the target machine.

popd
exit /b 0
