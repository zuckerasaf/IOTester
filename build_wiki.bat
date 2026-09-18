@echo off
rem Build the Wiki (mkdocs site) only - converts docs\*.md into site\*.html
rem Run this whenever docs\ content changes, without rebuilding the EXE/installer.

setlocal enabledelayedexpansion

echo ========================================
echo Building IO Tester Wiki (mkdocs)
echo ========================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

%PY_CMD% -m mkdocs build
if errorlevel 1 (
    echo.
    echo ERROR: Wiki build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Wiki build complete: site\index.html
echo ========================================
pause
endlocal
