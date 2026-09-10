# EchoSphere Real-time GPU Training Monitor (PowerShell Stream)
# Directly tails the active GPU training engine log in real time

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "EchoSphere Qwen 2.5 3B Live Training Stream"

$logFile = Get-ChildItem -Path "$env:USERPROFILE\.gemini\antigravity-ide\brain\*\.system_generated\tasks\task-*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $logFile) {
    $fallbackLog = "C:\echosphere v2.2\backend\ml\qwen_training\output_qwen_model\training.log"
    if (Test-Path $fallbackLog) {
        $logPath = $fallbackLog
    } else {
        Write-Error "No active training log found. Please start training first."
        exit 1
    }
} else {
    $logPath = $logFile.FullName
}

Clear-Host
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  ECHOSPHERE AI :: REAL-TIME GPU TRAINING LOG STREAM" -ForegroundColor Cyan
Write-Host "  Target: NVIDIA GeForce RTX 4060 Laptop GPU | Qwen 2.5 3B Instruct" -ForegroundColor DarkGray
Write-Host "  Log:    $logPath" -ForegroundColor DarkGray
Write-Host "  [Press Ctrl+C to exit monitor; training continues running in background]" -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Get-Content -Path $logPath -Wait -Tail 20 -Encoding utf8
