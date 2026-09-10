@echo off
title EchoSphere Qwen 2.5 3B Live Training Monitor
echo Connecting to EchoSphere Live Training Dashboard...
cd /d "%~dp0"
"..\gemma_training\.venv\Scripts\python.exe" "%~dp0monitor_training.py"
pause
