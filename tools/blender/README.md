# Blender sprite pipeline

Pre-rendered sprites for Sand Castle Crashers, made by running Blender from the command line.
No add-ons, no extra installs: the scripts only use what ships inside Blender (tested with 5.3).

| File | What it does |
|---|---|
| `render_sprites.py` | Renders any `.blend` to a sprite sheet PNG + JSON. Sets the camera to match the game's `iso()` projection, transparent background, one fixed lighting rig. Also used as a library by the crumble test. |
| `crumble_castle.py` | The crumble test. Builds a sandcastle on the game's 4 x 4 footprint, splits it into chunks, collapses it with rigid-body physics. To read as sand, a chunk rounds off and shrinks away once it moves, while a heap of loose sand rises underneath. Outputs a 20-frame animation and 3 stills (intact, cracked, half). |
| `render_sprites.ps1` | Windows wrapper: one command runs the crumble test. |

## Run it (Windows, PowerShell, from the repo folder)

```powershell
.\tools\blender\render_sprites.ps1 -Quick     # draft, well under a minute
.\tools\blender\render_sprites.ps1            # full quality
```

Output lands in `tools\blender\out\` (ignored by git):
`castle_crumble.png/.json`, `castle_states.png/.json`, and `frames\`.

Useful switches: `-Seed 11` (a different collapse), `-Frames 24`, `-Scale 1` (half-size sheet),
`-Only states`, `-SaveBlend` (writes `out\crumble.blend` to open in Blender), `-Gpu`.

Look knobs (pass to `crumble_castle.py` after `--`): `--melt-frames` (how fast a moving chunk turns
to sand), `--clumps` (damp lumps left on the heap), `--mound-height`, `--mound-radius`, `--push`,
`--friction`, `--step` (physics frames per rendered frame).

## Render your own model

Model with 1 tile side = 1 Blender unit, the piece's back corner at the world origin, built toward
+X (col) and -Y (row). One game `z` unit is 0.8165 units of height. Then:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b my_piece.blend --python-exit-code 1 -P tools\blender\render_sprites.py -- --name my_piece --frames 1 1 --frame-w 96 --frame-h 96 --anchor-x 48 --anchor-y 40
```

`--frame-w/h` and `--anchor-x/y` are in game pixels at zoom 1; the anchor is where the world origin
(the game's `iso(col,row,0)`) lands inside the frame.

## How the camera matches the game

The game draws with `x = (col-row)*28`, `y = (col+row)*14 - z*28` at zoom 1 (tile 56 x 28, 2:1).
That is an orthographic camera rotated X 60, Z 45 degrees (looking down 30 degrees - not true
isometric), with 39.6 px per Blender unit. Checked: the intact castle's outline lands within 2 px
of where `iso()` puts the footprint corners (the 1-2 px is the rounded edges).

## JSON

`scale` = sheet px per game px at zoom 1. `anchor` = px inside each frame that sits on
`iso(col,row,0)`. `frames` = `{name, x, y, w, h}` rects in the sheet. To draw a frame at zoom `Z`:
scale by `Z / scale` and put the anchor on `iso(col,row,0)`.
