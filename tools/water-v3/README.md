# Water v3 — patch scripts and tests

These scripts produced the water v3 change in `sandcastle_iso2.html` on branch
`feature/water-v3`. They are kept here so this repo does not depend on the
soccer-app repo, where the prototype was first built (handoff commit e9868e9).

## Files

| File | What it does |
|---|---|
| `patch_water2.py` | Water texture (see-through shallows, swell, caustics, glints), sideways swash, wet sand, foam edge. Big waves in the defend phase only; damage follows the locked enemy chain. |
| `patch_water3.py` | Applied on top of patch 2. Surge stops at the moat/castle, moats and castle ring pour in and dry up, walls and castle melt with health, more slosh. |
| `patch_water4.py` | Applied on top of patch 3. Phone fix (water was blocky: pattern scale floored, finer texture on small screens) and removal of the per-tile shore tint that showed the tile grid through the clear shallows. |
| `patch_water5.py` | Applied on top of patch 4. No "BIG WAVE!" banner; waves enter from one side, cross to the other and fan out; random wave speeds; backwash from a retreating wave slows an incoming one. Each wave runs on its own clock (`w.p`). |
| `test_surge3.cjs` | 15 Playwright gameplay checks (moat/wall/castle damage, barrier, pour, dry, melt, build-phase safety). |
| `probe_block.cjs` | Fails if phone water is much blockier than desktop. |
| `probe_grid.cjs` | Fails if the tile grid shows through the shallows. |
| `probe_waves.cjs` | Wave behaviour: no banner, big wave crosses the castle side to side, swash fans out, speeds vary, backwash slows an incoming wave. |

## Rebuild check (any machine with Python 3)

```
git show main:sandcastle_iso2.html > main.html
python3 patch_water2.py main.html v2.html
python3 patch_water3.py v2.html v3.html
python3 patch_water4.py v3.html v4.html
python3 patch_water5.py v4.html v5.html
```

`v5.html` is identical to `sandcastle_iso2.html` on the branch, byte for byte.
(Use bash for the `git show ... >` step: PowerShell's `>` re-encodes the bytes.)

## Running the tests (needs Node + Playwright)

Serve a folder containing the build as `index.html`, then:

```
node test_surge3.cjs http://127.0.0.1:PORT/
node probe_block.cjs http://127.0.0.1:PORT/
node probe_grid.cjs  http://127.0.0.1:PORT/
node probe_waves.cjs http://127.0.0.1:PORT/
```

Each exits 0 on pass and 1 on fail. `test_surge3.cjs` fails on main (no wave
system there); the block and grid probes failed on the pre-fix v3 build;
`probe_waves.cjs` failed 5 of 7 checks on the build before patch 5.
