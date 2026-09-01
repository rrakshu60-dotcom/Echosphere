# Instant 1-Click EchoSphere Web Deployer
Set-Location "$PSScriptRoot\frontend"
Write-Host "⚡ Building Flutter Web App..." -ForegroundColor Cyan
flutter build web --release --no-wasm-dry-run --base-href /

Set-Location "$PSScriptRoot"
Write-Host "🚀 Uploading directly to Cloudflare Pages..." -ForegroundColor Green
npx wrangler pages deploy frontend/build/web --project-name=echosphere --branch=main --commit-dirty=true
Write-Host "✅ Live on Cloudflare!" -ForegroundColor Green
