@echo off
rem Create portable ZIP distribution of IO Tester
rem This ZIP version is less likely to be blocked by antivirus

setlocal enabledelayedexpansion

echo ========================================
echo Creating Portable ZIP Distribution
echo ========================================
echo.

rem Check if dist folder exists
if not exist "dist\IOTester\" (
    echo ERROR: dist\IOTester\ folder not found!
    echo Please run build_exe.bat first to create the executable.
    echo.
    pause
    exit /b 1
)

rem Create output directory
if not exist "portable_zip" mkdir portable_zip

rem Set ZIP filename with version
set "ZIP_NAME=IOTester_v1.0.0_Portable.zip"
set "OUTPUT_PATH=portable_zip\%ZIP_NAME%"

echo Creating portable package...
echo Source: dist\IOTester\
echo Output: %OUTPUT_PATH%
echo.

rem Check if PowerShell is available
where powershell >nul 2>&1
if errorlevel 1 (
    echo ERROR: PowerShell not found!
    pause
    exit /b 1
)

rem Create README for ZIP distribution
echo Creating README.txt for portable version...
(
echo IO TESTER - Portable Version
echo ========================================
echo.
echo This is a portable version of IO Tester that does not require installation.
echo.
echo QUICK START:
echo 1. Extract this ZIP file to any folder ^(e.g., C:\IOTester\^)
echo 2. Run IOTester.exe
echo 3. Configuration files are in the 'config' subfolder
echo.
echo ADVANTAGES OF PORTABLE VERSION:
echo - No installation required
echo - No admin rights needed
echo - Can run from USB drive
echo - Easy to update ^(just replace files^)
echo - Less likely to be blocked by antivirus
echo.
echo SYSTEM REQUIREMENTS:
echo - Windows 10/11 ^(64-bit^)
echo - No Python installation required
echo - Approximately 200 MB disk space
echo.
echo FIRST RUN:
echo If Windows SmartScreen appears, click "More info" then "Run anyway"
echo This is a false positive - the software is safe.
echo.
echo FOR SUPPORT:
echo See User_Manual.txt in the docs folder
echo.
) > "dist\IOTester\README.txt"

rem Create ZIP using PowerShell
echo Compressing files... ^(this may take a minute^)
powershell -Command "Compress-Archive -Path 'dist\IOTester\*' -DestinationPath '%OUTPUT_PATH%' -CompressionLevel Optimal -Force"

if errorlevel 1 (
    echo ERROR: Failed to create ZIP file!
    pause
    exit /b 1
)

rem Get ZIP file size
for %%A in ("%OUTPUT_PATH%") do set "ZIP_SIZE=%%~zA"
set /a ZIP_SIZE_MB=!ZIP_SIZE! / 1048576

echo.
echo ========================================
echo ZIP CREATED SUCCESSFULLY!
echo ========================================
echo.
echo File: %OUTPUT_PATH%
echo Size: ~!ZIP_SIZE_MB! MB
echo.
echo This portable ZIP version:
echo - Does not require installation
echo - Can be extracted anywhere
echo - Is less likely to be blocked by antivirus
echo.
echo DISTRIBUTION:
echo Send this ZIP file to customers instead of the installer
echo if they have issues with antivirus blocking.
echo.
pause
