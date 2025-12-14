@echo off
REM =========================================
REM Switch UDP Settings to Real Hardware
REM =========================================

echo.
echo ==========================================
echo Switching to REAL HARDWARE Mode
echo ==========================================
echo.

set SETTINGS_FILE=src\hw_tester\config\settings.yaml

echo Updating settings.yaml...
echo - Restoring real hardware IP addresses
echo - Setting all send_port to 2880 (real hardware)
echo - You can adjust enabled cards as needed
echo.

REM Backup current settings
copy /Y "%SETTINGS_FILE%" "%SETTINGS_FILE%.backup" >nul
echo [Backup] Created: %SETTINGS_FILE%.backup

REM Use PowerShell to restore hardware IP addresses and ports
powershell -Command "$content = Get-Content '%SETTINGS_FILE%'; $cardId = 0; $content | ForEach-Object { if ($_ -match 'card_id: (\d+)') { $cardId = [int]$Matches[1] }; if ($_ -match 'send_ip:.*#.*Real: \"([\d.]+)\"') { $realIp = $Matches[1]; $_ = \"      send_ip: `\"$realIp`\"      # Real hardware | Localhost: 127.0.0.1\" } elseif ($_ -match 'send_ip:') { $newIp = \"192.168.195.\" + [string](10 + $cardId); $_ = \"      send_ip: `\"$newIp`\"      # Real hardware | Localhost: 127.0.0.1\" } elseif ($_ -match 'receive_ip:.*#.*Real: \"([\d.]+)\"') { $realIp = $Matches[1]; $_ = \"      receive_ip: `\"$realIp`\"   # Real hardware | Localhost: 127.0.0.1\" } elseif ($_ -match 'receive_ip:') { if ($cardId -eq 7) { $newIp = \"192.168.195.70\" } else { $newIp = \"192.168.195.10\" }; $_ = \"      receive_ip: `\"$newIp`\"   # Real hardware | Localhost: 127.0.0.1\" } elseif ($_ -match 'send_port:') { $_ = \"      send_port: 2880            # Real hardware uses same port | Localhost: \" + [string](2879 + $cardId) }; $_ } | Set-Content '%SETTINGS_FILE%'"

echo.
echo [SUCCESS] Switched to REAL HARDWARE mode
echo.
echo Configuration:
echo   - Card 1: 192.168.195.11 -^> 192.168.195.10
echo   - Card 2: 192.168.195.12 -^> 192.168.195.10
echo   - Card 3: 192.168.195.13 -^> 192.168.195.10
echo   - Card 4: 192.168.195.14 -^> 192.168.195.10
echo   - Card 5: 192.168.195.15 -^> 192.168.195.10
echo   - Card 6: 192.168.195.16 -^> 192.168.195.10
echo   - Card 7: 192.168.195.17 -^> 192.168.195.70
echo.
echo IMPORTANT: 
echo   - Verify your network connection to hardware
echo   - Adjust 'enabled' settings per card as needed
echo   - All send_port use 2880 on real hardware
echo.
echo To return to localhost testing, run: switch_to_localhost.bat
echo ==========================================
echo.

pause
