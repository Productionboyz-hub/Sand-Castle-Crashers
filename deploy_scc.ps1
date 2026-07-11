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

# 1. Sync sandcastle_iso2.html -> index.html
Write-Host "Syncing index.html..." -ForegroundColor Cyan
[System.IO.File]::WriteAllBytes(
    "$root\index.html",
    [System.IO.File]::ReadAllBytes("$root\sandcastle_iso2.html")
)

# 2. Copy to Google Drive
Write-Host "Copying to Google Drive..." -ForegroundColor Cyan
Copy-Item "$root\index.html" "G:\My Drive\Sand Castle Crashers\index.html" -Force
Copy-Item "$root\sandcastle_iso2.html" "G:\My Drive\Sand Castle Crashers\sandcastle_iso2.html" -Force

# 3. Sync worker file with game HTML
Write-Host "Updating worker file..." -ForegroundColor Cyan
$html = [System.IO.File]::ReadAllText("$root\sandcastle_iso2.html").Replace('</script>', '<\/script>')
$worker = "export default { fetch: () => new Response(" + '`' + $html + '`' + ", { headers: { 'Content-Type': 'text/html' } }) };"
[System.IO.File]::WriteAllText("$root\sand_castle_worker.js", $worker, [System.Text.UTF8Encoding]::new($false))

# 4. Git commit + push
Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
Set-Location $root
git add -A
git commit -m "${version}: ${desc}"
git push

# 5. Wrangler deploy (needs CMD — launching via cmd.exe)
Write-Host "Deploying to Cloudflare..." -ForegroundColor Cyan
cmd /c "cd /d `"$root`" && wrangler deploy"

Write-Host ""
Write-Host "Done! Live at:" -ForegroundColor Green
Write-Host "  GitHub Pages : https://productionboyz-hub.github.io/Sand-Castle-Crashers" -ForegroundColor Green
Write-Host "  Cloudflare   : https://sand-castle-crashers.athleticsouthla.workers.dev" -ForegroundColor Green
