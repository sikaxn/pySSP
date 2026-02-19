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

pushd "%ROOT_DIR%"
"%VENV_PY%" main.py --cleanstart
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
