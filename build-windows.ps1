# EchoSphere Fast Local Windows App Builder
# Builds native Windows desktop release executable and zips it in ~30 seconds

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$timer = [System.Diagnostics.Stopwatch]::StartNew()

Write-Host ""
Write-Host "  =========================================" -ForegroundColor Cyan
Write-Host "       EchoSphere Windows App Builder      " -ForegroundColor Cyan
Write-Host "  =========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location "$root\frontend"

Write-Host "  [1/2] Building Windows Desktop Release..." -ForegroundColor Yellow
$buildStart = $timer.Elapsed
flutter build windows --release --no-pub
$buildTime = [math]::Round(($timer.Elapsed - $buildStart).TotalSeconds, 1)
Write-Host "  [1/2] Built in ${buildTime}s!" -ForegroundColor Green

$winBuildDir = "$root\frontend\build\windows\x64\runner\Release"
$targetZip = "$root\echosphere-windows.zip"
if (Test-Path $winBuildDir) {
    Write-Host "  [2/2] Packaging release zip..." -ForegroundColor Yellow
    if (Test-Path $targetZip) { Remove-Item $targetZip -Force }
    Compress-Archive -Path "$winBuildDir\*" -DestinationPath $targetZip -Force
    $sizeMB = [math]::Round((Get-Item $targetZip).Length / 1MB, 1)
    Write-Host "  [2/2] Ready: $targetZip ($sizeMB MB)" -ForegroundColor Green
}

$timer.Stop()
$total = [math]::Round($timer.Elapsed.TotalSeconds, 1)

Write-Host ""
Write-Host "  =========================================" -ForegroundColor Green
Write-Host "  Windows App Ready in ${total}s: $targetZip" -ForegroundColor Cyan
Write-Host "  =========================================" -ForegroundColor Green
Write-Host ""
