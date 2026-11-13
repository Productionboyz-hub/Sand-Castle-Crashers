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
| `patch_water6.py` | Applied on top of patch 5. Stronger see-saw pitch (`SWASH_PITCH`), wider fan-out (`SWASH_FAN_MIN/MAX`), faster sideways slosh. |
| `patch_water7.py` | Applied on top of patch 6. Waves are POURED along the beach: a wave lands at one spot, its front slides left or right, thinning as it goes, and the sheet behind it stays up then drains. Foam, streaks and flecks in the thin water are carried sideways with the flow. Knobs: `SWASH_SLIDE_MIN/MAX`, `SWASH_REACH_MIN/MAX`, `SWASH_FLOW_VIS`. |
| `patch_water8.py` | Applied on top of patch 7. Wave SIZE matters: small waves part-fill a moat and it dries fast, big waves fill it and it dries slowly; ordinary waves do a little damage (scaled by size, defend phase only, same locked chain). Knobs: `SWASH_MOAT_DMG`, `SWASH_WALL_DMG`, `SWASH_CASTLE_HITS`, `MOAT_FILL_MIN`, `MOAT_DRY_SMALL/BIG`. |
| `patch_water9.py` | Applied on top of patch 8. Rising water in the moat (drawing only): moats and the castle ring are sunken trenches with inner walls and a floor; the water surface climbs the walls as it fills and drops as it dries. Knobs: `TRENCH_DEPTH`, `TRENCH_RING_DEPTH`, `TRENCH_RIM_GAP`. |
| `patch_truck10.py` | Applied on top of patch 9. Not water work: the cleaner truck now scales with zoom and is `TRUCK_SCALE` (2) times bigger. Drawing only. |
| `test_surge3.cjs` | 15 Playwright gameplay checks (moat/wall/castle damage, barrier, pour, dry, melt, build-phase safety). |
| `probe_block.cjs` | Fails if phone water is much blockier than desktop. |
| `probe_grid.cjs` | Fails if the tile grid shows through the shallows. |
| `probe_waves.cjs` | Wave behaviour: no banner, big wave crosses the castle side to side, swash fans out, speeds vary, backwash slows an incoming wave. |
| `probe_trench.cjs` | Rising water: the surface sits lower in deeper moats when half full and just below the rim when full; same for the castle ring. Fails on the build before patch 9. |
| `probe_truck.cjs` | Truck size: scales with zoom, and is sized against a tourist. Fails on the build before patch 10. |
| `probe_sizes.cjs` | Wave size: small vs large wave damage on moat / wall / castle, part-fill, fast vs slow drying, no damage in the build phase. |

## Rebuild check (any machine with Python 3)

```
git show main:sandcastle_iso2.html > main.html
python3 patch_water2.py main.html v2.html
python3 patch_water3.py v2.html v3.html
python3 patch_water4.py v3.html v4.html
python3 patch_water5.py v4.html v5.html
python3 patch_water6.py v5.html v6.html
python3 patch_water7.py v6.html v7.html
python3 patch_water8.py v7.html v8.html
python3 patch_water9.py v8.html v9.html
python3 patch_truck10.py v9.html v10.html
```

`v10.html` is identical to `sandcastle_iso2.html` on the branch, byte for byte.
(Use bash for the `git show ... >` step: PowerShell's `>` re-encodes the bytes.)

## Running the tests (needs Node + Playwright)

Serve a folder containing the build as `index.html`, then:

```
node test_surge3.cjs http://127.0.0.1:PORT/
node probe_block.cjs http://127.0.0.1:PORT/
node probe_grid.cjs  http://127.0.0.1:PORT/
node probe_waves.cjs http://127.0.0.1:PORT/
node probe_sizes.cjs http://127.0.0.1:PORT/
node probe_trench.cjs http://127.0.0.1:PORT/
node probe_truck.cjs  http://127.0.0.1:PORT/
```

Each exits 0 on pass and 1 on fail. `test_surge3.cjs` fails on main (no wave
system there); the block and grid probes failed on the pre-fix v3 build;
`probe_waves.cjs` failed 5 of its checks on the build before patch 5, and its
pitch/fan-out strength checks (W7, W8) failed on the build before patch 6.
