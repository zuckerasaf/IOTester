@echo off
rem Build standalone EXE for the IO Tester app using PyInstaller.
rem This script bundles source, configuration, styles, and web resources.

setlocal enabledelayedexpansion

rem Name of the generated executable
set EXE_NAME=IOTester

rem Main Python entrypoint
set MAIN_SCRIPT=src\hw_tester\app.py

rem Output directories
set DIST_DIR=dist
set BUILD_DIR=build

rem Optional icon file (uncomment and set if you have one)
rem set ICON=--icon=path\to\icon.ico

rem Choose distribution type: onedir is less likely to be flagged by antivirus.
rem To force onefile, run: set DIST_MODE=onefile && .\build_exe.bat
if "%DIST_MODE%"=="" set DIST_MODE=onedir

echo Building %DIST_MODE% distribution for %EXE_NAME%

set DIST_ARGS=--noupx --windowed --name %EXE_NAME%
if /i "%DIST_MODE%"=="onefile" (
    set DIST_ARGS=%DIST_ARGS% --onefile
    set "BUILD_OUTPUT_DIR=%DIST_DIR%"
) else (
    set DIST_ARGS=%DIST_ARGS% --onedir
    set "BUILD_OUTPUT_DIR=%DIST_DIR%\%EXE_NAME%"
)

rem Preserve existing dist config folder during rebuild
set "CONFIG_DIR=%BUILD_OUTPUT_DIR%\config"
set "TEMP_CONFIG_BACKUP=%TEMP%\%EXE_NAME%_config_backup"
if exist "%TEMP_CONFIG_BACKUP%" rd /s /q "%TEMP_CONFIG_BACKUP%"
if exist "%CONFIG_DIR%" (
    echo Backing up existing config folder: %CONFIG_DIR%
    xcopy /e /i /y "%CONFIG_DIR%" "%TEMP_CONFIG_BACKUP%" >nul
)

rem Use the virtual environment Python if available, otherwise fallback to system PyInstaller
if exist ".venv\Scripts\python.exe" (
    set "PYINSTALLER_CMD=.venv\Scripts\python.exe"
    set "PYINSTALLER_ARGS=-m PyInstaller"
) else (
    set "PYINSTALLER_CMD=pyinstaller"
    set "PYINSTALLER_ARGS="
)

%PYINSTALLER_CMD% %PYINSTALLER_ARGS% --noconfirm --clean %DIST_ARGS% %ICON% ^
    --add-data "src/hw_tester/config;config" ^
    --hidden-import=PySide6 ^
    --hidden-import=PySide6.QtCore ^
    --hidden-import=PySide6.QtGui ^
    --hidden-import=PySide6.QtWidgets ^
    --hidden-import=yaml ^
    %MAIN_SCRIPT%

if errorlevel 1 (
    echo.
    echo Build failed.
    pause
    if exist "%TEMP_CONFIG_BACKUP%" (
        echo Restoring config folder from backup...
        if exist "%CONFIG_DIR%" rd /s /q "%CONFIG_DIR%"
        xcopy /e /i /y "%TEMP_CONFIG_BACKUP%" "%CONFIG_DIR%" >nul
        rd /s /q "%TEMP_CONFIG_BACKUP%"
    )
    exit /b 1
)

if exist "%TEMP_CONFIG_BACKUP%" (
    echo Restoring config folder to dist output...
    if exist "%CONFIG_DIR%" rd /s /q "%CONFIG_DIR%"
    xcopy /e /i /y "%TEMP_CONFIG_BACKUP%" "%CONFIG_DIR%" >nul
    rd /s /q "%TEMP_CONFIG_BACKUP%"
)

rem Copy required config assets into external config folder
if not exist "%CONFIG_DIR%" (
    echo Creating config folder: %CONFIG_DIR%
    mkdir "%CONFIG_DIR%"
)
set "SOURCE_CONFIG_DIR=src\hw_tester\config"
for %%F in (board_pin_config.json pin_map.json settings.yaml Comm_settings.yaml connector_Address_A_map.xlsx connector_Address_B_map.xlsx) do (
    if exist "%SOURCE_CONFIG_DIR%\%%F" (
        if exist "%CONFIG_DIR%\%%F" del /f /q "%CONFIG_DIR%\%%F"
        echo Copying %%F to external config folder...
        copy /y "%SOURCE_CONFIG_DIR%\%%F" "%CONFIG_DIR%\%%F"
    ) else (
        echo Source file missing, skipping: %%F
    )
)
if exist "src\hw_tester\ui\Styles\dark.css" (
    if exist "%CONFIG_DIR%\dark.css" del /f /q "%CONFIG_DIR%\dark.css"
    echo Copying dark.css to external config folder...
    copy /y "src\hw_tester\ui\Styles\dark.css" "%CONFIG_DIR%\dark.css"
) else (
    echo Source stylesheet missing, skipping dark.css
)

echo.
echo Build complete. Executable is here:
echo %DIST_DIR%\%EXE_NAME%.exe
pause
endlocal
