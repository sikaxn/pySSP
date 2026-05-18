@ECHO OFF
setlocal

set "SPHINXBUILD=sphinx-build"
if exist "..\.venv\Scripts\sphinx-build.exe" set "SPHINXBUILD=..\.venv\Scripts\sphinx-build.exe"
set "PYTHON=python"
if exist "..\.venv\Scripts\python.exe" set "PYTHON=..\.venv\Scripts\python.exe"

%PYTHON% ..\scripts\generate_api_docs.py
if errorlevel 1 exit /b 1

%SPHINXBUILD% -b html source build/html %*
if errorlevel 1 exit /b 1

echo.
echo Built HTML docs: docs\build\html\index.html
