# ────────────────────────────────────────────────
#  Sand Castle Crashers — Build + Deploy + Receipt
#  Usage: .\deploy_scc.ps1
#  Commit and push BEFORE running this.
# ────────────────────────────────────────────────

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

# GUARD 1 — right repo
$remote = git remote get-url origin
if ($remote -notmatch 'Sand-Castle-Crashers') {
    Write-Host "ABORT: wrong repo -> $remote" -ForegroundColor Red
    exit 1
}

# GUARD 2 — clean tree (a SHA from a dirty tree is a lie)
$dirty = git status --porcelain --untracked-files=no
if ($dirty) {
    Write-Host "ABORT: uncommitted changes. Commit first." -ForegroundColor Red
    $dirty
    exit 1
}

# GUARD 3 — pushed
git fetch origin --quiet
if ((git rev-parse HEAD) -ne (git rev-parse '@{u}')) {
    Write-Host "ABORT: HEAD not pushed to origin." -ForegroundColor Red
    exit 1
}

$sha = git rev-parse --short HEAD
Write-Host "Building $sha ..." -ForegroundColor Cyan

# BUILD — stamp during copy; source keeps the placeholder
$src = Get-Content "$root\sandcastle_iso2.html" -Raw
if ($src -notmatch '__BUILD_SHA__') {
    Write-Host "ABORT: no __BUILD_SHA__ placeholder in source." -ForegroundColor Red
    exit 1
}
$out  = $src -replace '__BUILD_SHA__', $sha
$hits = ([regex]::Matches($out, "build $sha")).Count
if ($hits -ne 2) {
    Write-Host "ABORT: expected 2 injection points, found $hits." -ForegroundColor Red
    exit 1
}
$out = $out -replace "`r`n", "`n"
[System.IO.File]::WriteAllText("$root\public\index.html", $out)

# DEPLOY
Write-Host "Deploying..." -ForegroundColor Cyan
cmd /c "cd /d `"$root`" && wrangler deploy"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ABORT: wrangler failed ($LASTEXITCODE)." -ForegroundColor Red
    exit 1
}

# RECEIPT — read the served artifact back
Write-Host "Verifying served body..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
$cb    = [DateTimeOffset]::Now.ToUnixTimeSeconds()
$url   = "https://sand-castle-crashers.athleticsouthla.workers.dev/?cb=$cb"
$r     = Invoke-WebRequest $url -Headers @{"Cache-Control"="no-cache"} -UseBasicParsing
$cache = $r.Headers['cf-cache-status']
$found = [regex]::Matches($r.Content, 'build ([a-f0-9]{7})') | ForEach-Object { $_.Groups[1].Value }

Write-Host ""
Write-Host "  expected : $sha"
Write-Host "  found    : $($found -join ', ')"
Write-Host "  cache    : $cache"
Write-Host ""

if ($found.Count -eq 2 -and ($found | Where-Object { $_ -ne $sha }).Count -eq 0) {
    Write-Host "RECEIPT VERIFIED — $sha is live. Device pass next." -ForegroundColor Green
    Copy-Item "$root\sandcastle_iso2.html" "G:\My Drive\Sand Castle Crashers Sync\sandcastle_iso2.html" -Force
    Copy-Item "$root\CLAUDE.md"            "G:\My Drive\Sand Castle Crashers Sync\CLAUDE.md"            -Force
} else {
    Write-Host "RECEIPT FAILED — do NOT device pass." -ForegroundColor Red
    if ($cache -eq 'HIT') { Write-Host "cache HIT: wait 30s, re-run receipt only." -ForegroundColor Yellow }
    else                  { Write-Host "cache MISS + wrong SHA: origin problem. STOP." -ForegroundColor Yellow }
    exit 1
}
