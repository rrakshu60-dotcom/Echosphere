# EchoSphere Fast Local APK Builder
# Builds compact release APK (~15-20 MB) for modern Android phones in ~30 seconds
param(
    [switch]$InstallToDevice
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$timer = [System.Diagnostics.Stopwatch]::StartNew()

Write-Host ""
Write-Host "  =========================================" -ForegroundColor Cyan
Write-Host "       EchoSphere Fast Android Builder     " -ForegroundColor Cyan
Write-Host "  =========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location "$root\frontend"

Write-Host "  [1/2] Building Android Release APK (Arm64)..." -ForegroundColor Yellow
$buildStart = $timer.Elapsed
flutter build apk --release --target-platform android-arm64 --no-pub --android-skip-build-dependency-validation
$buildTime = [math]::Round(($timer.Elapsed - $buildStart).TotalSeconds, 1)
Write-Host "  [1/2] Built in ${buildTime}s!" -ForegroundColor Green

$apkPath = "$root\frontend\build\app\outputs\flutter-apk\app-release.apk"
$targetPath = "$root\echosphere-app.apk"
if (Test-Path $apkPath) {
    Copy-Item $apkPath $targetPath -Force
    $sizeMB = [math]::Round((Get-Item $targetPath).Length / 1MB, 1)
    Write-Host "  [2/2] Ready: $targetPath ($sizeMB MB)" -ForegroundColor Green
}

if ($InstallToDevice) {
    Write-Host "  Installing to connected ADB device..." -ForegroundColor Yellow
    adb install -r $targetPath
    Write-Host "  Installed successfully!" -ForegroundColor Green
}

$timer.Stop()
$total = [math]::Round($timer.Elapsed.TotalSeconds, 1)

Write-Host ""
Write-Host "  =========================================" -ForegroundColor Green
Write-Host "  APK Ready in ${total}s: $targetPath" -ForegroundColor Cyan
Write-Host "  =========================================" -ForegroundColor Green
Write-Host ""
