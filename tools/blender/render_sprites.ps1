# render_sprites.ps1 - one command: build the sandcastle crumble test and render its sprite sheets.
#
#   .\tools\blender\render_sprites.ps1                 # full quality (about 20 frames + 3 stills)
#   .\tools\blender\render_sprites.ps1 -Quick          # fast draft to check it runs
#   .\tools\blender\render_sprites.ps1 -Seed 11        # a different collapse
#
# Output goes to tools\blender\out\ (ignored by git). Your shell always ends up back where it started.
param(
    [string]$Blender = "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe",
    [string]$Out     = "out",
    [double]$Scale   = 2,       # sheet px per game px at zoom 1 (2 = tile 112 px wide)
    [int]$Frames     = 20,      # frames in the crumble animation
    [int]$Samples    = 48,      # render quality
    [int]$Seed       = 7,
    [ValidateSet("all", "crumble", "states")][string]$Only = "all",
    [switch]$Gpu,               # render on the graphics card if Cycles is set up for it
    [switch]$SaveBlend,         # also save out\crumble.blend to open in Blender
    [switch]$Quick              # draft: half size, few samples
)
$ErrorActionPreference = "Stop"

if (-not (Test-Path $Blender)) {
    $found = Get-ChildItem "C:\Program Files\Blender Foundation" -Recurse -Filter blender.exe -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $found) { throw "blender.exe not found. Pass it with -Blender 'C:\path\to\blender.exe'" }
    $Blender = $found.FullName
}
if ($Quick) { $Scale = 1; $Samples = 8 }

Push-Location $PSScriptRoot
try {
    $blArgs = @("-b", "--python-exit-code", "1", "-P", "crumble_castle.py", "--",
        "--out", $Out, "--scale", $Scale, "--frames", $Frames, "--samples", $Samples,
        "--seed", $Seed, "--only", $Only)
    if ($Gpu)       { $blArgs += @("--device", "GPU") }
    if ($SaveBlend) { $blArgs += "--save-blend" }
    Write-Host "Blender: $Blender"
    & $Blender @blArgs
    if ($LASTEXITCODE -ne 0) { throw "Blender exited with code $LASTEXITCODE" }
    Write-Host ""
    Write-Host "Done. Sprite sheets are in: $(Join-Path $PSScriptRoot $Out)"
}
finally {
    Pop-Location
}
