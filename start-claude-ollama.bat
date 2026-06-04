@echo off
:: NEUROTWIN OS - Claude Code via Ollama (GTX 1650 GPU, no cloud)
:: Model: qwen2.5-coder:3b stored at D:\OllamaModels
:: NOTE: Works best when Docker stack is paused (more VRAM headroom)
:: First time: run D:\pull_model.ps1 to download the model

title Claude Code [Ollama - LOCAL GPU]
cd /d D:\neurotwin

set OLLAMA_MODELS=D:\OllamaModels
set ANTHROPIC_AUTH_TOKEN=ollama
set ANTHROPIC_BASE_URL=http://localhost:11434
set CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

echo.
echo ========================================
echo  NEUROTWIN OS - Claude Code
echo  Mode: Ollama Local GPU (qwen2.5-coder:3b)
echo  VRAM: GTX 1650 4GB
echo  Models: D:\OllamaModels
echo  Project: D:\neurotwin
echo ========================================
echo.

:: Ensure Ollama is running
start "" "C:\Users\Abdul Razaq\AppData\Local\Programs\Ollama\ollama app.exe"
timeout /t 3 /nobreak >nul

claude --model qwen2.5-coder:3b
