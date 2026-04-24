@echo off
setlocal

set "ROOT_DIR=%~dp0"
call "%ROOT_DIR%run_tests_venv.bat" %*
exit /b %ERRORLEVEL%
