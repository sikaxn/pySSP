@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "VERSION_FILE=%ROOT_DIR%version.json"
set "GENERATED_VERSION_DIR=%ROOT_DIR%.build_meta"
set "GENERATED_VERSION_FILE=%GENERATED_VERSION_DIR%\version.json"
set "APP_VERSION=0.0.0"
set "APP_BUILD_ID="
set "APP_BASENAME=pySSP-%APP_VERSION%"
set "APP_EXE_NAME=pySSP"
set "PIPENV_IGNORE_VIRTUALENVS=1"
set "PIPENV_VENV_IN_PROJECT=1"
pushd "%ROOT_DIR%"

where pipenv >nul 2>&1
if errorlevel 1 (
    echo [INFO] pipenv not found. Installing with Python launcher...
    py -m pip install --user pipenv
    if errorlevel 1 (
        echo [ERROR] Failed to install pipenv.
        popd
        exit /b 1
    )
)

echo [INFO] Ensuring pipenv uses Python 3.12...
pipenv --python 3.12
if errorlevel 1 (
    echo [ERROR] Could not create/select a Python 3.12 pipenv.
    popd
    exit /b 1
)

set "PY_OK="
for /f %%i in ('pipenv run python -c "import sys; print('ok' if sys.version_info[:2] == (3, 12) else 'bad')"') do set "PY_OK=%%i"
if /I not "%PY_OK%"=="ok" (
    echo [WARN] Existing pipenv is not using Python 3.12. Recreating environment...
    pipenv --rm
    pipenv --python 3.12
    if errorlevel 1 (
        echo [ERROR] Failed to recreate pipenv with Python 3.12.
        popd
        exit /b 1
    )
)

echo [INFO] Installing dependencies from Pipfile.lock/Pipfile...
pipenv install --dev
if errorlevel 1 (
    echo [WARN] Locked dependency install failed. Retrying without lock...
    pipenv install --dev --skip-lock
    if errorlevel 1 (
        echo [ERROR] pipenv install failed.
        popd
        exit /b 1
    )
)

if exist "%VERSION_FILE%" (
    if not exist "%GENERATED_VERSION_DIR%" mkdir "%GENERATED_VERSION_DIR%"
    for /f "usebackq tokens=1,2 delims==" %%A in (`pipenv run python scripts\generate_build_version.py --source "%VERSION_FILE%" --output "%GENERATED_VERSION_FILE%"`) do (
        if /I "%%A"=="version" set "APP_VERSION=%%B"
        if /I "%%A"=="build_id" set "APP_BUILD_ID=%%B"
    )
    if not exist "%GENERATED_VERSION_FILE%" (
        echo [ERROR] Failed to generate build metadata version file.
        popd
        exit /b 1
    )
)
set "APP_BASENAME=pySSP-%APP_VERSION%"
echo [INFO] Build version: %APP_VERSION%
if defined APP_BUILD_ID echo [INFO] Build id: %APP_BUILD_ID%

echo [INFO] Cleaning previous PyInstaller output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [INFO] Building documentation HTML...
if not exist docs\source\conf.py (
    echo [ERROR] docs\source\conf.py not found.
    popd
    exit /b 1
)
pipenv run sphinx-build -b html docs\source docs\build\html
if errorlevel 1 (
    echo [ERROR] Documentation build failed.
    popd
    exit /b 1
)
if not exist docs\build\html\index.html (
    echo [ERROR] Missing docs\build\html\index.html after documentation build.
    popd
    exit /b 1
)

set "HAS_SPLEETER="
for /f %%i in ('pipenv run python -c "import importlib.util; print('yes' if importlib.util.find_spec('spleeter') else 'no')"') do set "HAS_SPLEETER=%%i"
set "SPLEETER_PYI_ARGS="
if /I "%HAS_SPLEETER%"=="yes" (
    echo [INFO] Preparing bundled Spleeter 2stems model...
    pipenv run python scripts\prepare_spleeter_model.py --output "pyssp\assets\spleeter_models"
    if errorlevel 1 (
        echo [WARN] Failed to prepare Spleeter model assets. Continuing without bundled Spleeter.
        set "HAS_SPLEETER=no"
    )
)
if /I "%HAS_SPLEETER%"=="yes" (
    set "SPLEETER_PYI_ARGS=--collect-all spleeter --hidden-import spleeter.separator --hidden-import spleeter.model.provider"
) else (
    echo [WARN] Spleeter not installed for this Python environment. Vocal removal will be unavailable in this build.
)

echo [INFO] Building app (no terminal) with PyInstaller...
pipenv run pyinstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name %APP_EXE_NAME% ^
  --icon "pyssp\assets\app_icon.ico" ^
  --collect-data "imageio_ffmpeg" ^
  %SPLEETER_PYI_ARGS% ^
  --add-data "pyssp\assets;pyssp\assets" ^
  --add-data "pyssp\bin;pyssp\bin" ^
  --add-data "docs\build\html;docs\build\html" ^
  --add-data ".build_meta\version.json;." ^
  main.py
if errorlevel 1 (
    echo [ERROR] PyInstaller GUI build failed.
    popd
    exit /b 1
)

echo [INFO] Adding cleanstart launcher...
(
  echo @echo off
  echo setlocal
  echo set "EXE_DIR=%%~dp0"
  echo "%%EXE_DIR%%pySSP.exe" --cleanstart
  echo exit /b %%ERRORLEVEL%%
) > "%ROOT_DIR%dist\pySSP\pySSP_cleanstart.bat"
if errorlevel 1 (
    echo [ERROR] Failed to create cleanstart launcher.
    popd
    exit /b 1
)

echo [INFO] Adding debug launcher...
(
  echo @echo off
  echo setlocal
  echo set "EXE_DIR=%%~dp0"
  echo "%%EXE_DIR%%pySSP.exe" -debug
  echo exit /b %%ERRORLEVEL%%
) > "%ROOT_DIR%dist\pySSP\pySSP_debug.bat"
if errorlevel 1 (
    echo [ERROR] Failed to create debug launcher.
    popd
    exit /b 1
)

if exist "%ROOT_DIR%dist\%APP_BASENAME%" rmdir /s /q "%ROOT_DIR%dist\%APP_BASENAME%"
set "FINAL_DIST=%ROOT_DIR%dist\%APP_BASENAME%"
move "%ROOT_DIR%dist\pySSP" "%ROOT_DIR%dist\%APP_BASENAME%" >nul
if errorlevel 1 (
    echo [WARN] Could not rename dist folder to versioned name. Using dist\pySSP output folder.
    set "FINAL_DIST=%ROOT_DIR%dist\pySSP"
)

echo.
echo [SUCCESS] Build complete:
echo   %FINAL_DIST%\pySSP.exe
echo   %FINAL_DIST%\pySSP_cleanstart.bat
echo   %FINAL_DIST%\pySSP_debug.bat

popd
exit /b 0
