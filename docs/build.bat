@ECHO OFF
setlocal

set "SPHINXBUILD=sphinx-build"
if exist "..\.venv\Scripts\sphinx-build.exe" set "SPHINXBUILD=..\.venv\Scripts\sphinx-build.exe"

%SPHINXBUILD% -b html source build/html %*
if errorlevel 1 exit /b 1

echo.
echo Built HTML docs: docs\build\html\index.html
