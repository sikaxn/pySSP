@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "VENV_PY=%ROOT_DIR%.venv\Scripts\python.exe"
set "SPLEETER_CLI_EXE=%ROOT_DIR%dist\spleeter-cli\spleeter-cli.exe"
set "SPLEETER_CLI_BUILD=%ROOT_DIR%spleeter-cli\build_pyinstaller.bat"

if not exist "%VENV_PY%" (
    echo [ERROR] Virtual environment not found at ".venv\Scripts\python.exe"
    echo.
    echo Create it with:
    echo   python -m venv .venv
    echo   .venv\Scripts\python -m pip install -r requirements.txt
    exit /b 1
)

if not exist "%SPLEETER_CLI_EXE%" (
    echo [WARN] Prebuilt spleeter-cli not found:
    echo [WARN]   %SPLEETER_CLI_EXE%
    echo.
    choice /C YN /N /M "Build spleeter-cli now? [Y/N]: "
    if errorlevel 2 (
        echo [INFO] Aborting launch until spleeter-cli is built.
        exit /b 0
    )
    if not exist "%SPLEETER_CLI_BUILD%" (
        echo [ERROR] Missing build script:
        echo [ERROR]   %SPLEETER_CLI_BUILD%
        exit /b 1
    )
    pushd "%ROOT_DIR%spleeter-cli"
    call build_pyinstaller.bat
    set "SPLEETER_BUILD_EXIT=%ERRORLEVEL%"
    popd
    if not "%SPLEETER_BUILD_EXIT%"=="0" (
        echo [ERROR] spleeter-cli build failed.
        exit /b %SPLEETER_BUILD_EXIT%
    )
    if not exist "%SPLEETER_CLI_EXE%" (
        echo [ERROR] spleeter-cli build completed but executable is still missing.
        echo [ERROR]   %SPLEETER_CLI_EXE%
        exit /b 1
    )
)

pushd "%ROOT_DIR%"
"%VENV_PY%" main.py
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
