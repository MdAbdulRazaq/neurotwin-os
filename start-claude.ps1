$env:ANTHROPIC_AUTH_TOKEN = "ollama"
$env:ANTHROPIC_BASE_URL = "http://localhost:11434"
$env:ANTHROPIC_API_KEY = ""
$env:CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1"
$env:OLLAMA_MODELS = "D:\OllamaModels"
$env:PATH = "D:\Ollama;D:\npm-global;" + $env:PATH

Write-Host "Starting Ollama if not running..." -ForegroundColor Yellow
$running = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $running) {
    Start-Process "D:\Ollama\ollama.exe" "serve" -WindowStyle Minimized
    Start-Sleep 3
    Write-Host "Ollama started." -ForegroundColor Green
} else {
    Write-Host "Ollama already running." -ForegroundColor Green
}

Set-Location D:\neurotwin
Write-Host "Launching Claude Code -> qwen2.5-coder:7b" -ForegroundColor Cyan
& "D:\npm-global\claude.ps1" --model qwen2.5-coder:7b
