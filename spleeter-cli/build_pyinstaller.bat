@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "CLI_DIR=%ROOT_DIR%\spleeter-cli"
set "DIST_DIR=%ROOT_DIR%\dist"
set "MODEL_DIR=%CLI_DIR%\models\2stems"
set "SPLEETER_VENV_DIR=%ROOT_DIR%\.venv-spleeter"
set "SPLEETER_PYTHON=%SPLEETER_VENV_DIR%\Scripts\python.exe"
set "MODEL_OK="

pushd "%ROOT_DIR%"

if not exist "%CLI_DIR%\main.py" (
    echo [ERROR] Missing spleeter-cli\main.py
    popd
    exit /b 1
)

if not exist "%SPLEETER_PYTHON%" (
    echo [ERROR] Missing Spleeter venv Python:
    echo [ERROR]   %SPLEETER_PYTHON%
    echo [ERROR] Create it first with:
    echo [ERROR]   py -3.11 -m venv .venv-spleeter
    popd
    exit /b 1
)

"%SPLEETER_PYTHON%" -c "import spleeter, tensorflow" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] .venv-spleeter is missing required modules.
    echo [ERROR] Install or repair:
    echo [ERROR]   .venv-spleeter\Scripts\python.exe -m pip install spleeter==2.4.2 pyinstaller
    popd
    exit /b 1
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

popd
exit /b 0
