# EchoSphere Real-time GPU Training Monitor
# Streams the active GPU training progress and live ASCII validation curve directly to terminal.

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "EchoSphere AI Training Live Stream"

$logFile = Get-ChildItem -Path "$env:USERPROFILE\.gemini\antigravity-ide\brain\*\.system_generated\tasks\task-*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($logFile) {
    $logPath = $logFile.FullName
} else {
    Write-Error "No active task log found."
    exit 1
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  STREAMING ECHOSPHERE GPU TRAINING PROGRESS TO TERMINAL" -ForegroundColor Cyan
Write-Host "  Log: $logPath" -ForegroundColor DarkGray
Write-Host "  Press Ctrl+C to exit monitor (training continues in background)" -ForegroundColor DarkGray
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

Get-Content -Path $logPath -Wait -Tail 35 -Encoding utf8
