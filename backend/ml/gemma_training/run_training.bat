@echo off
title EchoSphere Local Gemma Training - RTX 4060 GPU
echo =========================================================
echo Starting EchoSphere Local Gemma Training on RTX 4060 GPU
echo =========================================================
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" "%~dp0train_local_gpu.py"
pause
