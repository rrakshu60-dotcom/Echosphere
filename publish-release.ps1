# EchoSphere GitHub Release Publisher - Local Build & Direct Upload
# Builds Android APK and/or Windows ZIP locally and uploads directly to GitHub Releases
param(
    [string]$Tag = "latest",
    [string]$Title = "EchoSphere Latest Release",
    [switch]$SkipAndroid,
    [switch]$SkipWindows
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$timer = [System.Diagnostics.Stopwatch]::StartNew()

# Locate gh CLI
$gh = Get-Command gh -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $gh) {
    $gh = "C:\Users\Rakshitha\.gemini\antigravity-ide\brain\bf47dc5b-f9f2-44b6-a719-497467150d92\scratch\bin\gh.exe"
}

if (-not (Test-Path $gh)) {
    Write-Host "  [!] GitHub CLI (gh) not found." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "  =========================================" -ForegroundColor Cyan
Write-Host "      EchoSphere GitHub Release Publisher  " -ForegroundColor Cyan
Write-Host "  =========================================" -ForegroundColor Cyan
Write-Host ""

$filesToUpload = @()

Set-Location "$root\frontend"
Write-Host "  [0/3] Syncing Flutter dependencies..." -ForegroundColor Yellow
flutter pub get

# 1. Build Android APK
if (-not $SkipAndroid) {
    Write-Host "  [1/3] Building Android Release APK (Arm64)..." -ForegroundColor Yellow
    Set-Location "$root\frontend"
    flutter build apk --release --target-platform android-arm64 --android-skip-build-dependency-validation

    
    $apkPath = "$root\frontend\build\app\outputs\flutter-apk\app-release.apk"
    $targetApk = "$root\echosphere-app.apk"
    if (Test-Path $apkPath) {
        Copy-Item $apkPath $targetApk -Force
        $sizeMB = [math]::Round((Get-Item $targetApk).Length / 1MB, 1)
        Write-Host "  [1/3] Built Android APK ($sizeMB MB)" -ForegroundColor Green
        $filesToUpload += $targetApk
    }
}

# 2. Build Windows App
if (-not $SkipWindows) {
    Write-Host "  [2/3] Building Windows Desktop Release..." -ForegroundColor Yellow
    Set-Location "$root\frontend"
    flutter build windows --release
    
    $winBuildDir = "$root\frontend\build\windows\x64\runner\Release"
    $targetZip = "$root\echosphere-windows.zip"
    if (Test-Path $winBuildDir) {
        if (Test-Path $targetZip) { Remove-Item $targetZip -Force }
        Compress-Archive -Path "$winBuildDir\*" -DestinationPath $targetZip -Force
        $sizeMB = [math]::Round((Get-Item $targetZip).Length / 1MB, 1)
        Write-Host "  [2/3] Built Windows App Zip ($sizeMB MB)" -ForegroundColor Green
        $filesToUpload += $targetZip
    }
}

# 3. Publish to GitHub Releases via gh CLI
if ($filesToUpload.Count -gt 0) {
    Write-Host "  [3/3] Uploading binaries directly to GitHub Release '$Tag'..." -ForegroundColor Yellow
    Set-Location $root

    # Ensure release exists
    & $gh release view $Tag 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Creating release '$Tag'..." -ForegroundColor DarkGray
        & $gh release create $Tag --title "$Title" --notes "Direct local build upload"
    }

    # Upload files using --clobber to overwrite old assets
    & $gh release upload $Tag $filesToUpload --clobber
    Write-Host "  [3/3] Successfully published all assets to GitHub Releases!" -ForegroundColor Green
} else {
    Write-Host "  [!] No files built to upload." -ForegroundColor Yellow
}

$timer.Stop()
$total = [math]::Round($timer.Elapsed.TotalSeconds, 1)

Write-Host ""
Write-Host "  =========================================" -ForegroundColor Green
Write-Host "  ✅ Published to GitHub Releases in ${total}s!" -ForegroundColor Green
Write-Host "  https://github.com/rrakshu60-dotcom/Echosphere/releases/tag/$Tag" -ForegroundColor Cyan
Write-Host "  =========================================" -ForegroundColor Green
Write-Host ""
