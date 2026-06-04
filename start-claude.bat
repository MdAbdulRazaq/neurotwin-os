@echo off
title NEUROTWIN OS - Claude Code (Ollama Local)
echo ========================================
echo  NEUROTWIN OS - Claude Code
echo  Mode: Ollama Local GPU (qwen2.5-coder:7b)
echo  VRAM: GTX 1650 4GB
echo  Models: D:\OllamaModels
echo  Project: D:\neurotwin
echo ========================================
echo.

:: Set all vars inline so no stale session issues
set ANTHROPIC_AUTH_TOKEN=ollama
set ANTHROPIC_BASE_URL=http://localhost:11434
set ANTHROPIC_API_KEY=
set CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
set OLLAMA_MODELS=D:\OllamaModels

:: Ensure D:\Ollama is in PATH
set PATH=D:\Ollama;D:\npm-global;%PATH%

:: Start Ollama service if not running
echo Checking Ollama service...
D:\Ollama\ollama.exe list >nul 2>&1
if errorlevel 1 (
    echo Starting Ollama...
    start /min D:\Ollama\ollama.exe serve
    timeout /t 3 /nobreak >nul
)

:: Launch Claude Code
cd /d D:\neurotwin
echo Launching Claude Code with qwen2.5-coder:7b ...
echo.
D:\npm-global\claude.ps1 --model qwen2.5-coder:7b
