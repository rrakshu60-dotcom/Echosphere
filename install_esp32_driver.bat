@echo off
title EchoSphere - ESP32 CP210x Driver Installer
echo ========================================================
echo   EchoSphere ESP32 Hardware USB Driver Setup
echo ========================================================
echo.

:: Check for administrative rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Administrator rights required to register driver with Windows.
    echo [INFO] Requesting elevation...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo [OK] Running with Administrator privileges.
echo [INFO] Installing Silicon Labs CP210x Driver for ESP32...
pnputil /add-driver "%~dp0drivers\CP210x\silabser.inf" /install

echo.
echo ========================================================
echo   Driver Installation Complete!
echo   Checking for COM ports...
echo ========================================================
powershell -Command "[System.IO.Ports.SerialPort]::getportnames()"
echo.
echo If your ESP32 is connected, it should now appear (e.g. COM7).
echo.
pause
