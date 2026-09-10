@echo off
title EchoSphere SOTA Qwen 2.5 3B Training Engine - RTX 4060 GPU
echo ====================================================================
echo Starting EchoSphere SOTA Qwen 2.5 3B Frontier Training on RTX 4060 GPU
echo 200,000 SFT Samples + 30,000 DPO Triplets (36-Layer DoRA)
echo ====================================================================
cd /d "%~dp0"
"..\gemma_training\.venv\Scripts\python.exe" "%~dp0train_qwen_gpu.py"
pause
