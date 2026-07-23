# STATE

## STATE - 2026-07-22
Live: v0.8.10 (commit 7e8f335), body receipt verified: YES (two stamps, both 7e8f335)
Golden: v0.8.10 (tag v0.8.10-golden)   Rollback: v0.8.9 (commit 5b5373b)
Last device pass: 2026-07-22, Android phone, GREEN
  Steps run: badge reads v0.8.10 . build 7e8f335 with correct middle dot;
  tide HUD renders correctly; game loads; castle + ocean render.
Backlog changes: opened #1-#11
NEXT ACTION: Disable GitHub Pages in repo settings (source -> None), then
rewrite CLAUDE.md to remove the self-contradictory Worker-embedding section
(#1).

## Session log

### 2026-07-22 - pipeline proof
Commits: 7ca4897 (hygiene), c183995 (wip gameplay + untrack dist),
76f89df (SHA stamp + guarded deploy script), 16f2730 (UTF-8 + cache-buster),
7e8f335 (ASCII-only script) -> GOLDEN

Established: git-derived build stamp replacing four hand-typed version
strings; deploy script with three guards (right repo / clean tree / pushed);
receipt verification against the served artifact; dist untracked.

Known-good before this session: 5b5373b.

## Backlog

#1  [HIGH] CLAUDE.md contradicts itself
    The "Deploy routine" section says the Worker embeds the game HTML in a
    backtick template literal and that live is a stale v0.6.1 prototype. The
    "Serving strategy (DECIDED July 2026)" section says the opposite. A fresh
    Claude Code session reads top-down and hits the false version first.
    Also stale: says X-Worker-Ver is "not yet implemented" (it is); session
    log describes version state as v0.7.2; deploy checklist describes the
    old script.
    Status: open

#2  [HIGH] Two water definitions across entities
    `isTileWater()` (grid-based) and `shoreYAtScreenX()` (screen-space)
    disagree. Bob uses a merged `nextIsWet` test; the cleaner truck uses a
    screen-space test with despawn+cooldown. A third entity will get a third
    answer.
    Root cause: (blank until diagnosed)
    Status: open - candidate fix is one exported primitive every entity and
    the tide itself calls.

#3  [SEV?] Tide does not visually reach the castle at peak
    Repro: (needs exact steps)
    Root cause: (blank) - suspected #2
    Status: open

#4  [SEV?] Cleaner truck drives into the ocean
    Guard shipped in 7e8f335, unverified on device.
    Status: fixed-unverified

#5  [SEV?] Bob enters the ocean
    Refactor shipped in 7e8f335, unverified on device.
    Status: fixed-unverified

#6  [LOW] Version badge overlaps tide HUD text
    Badge grew when the build stamp was added.
    Status: open

#7  [MED] Simulation is frame-coupled
    Decay rates and cooldowns expressed in ticks-at-60fps. WORKFLOW sec.8 wants
    fixed-timestep decoupled from render; calls it near-impossible to
    retrofit. Currently load-bearing.
    Status: open - needs an explicit decide/defer/accept-debt call.

#8  [MED] Balance data lives in code
    DECAY_RATE{}, SHORE_HIGH_CAP/MAX, wave scaling constants. WORKFLOW sec.8
    wants these in src/data/*.json so tuning is editing, not engineering.
    Status: open

#9  [MED] RNG unseeded
    Tide peak and speed randomize per cycle. "The truck drove into the ocean"
    is not reproducible on demand.
    Status: open

#10 [LOW] Portrait _FIT_ZOOM gap
    On portrait viewports _FIT_ZOOM fits by width, so low-tide waterline
    lands ~50-54% down screen instead of the intended 75%. Needs fit-by-height
    on tall aspect ratios.
    Status: open

#11 [LOW] Commit c183995 has a misleading message
    Says "wip: tide retune..." but also contains 3400 deletions from
    untracking public/index.html. Pushed; not worth a force-push to fix.
    Status: wontfix - noted for archaeology.

## Deviations from WORKFLOW, accepted
- sec.3 src/dist split not done. Project is a working single-file monolith at
  v0.8.10, not day one. Large blast radius; ships alone when scheduled.
- sec.8 fixed-timestep not done. See #7.
