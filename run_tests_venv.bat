@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "VENV_PY=%ROOT_DIR%.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo [ERROR] Virtual environment not found at ".venv\Scripts\python.exe"
    echo.
    echo Create it with:
    echo   python -m venv .venv
    echo   .venv\Scripts\python -m pip install -r requirements.txt
    exit /b 1
)

if "%QT_QPA_PLATFORM%"=="" set "QT_QPA_PLATFORM=offscreen"

pushd "%ROOT_DIR%"
echo [INFO] Running test suite with "%VENV_PY%"
"%VENV_PY%" scripts\run_tests_stable.py %*
set "EXIT_CODE=%ERRORLEVEL%"
if "%EXIT_CODE%"=="0" (
    echo [INFO] Test suite completed successfully. Exit code: 0
) else (
    echo [ERROR] Test suite exited with code %EXIT_CODE%
)
popd

exit /b %EXIT_CODE%
