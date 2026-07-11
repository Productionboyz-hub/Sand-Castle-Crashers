# ─────────────────────────────────────────────
#  Sand Castle Crashers — Deploy Script
#  Usage: .\deploy_scc.ps1 v0.7.0 "what changed"
# ─────────────────────────────────────────────

param(
    [string]$version = "",
    [string]$desc    = "update"
)

if ($version -eq "") {
    $version = Read-Host "Version (e.g. v0.7.0)"
}

$root = $PSScriptRoot

# 1. Copy game file to public/index.html (served as static asset by Worker)
Write-Host "Syncing public/index.html..." -ForegroundColor Cyan
Copy-Item "$root\sandcastle_iso2.html" "$root\public\index.html" -Force

# 2. Git commit + push
Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
Set-Location $root
git add -A
git commit -m "${version}: ${desc}"
git push

# 3. Wrangler deploy
Write-Host "Deploying to Cloudflare..." -ForegroundColor Cyan
cmd /c "cd /d `"$root`" && wrangler deploy"

# 4. Sync to Google Drive
Write-Host "Syncing to Google Drive..." -ForegroundColor Cyan
$syncDir = "G:\My Drive\Sand Castle Crashers Sync"
Copy-Item "$root\sandcastle_iso2.html" "$syncDir\sandcastle_iso2.html" -Force
Copy-Item "$root\CLAUDE.md"            "$syncDir\CLAUDE.md"            -Force
Write-Host "Synced to $syncDir" -ForegroundColor Green

Write-Host ""
Write-Host "Done! Live at:" -ForegroundColor Green
Write-Host "  GitHub Pages : https://productionboyz-hub.github.io/Sand-Castle-Crashers" -ForegroundColor Green
Write-Host "  Cloudflare   : https://sand-castle-crashers.athleticsouthla.workers.dev" -ForegroundColor Green
