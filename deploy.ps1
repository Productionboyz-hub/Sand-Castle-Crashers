# ─────────────────────────────────────────────
#  Athletic South LA — Deploy Script
#  Run from VSCode terminal: .\deploy.ps1
# ─────────────────────────────────────────────

$version  = "v186"   # <-- CHANGE THIS EACH VERSION
$destName = "index_$version.html"
$source   = "$PSScriptRoot\index.html"
$dest     = "G:\My Drive\SOCCER APP\$destName"

# ── Copy to Google Drive ────────────────────
Write-Host "Copying to Google Drive..." -ForegroundColor Cyan
Copy-Item $source $dest -Force
Write-Host "Done: $destName is in SOCCER APP folder" -ForegroundColor Green
Write-Host "Tell Claude: '$destName is in Drive'" -ForegroundColor Yellow
