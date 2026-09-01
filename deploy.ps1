# EchoSphere Instant Deployer - Build, Deploy and Push in 1 Click
param(
    [switch]$SkipBuild,
    [switch]$SkipPush,
    [string]$Message = "deploy: update web build"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$timer = [System.Diagnostics.Stopwatch]::StartNew()

Write-Host ""
Write-Host "  =========================================" -ForegroundColor Cyan
Write-Host "       EchoSphere Instant Deployer" -ForegroundColor Cyan
Write-Host "  =========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Build Flutter Web
if (-not $SkipBuild) {
    $buildStart = $timer.Elapsed
    Write-Host "  [1/3] Building Flutter Web..." -ForegroundColor Yellow
    Set-Location "$root\frontend"
    flutter build web --release --no-wasm-dry-run --base-href / 2>&1 | Out-Null
    $buildTime = ($timer.Elapsed - $buildStart).TotalSeconds
    $buildTimeRounded = [math]::Round($buildTime, 1)
    Write-Host "  [1/3] Built in ${buildTimeRounded}s" -ForegroundColor Green
}
else {
    Write-Host "  [1/3] Build skipped (using existing build)" -ForegroundColor DarkGray
}

# Step 2: Deploy to Cloudflare Pages
$deployStart = $timer.Elapsed
Write-Host "  [2/3] Uploading to Cloudflare Pages..." -ForegroundColor Yellow
Set-Location $root
$deployOutput = npx wrangler pages deploy frontend/build/web --project-name=echosphere --branch=main --commit-dirty=true 2>&1
$deployTime = ($timer.Elapsed - $deployStart).TotalSeconds
$deployTimeRounded = [math]::Round($deployTime, 1)

$urlMatch = $deployOutput | Select-String -Pattern "https://.*\.pages\.dev" | Select-Object -First 1
if ($urlMatch) {
    $url = $urlMatch.Matches.Value
}
else {
    $url = "https://echosphere-2jf.pages.dev"
}
Write-Host "  [2/3] Deployed in ${deployTimeRounded}s" -ForegroundColor Green

# Step 3: Commit and Push to GitHub
if (-not $SkipPush) {
    $pushStart = $timer.Elapsed
    Write-Host "  [3/3] Pushing build to GitHub..." -ForegroundColor Yellow
    Set-Location $root
    cmd /c "git add frontend/build/web -f 2>&1" | Out-Null
    cmd /c "git add deploy.ps1 2>&1" | Out-Null
    cmd /c "git diff --cached --quiet 2>&1"
    $hasChanges = ($LASTEXITCODE -ne 0)
    if ($hasChanges) {
        cmd /c "git commit -m `"$Message`" 2>&1" | Out-Null
        cmd /c "git push origin main 2>&1" | Out-Null
        $pushTime = ($timer.Elapsed - $pushStart).TotalSeconds
        $pushTimeRounded = [math]::Round($pushTime, 1)
        Write-Host "  [3/3] Pushed in ${pushTimeRounded}s" -ForegroundColor Green
    }
    else {
        Write-Host "  [3/3] Already up to date" -ForegroundColor Green
    }
}
else {
    Write-Host "  [3/3] Git push skipped" -ForegroundColor DarkGray
}

# Done
$timer.Stop()
$total = [math]::Round($timer.Elapsed.TotalSeconds, 1)

Write-Host ""
Write-Host "  =========================================" -ForegroundColor Green
Write-Host "  LIVE in ${total}s" -ForegroundColor Green
Write-Host "  $url" -ForegroundColor Cyan
Write-Host "  =========================================" -ForegroundColor Green
Write-Host ""
