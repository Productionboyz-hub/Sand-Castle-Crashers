# render_sprites.ps1 - one command: render the sandcastle (crumble + melt) and the three walls as sprite sheets.
#
#   .\tools\blender\render_sprites.ps1                 # full quality (20 crumble frames + 10 melt stages + walls)
#   .\tools\blender\render_sprites.ps1 -Only melt      # just the castle melt stages
#   .\tools\blender\render_sprites.ps1 -Only walls     # just the three walls and their melt
#   .\tools\blender\render_sprites.ps1 -Only sections  # just the castle crumbling a quarter at a time (the game's castle)
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
    [ValidateSet("all", "crumble", "melt", "walls", "sections")][string]$Only = "all",
    [int]$MeltStages = 10,     # castle melt stages, from whole castle to low mound
    [int]$WallStages = 8,      # melt stages per wall, from whole wall to low mound
    [int]$SectionFrames = 10,  # frames in each quarter's crumble (sections run)
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
    $extra = @()
    if ($Gpu)       { $extra += @("--device", "GPU") }
    if ($SaveBlend) { $extra += "--save-blend" }
    $outDir = Join-Path $PSScriptRoot $Out
    $dest = Join-Path $PSScriptRoot "..\..\assets\sprites"
    Write-Host "Blender: $Blender"
    if (($Only -eq "all") -or ($Only -eq "sections")) {
        # the castle the game draws: it crumbles a quarter at a time. Rendered at 3/4 of -Scale, saved as WebP (small)
        $secScale = $Scale * 0.75
        $blArgs = @("-b", "--python-exit-code", "1", "-P", "crumble_castle.py", "--",
            "--out", $Out, "--scale", $secScale, "--samples", $Samples, "--seed", $Seed, "--only", "sections",
            "--section-frames", $SectionFrames, "--cols", 7, "--webp", 82) + $extra
        & $Blender @blArgs
        if ($LASTEXITCODE -ne 0) { throw "Blender exited with code $LASTEXITCODE" }
        $sections = Join-Path $outDir "castle_sections.webp"
        if (Test-Path $sections) {
            if ($Scale -ne 2 -or $SectionFrames -ne 10 -or $Seed -ne 7) {
                Write-Host "Crumbling castle not copied into the game: it expects -Scale 2, -SectionFrames 10 and -Seed 7 (see CRUMBLE_ constants in sandcastle_iso2.html)."
            } else {
                New-Item -ItemType Directory -Force -Path $dest | Out-Null
                Copy-Item $sections (Join-Path $dest "castle_sections.webp") -Force
                Write-Host "Copied castle_sections.webp into assets\sprites for the game."
            }
        }
    }
    if (($Only -ne "walls") -and ($Only -ne "sections")) {
        $castleOnly = $Only
        $blArgs = @("-b", "--python-exit-code", "1", "-P", "crumble_castle.py", "--",
            "--out", $Out, "--scale", $Scale, "--frames", $Frames, "--samples", $Samples,
            "--seed", $Seed, "--only", $castleOnly, "--melt-stages", $MeltStages) + $extra
        & $Blender @blArgs
        if ($LASTEXITCODE -ne 0) { throw "Blender exited with code $LASTEXITCODE" }
        # the game loads the melt run from assets\sprites\castle_melt.png - put the fresh sheet there
        $melt = Join-Path $outDir "castle_melt.png"
        if (($Only -ne "crumble") -and (Test-Path $melt)) {
            if ($Scale -ne 2 -or $MeltStages -ne 10 -or $Seed -ne 7) {
                Write-Host "Castle not copied into the game: it expects -Scale 2, -MeltStages 10 and -Seed 7 (see MELT_ constants in sandcastle_iso2.html)."
            } else {
                New-Item -ItemType Directory -Force -Path $dest | Out-Null
                Copy-Item $melt (Join-Path $dest "castle_melt.png") -Force
                Write-Host "Copied castle_melt.png into assets\sprites for the game."
            }
        }
    }
    if (($Only -eq "all") -or ($Only -eq "walls")) {
        $blArgs = @("-b", "--python-exit-code", "1", "-P", "melt_walls.py", "--",
            "--out", $Out, "--scale", $Scale, "--samples", $Samples,
            "--seed", $Seed, "--melt-stages", $WallStages) + $extra
        & $Blender @blArgs
        if ($LASTEXITCODE -ne 0) { throw "Blender exited with code $LASTEXITCODE" }
        # the game loads the walls from assets\sprites\walls_melt.png
        $walls = Join-Path $outDir "walls_melt.png"
        if (Test-Path $walls) {
            if ($Scale -ne 2 -or $WallStages -ne 8 -or $Seed -ne 7) {
                Write-Host "Walls not copied into the game: it expects -Scale 2, -WallStages 8 and -Seed 7 (see WALLS_ constants in sandcastle_iso2.html)."
            } else {
                New-Item -ItemType Directory -Force -Path $dest | Out-Null
                Copy-Item $walls (Join-Path $dest "walls_melt.png") -Force
                Write-Host "Copied walls_melt.png into assets\sprites for the game."
            }
        }
    }
    Write-Host ""
    Write-Host "Done. Sprite sheets are in: $outDir"
}
finally {
    Pop-Location
}
