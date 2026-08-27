@echo off
rem Complete Build Script for IO Tester Windows Installer
rem This script builds the executable with PyInstaller and then creates the installer with Inno Setup
rem
rem Prerequisites:
rem   1. Python virtual environment with all dependencies (.venv)
rem   2. Inno Setup installed (download from https://jrsoftware.org/isdl.php)
rem   3. Inno Setup added to PATH or installed in default location

setlocal enabledelayedexpansion

echo ========================================
echo IO Tester - Complete Build Process
echo ========================================
echo.

rem Step 1: Build the executable with PyInstaller
echo [1/3] Building executable with PyInstaller...
echo ========================================
call build_exe.bat
if errorlevel 1 (
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)
echo.
echo Executable built successfully in dist\IOTester\
echo.

rem Step 2: Check if Inno Setup is available
echo [2/3] Checking for Inno Setup...
echo ========================================
set "ISCC="

rem Try to find ISCC in PATH first
where ISCC.exe >nul 2>&1
if !errorlevel! equ 0 (
    set "ISCC=ISCC.exe"
    goto :found_iscc
)

rem Check common installation paths
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    goto :found_iscc
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
    goto :found_iscc
)

rem Inno Setup not found
echo ERROR: Inno Setup not found!
echo.
echo Please install Inno Setup from: https://jrsoftware.org/isdl.php
echo After installation, either:
echo   - Add Inno Setup to your PATH, or
echo   - Install to the default location: C:\Program Files (x86)\Inno Setup 6\
echo.
pause
exit /b 1

:found_iscc
echo Found Inno Setup: !ISCC!
echo.

rem Step 3: Build the installer
echo [3/3] Building Windows installer...
echo ========================================
"!ISCC!" installer.iss
if errorlevel 1 (
    echo ERROR: Installer build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD COMPLETE!
echo ========================================
echo.
echo Installer created successfully!
echo Location: installer_output\IOTester_Setup_v2.0.0.exe
echo.
echo You can now distribute this installer to your customers.
echo.
pause
