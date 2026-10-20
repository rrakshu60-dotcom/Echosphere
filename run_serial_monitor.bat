@echo off
title EchoSphere - ESP32 Hardware & Latency Monitor
color 0A
echo ===========================================================================
echo   EchoSphere Live ESP32 Hardware & Website Latency Monitor
echo   Port: COM5 (115200 baud) ^| Cloud API: Render
echo ===========================================================================
echo.
cd /d "%~dp0"
python -u backend\scripts\live_esp32_monitor.py
echo.
echo Monitor stopped.
pause
