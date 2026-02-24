@echo off
setlocal

set "ROOT_DIR=%~dp0"
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
    echo [ERROR] pipenv install failed.
    popd
    exit /b 1
)

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

echo [INFO] Building app (no terminal) with PyInstaller...
pipenv run pyinstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name pySSP ^
  --icon "pyssp\assets\app_icon.ico" ^
  --add-data "pyssp\assets;pyssp\assets" ^
  --add-data "docs\build\html;docs\build\html" ^
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

echo.
echo [SUCCESS] Build complete:
echo   %ROOT_DIR%dist\pySSP\pySSP.exe
echo   %ROOT_DIR%dist\pySSP\pySSP_cleanstart.bat
echo   %ROOT_DIR%dist\pySSP\pySSP_debug.bat

popd
exit /b 0
