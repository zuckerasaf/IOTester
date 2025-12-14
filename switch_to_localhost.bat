@echo off
REM =========================================
REM Switch UDP Settings to Localhost Testing
REM =========================================

echo.
echo ==========================================
echo Switching to LOCALHOST Testing Mode
echo ==========================================
echo.

set SETTINGS_FILE=src\hw_tester\config\settings.yaml

echo Updating settings.yaml...
echo - All IPs will be set to 127.0.0.1
echo - Send ports will be unique (2880-2886) for localhost
echo - All cards will be ENABLED
echo.

REM Backup current settings
copy /Y "%SETTINGS_FILE%" "%SETTINGS_FILE%.backup" >nul
echo [Backup] Created: %SETTINGS_FILE%.backup

REM Use PowerShell to replace IP addresses, ports, and enable cards
powershell -Command "$content = Get-Content '%SETTINGS_FILE%'; $cardId = 0; $content | ForEach-Object { if ($_ -match 'card_id: (\d+)') { $cardId = [int]$Matches[1] }; if ($_ -match 'send_ip:') { $_ = \"      send_ip: `\"127.0.0.1`\"      # Localhost for testing | Real: `\"192.168.195.\" + [string](10 + $cardId) + \"`\"\" } elseif ($_ -match 'receive_ip:') { if ($cardId -eq 7) { $realIp = \"192.168.195.70\" } else { $realIp = \"192.168.195.10\" }; $_ = \"      receive_ip: `\"127.0.0.1`\"   # Localhost for testing | Real: `\"$realIp`\"\" } elseif ($_ -match 'send_port:') { $port = 2879 + $cardId; if ($cardId -eq 1) { $_ = \"      send_port: 2880\" } else { $_ = \"      send_port: $port            # Localhost needs unique port | Real: 2880\" } } elseif ($_ -match 'enabled: false') { $_ = \"      enabled: true\" }; $_ } | Set-Content '%SETTINGS_FILE%'"

echo.
echo [SUCCESS] Switched to LOCALHOST mode
echo.
echo Configuration:
echo   - All send_ip: 127.0.0.1
echo   - All receive_ip: 127.0.0.1
echo   - All cards: ENABLED
echo.
echo Ready for localhost testing!
echo.
echo Next steps:
echo   1. Start simulator: python src\hw_tester\core\localhost_simulator.py
echo   2. Run your tests: python src\hw_tester\core\udp_sender.py
echo.
echo To restore real hardware settings, run: switch_to_hardware.bat
echo ==========================================
echo.

pause
