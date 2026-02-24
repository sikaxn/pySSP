@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
set "VERSION_FILE=%ROOT_DIR%version.json"
set "APP_VERSION=0.0.0"
if exist "%VERSION_FILE%" (
    for /f %%i in ('python -c "import json; print(json.load(open('version.json','r',encoding='utf-8')).get('version','0.0.0'))"') do set "APP_VERSION=%%i"
)
set "APP_BASENAME=pySSP-%APP_VERSION%"
set "DIST_DIR=%ROOT_DIR%dist\%APP_BASENAME%"
set "MAIN_EXE=%DIST_DIR%\pySSP.exe"
set "SOURCE_ABOUT_MD=%ROOT_DIR%pyssp\assets\about\about.md"
set "SOURCE_LOGO_PNG=%ROOT_DIR%pyssp\assets\logo2.png"
set "REQUIRED_ABOUT_MD=%DIST_DIR%\_internal\pyssp\assets\about\about.md"
set "REQUIRED_LOGO=%DIST_DIR%\_internal\pyssp\assets\logo2.png"
set "OUTPUT_DIR=%ROOT_DIR%dist"
set "INSTALLER_NAME=%APP_BASENAME%-setup.exe"

pushd "%ROOT_DIR%"

if not exist "%MAIN_EXE%" (
    echo [ERROR] Missing "%MAIN_EXE%".
    echo [INFO] Run build_pyinstaller.bat first.
    popd
    exit /b 1
)
if not exist "%SOURCE_ABOUT_MD%" (
    echo [ERROR] Missing "%SOURCE_ABOUT_MD%".
    popd
    exit /b 1
)
if not exist "%SOURCE_LOGO_PNG%" (
    echo [ERROR] Missing "%SOURCE_LOGO_PNG%".
    popd
    exit /b 1
)
if not exist "%REQUIRED_ABOUT_MD%" (
    echo [ERROR] Missing "%REQUIRED_ABOUT_MD%".
    echo [INFO] About markdown was not found in dist payload. Re-run build_pyinstaller.bat.
    popd
    exit /b 1
)
if not exist "%REQUIRED_LOGO%" (
    echo [ERROR] Missing "%REQUIRED_LOGO%".
    echo [INFO] About logo was not found in dist payload. Re-run build_pyinstaller.bat.
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
set "ABOUT_PAGE_FILE=%TEMP%\pySSP_about_%RANDOM%%RANDOM%.txt"
set "LOGO_BMP=%TEMP%\pySSP_logo_%RANDOM%%RANDOM%.bmp"

powershell -NoProfile -Command "$content = Get-Content -Raw '%SOURCE_ABOUT_MD%'; $content = $content.Replace('{{VERSION}}','%APP_VERSION%'); Set-Content -Path '%ABOUT_PAGE_FILE%' -Value $content -Encoding UTF8"
if errorlevel 1 (
    echo [ERROR] Failed to prepare About page text for NSIS.
    popd
    exit /b 1
)

powershell -NoProfile -Command "Add-Type -AssemblyName System.Drawing; $img=[System.Drawing.Image]::FromFile('%SOURCE_LOGO_PNG%'); $tw=164; $th=314; $bmp=New-Object System.Drawing.Bitmap($tw,$th); $g=[System.Drawing.Graphics]::FromImage($bmp); $g.Clear([System.Drawing.Color]::White); $scale=[Math]::Min($tw / [double]$img.Width, $th / [double]$img.Height); $dw=[int]($img.Width*$scale); $dh=[int]($img.Height*$scale); $dx=[int](($tw-$dw)/2); $dy=[int](($th-$dh)/2); $g.DrawImage($img, $dx, $dy, $dw, $dh); $g.Dispose(); $bmp.Save('%LOGO_BMP%', [System.Drawing.Imaging.ImageFormat]::Bmp); $bmp.Dispose(); $img.Dispose()"
if errorlevel 1 (
    echo [ERROR] Failed to prepare NSIS logo bitmap.
    del /q "%ABOUT_PAGE_FILE%" >nul 2>&1
    popd
    exit /b 1
)

(
    echo Name "%APP_BASENAME%"
    echo OutFile "%OUTPUT_DIR%\%INSTALLER_NAME%"
    echo InstallDir "$PROGRAMFILES\pySSP"
    echo RequestExecutionLevel admin
    echo SetCompressor /SOLID lzma
    echo !include "MUI2.nsh"
    echo !include "nsDialogs.nsh"
    echo !include "LogicLib.nsh"
    echo Var AppDataChoice
    echo Var AppDataPromptLabel
    echo Var AppDataUpdateRadio
    echo Var AppDataCleanRadio
    echo !define MUI_WELCOMEFINISHPAGE_BITMAP "%LOGO_BMP%"
    echo !insertmacro MUI_PAGE_WELCOME
    echo Page Custom AppDataModePage AppDataModePageLeave
    echo !insertmacro MUI_PAGE_LICENSE "%ABOUT_PAGE_FILE%"
    echo !insertmacro MUI_PAGE_DIRECTORY
    echo !insertmacro MUI_PAGE_INSTFILES
    echo !insertmacro MUI_PAGE_FINISH
    echo !insertmacro MUI_UNPAGE_CONFIRM
    echo !insertmacro MUI_UNPAGE_INSTFILES
    echo !insertmacro MUI_LANGUAGE "English"
    echo.
    echo Function .onInit
    echo   nsExec::ExecToStack 'cmd /C tasklist /FI "IMAGENAME eq pySSP.exe" /NH ^| findstr /I /C:"pySSP.exe"'
    echo   Pop $0
    echo   Pop $1
    echo   StrCmp $0 "0" RunningDetected
    echo   nsExec::ExecToStack 'cmd /C tasklist /FI "IMAGENAME eq pySSP-*.exe" /NH ^| findstr /I /C:"pySSP-"'
    echo   Pop $0
    echo   Pop $1
    echo   StrCmp $0 "0" RunningDetected NoRunningInstance
    echo RunningDetected:
    echo   MessageBox MB_ICONEXCLAMATION^|MB_YESNO "pySSP is currently running. Quit pySSP now to continue installation?" IDYES TryQuit IDNO CancelInstall
    echo TryQuit:
    echo   nsExec::ExecToStack 'cmd /C taskkill /F /IM pySSP.exe ^& taskkill /F /IM pySSP-*.exe'
    echo   Pop $2
    echo   Pop $3
    echo   Sleep 900
    echo   nsExec::ExecToStack 'cmd /C tasklist /FI "IMAGENAME eq pySSP.exe" /NH ^| findstr /I /C:"pySSP.exe"'
    echo   Pop $4
    echo   Pop $5
    echo   StrCmp $4 "0" QuitFailed
    echo   nsExec::ExecToStack 'cmd /C tasklist /FI "IMAGENAME eq pySSP-*.exe" /NH ^| findstr /I /C:"pySSP-"'
    echo   Pop $4
    echo   Pop $5
    echo   StrCmp $4 "0" QuitFailed NoRunningInstance
    echo QuitFailed:
    echo   MessageBox MB_ICONSTOP "Could not close pySSP automatically. Please close pySSP manually, then run installer again."
    echo   Abort
    echo CancelInstall:
    echo   Abort
    echo NoRunningInstance:
    echo FunctionEnd
    echo.
    echo Function AppDataModePage
    echo   StrCpy $AppDataChoice "update"
    echo   IfFileExists "$APPDATA\pySSP\*.*" 0 NoAppDataFound
    echo   nsDialogs::Create 1018
    echo   Pop $0
    echo   ${If} $0 == error
    echo     Abort
    echo   ${EndIf}
    echo   ${NSD_CreateLabel} 0 0 100%% 28u "Existing settings were found in $APPDATA\pySSP. Choose update mode:"
    echo   Pop $AppDataPromptLabel
    echo   ${NSD_CreateRadioButton} 0 34u 100%% 12u "Update (keep existing AppData settings)"
    echo   Pop $AppDataUpdateRadio
    echo   ${NSD_Check} $AppDataUpdateRadio
    echo   ${NSD_CreateRadioButton} 0 50u 100%% 12u "Clean install (remove existing AppData settings)"
    echo   Pop $AppDataCleanRadio
    echo   nsDialogs::Show
    echo   Return
    echo NoAppDataFound:
    echo   Abort
    echo FunctionEnd
    echo.
    echo Function AppDataModePageLeave
    echo   IfFileExists "$APPDATA\pySSP\*.*" 0 EndChoice
    echo   ${NSD_GetState} $AppDataCleanRadio $0
    echo   ${If} $0 == ${BST_CHECKED}
    echo     StrCpy $AppDataChoice "clean"
    echo   ${Else}
    echo     StrCpy $AppDataChoice "update"
    echo   ${EndIf}
    echo EndChoice:
    echo FunctionEnd
    echo.
    echo Section "Install"
    echo IfFileExists "$INSTDIR\*.*" 0 +2
    echo RMDir /r "$INSTDIR"
    echo StrCmp $AppDataChoice "clean" 0 +2
    echo RMDir /r "$APPDATA\pySSP"
    echo SetOutPath "$INSTDIR"
    echo File /r "%DIST_DIR%\*"
    echo CreateDirectory "$SMPROGRAMS\pySSP"
    echo CreateShortcut "$SMPROGRAMS\pySSP\pySSP.lnk" "$INSTDIR\pySSP.exe"
    echo CreateShortcut "$SMPROGRAMS\pySSP\pySSP cleanstart.lnk" "$INSTDIR\pySSP_cleanstart.bat"
    echo CreateShortcut "$SMPROGRAMS\pySSP\pySSP debug.lnk" "$INSTDIR\pySSP_debug.bat"
    echo CreateShortcut "$DESKTOP\pySSP.lnk" "$INSTDIR\pySSP.exe"
    echo WriteUninstaller "$INSTDIR\Uninstall.exe"
    echo WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\pySSP" "DisplayName" "%APP_BASENAME%"
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
    del /q "%ABOUT_PAGE_FILE%" >nul 2>&1
    del /q "%LOGO_BMP%" >nul 2>&1
    popd
    exit /b 1
)

echo [INFO] Building installer with:
echo        "%MAKENSIS%"
"%MAKENSIS%" "%NSI_FILE%"
set "NSIS_EXIT=%ERRORLEVEL%"

del /q "%NSI_FILE%" >nul 2>&1
del /q "%ABOUT_PAGE_FILE%" >nul 2>&1
del /q "%LOGO_BMP%" >nul 2>&1

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
