@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
set "DIST_DIR=%ROOT_DIR%dist\pySSP"
set "MAIN_EXE=%DIST_DIR%\pySSP.exe"
set "OUTPUT_DIR=%ROOT_DIR%dist"
set "INSTALLER_NAME=pySSP-setup.exe"

pushd "%ROOT_DIR%"

if not exist "%MAIN_EXE%" (
    echo [ERROR] Missing "%MAIN_EXE%".
    echo [INFO] Run build_pyinstaller.bat first.
    popd
    exit /b 1
)

if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
    if errorlevel 1 (
        echo [ERROR] Could not create output directory: "%OUTPUT_DIR%"
        popd
        exit /b 1
    )
)

set "MAKENSIS="
if defined NSIS_HOME if exist "%NSIS_HOME%\makensis.exe" set "MAKENSIS=%NSIS_HOME%\makensis.exe"
if not defined MAKENSIS if exist "%ProgramFiles(x86)%\NSIS\makensis.exe" set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
if not defined MAKENSIS if exist "%ProgramFiles%\NSIS\makensis.exe" set "MAKENSIS=%ProgramFiles%\NSIS\makensis.exe"
if not defined MAKENSIS (
    for /f "delims=" %%I in ('where makensis 2^>nul') do (
        set "MAKENSIS=%%I"
        goto :found_makensis
    )
)
:found_makensis
if not defined MAKENSIS (
    echo [ERROR] NSIS makensis.exe not found.
    echo [INFO] Install NSIS from https://nsis.sourceforge.io/Download
    echo [INFO] Then re-run this script.
    popd
    exit /b 1
)

set "NSI_FILE=%TEMP%\pySSP_installer_%RANDOM%%RANDOM%.nsi"

(
    echo Name "pySSP"
    echo OutFile "%OUTPUT_DIR%\%INSTALLER_NAME%"
    echo InstallDir "$PROGRAMFILES\pySSP"
    echo RequestExecutionLevel admin
    echo SetCompressor /SOLID lzma
    echo !include "MUI2.nsh"
    echo !insertmacro MUI_PAGE_WELCOME
    echo !insertmacro MUI_PAGE_DIRECTORY
    echo !insertmacro MUI_PAGE_INSTFILES
    echo !insertmacro MUI_PAGE_FINISH
    echo !insertmacro MUI_UNPAGE_CONFIRM
    echo !insertmacro MUI_UNPAGE_INSTFILES
    echo !insertmacro MUI_LANGUAGE "English"
    echo.
    echo Section "Install"
    echo SetOutPath "$INSTDIR"
    echo File /r "%DIST_DIR%\*"
    echo CreateDirectory "$SMPROGRAMS\pySSP"
    echo CreateShortcut "$SMPROGRAMS\pySSP\pySSP.lnk" "$INSTDIR\pySSP.exe"
    echo CreateShortcut "$SMPROGRAMS\pySSP\pySSP cleanstart.lnk" "$INSTDIR\pySSP_cleanstart.bat"
    echo CreateShortcut "$SMPROGRAMS\pySSP\pySSP debug.lnk" "$INSTDIR\pySSP_debug.bat"
    echo CreateShortcut "$DESKTOP\pySSP.lnk" "$INSTDIR\pySSP.exe"
    echo WriteUninstaller "$INSTDIR\Uninstall.exe"
    echo WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\pySSP" "DisplayName" "pySSP"
    echo WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\pySSP" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    echo WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\pySSP" "InstallLocation" "$INSTDIR"
    echo WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\pySSP" "DisplayIcon" "$INSTDIR\pySSP.exe"
    echo WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\pySSP" "NoModify" 1
    echo WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\pySSP" "NoRepair" 1
    echo SectionEnd
    echo.
    echo Section "Uninstall"
    echo Delete "$DESKTOP\pySSP.lnk"
    echo Delete "$SMPROGRAMS\pySSP\pySSP.lnk"
    echo Delete "$SMPROGRAMS\pySSP\pySSP cleanstart.lnk"
    echo Delete "$SMPROGRAMS\pySSP\pySSP debug.lnk"
    echo Delete "$SMPROGRAMS\pySSP\*.*"
    echo RMDir "$SMPROGRAMS\pySSP"
    echo RMDir /r "$INSTDIR"
    echo DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\pySSP"
    echo SectionEnd
) > "%NSI_FILE%"

if errorlevel 1 (
    echo [ERROR] Failed to generate NSIS script.
    popd
    exit /b 1
)

echo [INFO] Building installer with:
echo        "%MAKENSIS%"
"%MAKENSIS%" "%NSI_FILE%"
set "NSIS_EXIT=%ERRORLEVEL%"

del /q "%NSI_FILE%" >nul 2>&1

if not "%NSIS_EXIT%"=="0" (
    echo [ERROR] NSIS build failed.
    popd
    exit /b %NSIS_EXIT%
)

echo.
echo [SUCCESS] Installer created:
echo   "%OUTPUT_DIR%\%INSTALLER_NAME%"

popd
exit /b 0
