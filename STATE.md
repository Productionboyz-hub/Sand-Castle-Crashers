# STATE

## STATE - 2026-11-12
Live: unchanged (v0.8.10). No deploy this session. Golden unchanged.
New branch: feature/water-v3 - water v3 (realistic water + big waves).
  NOT merged, NOT deployed. Held off main so the efba0f1 device pass
  (#2) stays bisectable. Merge only after that pass is green.
What it is: prototype built in a soccer-app session (handoff commit
  e9868e9), approved by J from preview clips, then two fixes here:
  phone water was blocky (pattern scale floored, finer texture on small
  screens) and the tile grid showed through the clear shallows
  (per-tile isShore tint removed). Scripts + tests now live in
  tools/water-v3/ - this repo no longer depends on the soccer repo.
Verification (headless only - NOT a device pass):
  test_surge3.cjs 15/15 PASS on branch, FAILS on main (expected).
  probe_block.cjs PASS on branch, FAILED on pre-fix v3 (iPhone 2.47 -> 1.47
  vs desktop ~1.2). probe_grid.cjs PASS on branch (0.88), FAILED on
  pre-fix v3 (2.8). In-repo scripts rebuild the committed file from main
  byte-for-byte.
Second commit, same day - J tested the branch on PC ("water looks great")
  and asked for wave changes: no BIG WAVE banner; waves enter from one
  side, slosh across to the other and fan out (big waves too); random
  slow/fast waves; a retreating wave slows an incoming one. Done in
  patch_water5.py. Each wave now runs on its own clock (w.p), not
  tick - born. probe_waves.cjs: ALL PASS on branch, 5 of 7 FAILED on the
  previous commit. test_surge3 15/15 x3 runs, block + grid probes PASS.
  New TUNE knobs: SWASH_SPEED_MIN/MAX, BACKWASH_DRAG, BACKWASH_MIN.
Third commit, same day - J asked for more extreme pitch and fan-out.
  patch_water6.py: SWASH_PITCH 0.6 -> 1.6 (waterline tips ~2 tile-heights
  end to end at its peak, was ~0.75), fan-out ~4-8x landing width (was
  ~2-4.5x), faster sideways slosh. probe_waves W7/W8 PASS on branch, FAILED
  on the previous commit. test_surge3 15/15 x3.
  Test change, stated plainly: test_surge3 S1f (moat dries gradually)
  failed 1 run in 2 because an ordinary wave topped the moat back up
  mid-dry. The drying phase of the test now runs with ordinary waves
  switched off. The top-up itself is real game behaviour, visual only
  (ordinary waves never damage), and was already common on the previous
  commit at mid/high tide (moat at 8,8 reached 78% / 100% of ticks).
Direction (J, 2026-11-12): the game will eventually move to 3D sprites.
  Wants to SEE a moat fill with water (not a flat blue fill) and SEE walls
  melt/crumble. Keep both effects; any sprite pipeline must support them
  (fill level and damage stages), see CONTEXT.md art direction.
Fourth commit, same day - two more asks from J after watching it:
  (a) waves looked like "piano keys pressed left to right" - each wave was
  a bump travelling sideways. patch_water7.py: waves are POURED - land at
  one spot, the front slides along the beach, thins, the sheet behind
  stays up then drains; foam/streaks/flecks in the thin water are carried
  sideways (flowPh, drawing only). (b) patch_water8.py: wave SIZE matters.
  Small wave part-fills a moat and it dries in ~1 s; big wave fills it and
  it dries in ~8 s. Ordinary waves now do a LITTLE damage, defend phase
  only, same locked chain (moat -> nearest sea-side wall -> castle),
  scaled by size: max 4 to a moat or wall (a big wave does 34 / 40), and
  0.34 of a castle hit (accrued in swashCastleDebt, paid via
  damageCastle()). Big-wave damage unchanged.
  DESIGN CHANGE: ordinary swash is no longer drawing-only.
  New persistent state swashCastleDebt and ringK are in BOTH restart
  handlers' reset lists.
  Measured (headless, 60 s of defend, no big waves): low and mid tide
  ordinary waves never reach a piece at (8,8); at high tide a moat or wall
  there loses roughly 12-22 health a minute.
  Tests: probe_sizes.cjs ALL PASS (5 of 7 FAIL without patch 8);
  probe_waves ALL PASS (pour checks W9/W10 FAIL without patch 7);
  test_surge3 15/15; block + grid PASS. Test isolation, stated plainly:
  test_surge3 now switches ordinary waves off during its big-wave
  scenarios (they do damage now) and holds off the next big wave while it
  watches the moat dry.
Fifth commit, same day - rising water in the moat (J's "SEE a moat
  fill" ask). patch_water9.py, DRAWING ONLY: moats and the castle ring
  are sunken trenches (two inner walls + floor; shallow / standard / deep
  floors at 0.2 / 0.38 / 0.58 tile-heights, ring 0.38). The water surface
  climbs the walls to just below the rim and drops as it dries, leaving
  floor and walls damp. Level = p.depth * p.cover (ring: ringDepth *
  per-tile cover). No new persistent state; damage, fill and dry rates
  untouched. Neighbouring trench tiles join (no wall between them).
  drawPoolOnTile() replaced by drawTrenchOnTile().
  Tests (light, one run each): probe_trench.cjs ALL PASS on branch,
  3 of 5 FAIL on the previous commit; test_surge3 15/15. Other probes
  NOT re-run this commit. Rebuild main + patches 2-9 = committed file.
  Known look issue: the old per-tile rim outline still draws a thin line
  between joined moat tiles.
Sixth commit, 2026-11-13 - cleaner truck size (NOT water work; on this
  branch as its own commit because it is the branch J is testing).
  patch_truck10.py, DRAWING ONLY: the truck was drawn in fixed pixels, so
  it ignored zoom and was barely longer than a tourist is tall. Now scales
  with camZoom (same 0.9 factor as tourists/crabs) times TRUCK_SCALE = 2:
  about 2.6 tourist-heights long. Speed, pickup radius, coins, cooldown
  untouched. probe_truck.cjs ALL PASS on branch, 2 of 3 FAIL on the
  previous commit. No other tests re-run.
  Design ideas raised by J, not started: begin with a small starter
  castle (one bucket mound) that grows with waves survived, instead of a
  full castle on an empty beach. Castle stays oversized against people on
  purpose (hero scale). Crab size against people not yet checked.
GAME_VER still reads v0.8.10 on the branch - bump at merge/deploy time.
Backlog changes: opened #17 (damp-band hard edge), #18 (water v3 open
  items).
NEXT ACTION: unchanged from 2026-07-24 (deploy + device pass for efba0f1).
  Then: device pass of feature/water-v3 on iPad + iPhone (portrait),
  covering #18, before merging.

## STATE - 2026-07-24
Live: v0.8.10 (commit 7e8f335 game build), deploy receipt re-verified from
NEW repo path: YES (two stamps, both 606c0c5 - the docs-only HEAD).
Golden: v0.8.10 (tag v0.8.10-golden)   Rollback: v0.8.9 (commit 5b5373b)
Repo relocated: C:\Users\admin\OneDrive\Sand Caslte Crashers ->
  C:\Users\admin\Sand-Castle-Crashers. Proven working, deploys clean.
Last device pass: 2026-07-22, Android phone, GREEN (unchanged - no game code
  touched this session; move was infrastructure only).
Backlog changes: closed #14 (repo move). #15 already verified.
NEXT ACTION: Deploy 85c62b4, verify receipt. Flip FORCE_HIGH_TIDE=true,
commit/push/deploy/verify, run full device pass against that receipted
build. Revert toggle, redeploy, reverify, then watch a natural tide cycle
for #3. Then promote golden.
## STATE - 2026-07-23
Live: v0.8.10 (commit 7e8f335), body receipt verified: YES (carried from
2026-07-22; no deploy this session)
Golden: v0.8.10 (tag v0.8.10-golden)   Rollback: v0.8.9 (commit 5b5373b)
Last device pass: 2026-07-22, Android phone, GREEN
Backlog changes: opened #12-#14; #12 verified; #8 unblocked; #1 still open
NEXT ACTION: Relocate repo out of OneDrive (#14). Ships alone per
WORKFLOW sec.9. Path inventory by grep first, then diff, then a full
deploy loop including receipt.

## STATE - 2026-07-22
Status: DONE 2026-07-24. Copied to C:\Users\admin\Sand-Castle-Crashers
    via robocopy (162 files, 0 failed), git fsck clean, tip 606c0c5 on main.
    Deploy proven from new path: receipt verified, two 606c0c5 stamps live.
    VS Code re-pointed to new folder. Old OneDrive copy NOT renamed - OneDrive
    held a lock; left in place as warm fallback, retire next session.
    KNOWN TRAP: soccer-app repo also on this machine; VS Code terminal opens
    there by default. First command every session: cd to the new path, confirm
    606c0c5/main before anything else.
Golden: v0.8.10 (tag v0.8.10-golden)   Rollback: v0.8.9 (commit 5b5373b)
Last device pass: 2026-07-22, Android phone, GREEN
  Steps run: badge reads v0.8.10 . build 7e8f335 with correct middle dot;
  tide HUD renders correctly; game loads; castle + ocean render.
Backlog changes: opened #1-#11
NEXT ACTION: Disable GitHub Pages in repo settings (source -> None), then
rewrite CLAUDE.md to remove the self-contradictory Worker-embedding section
(#1).

## Session log

### 2026-07-23 - infrastructure hardening, no version change
No code changed. No deploy. Golden unchanged.

GitHub Pages was found LIVE, deploying from main / (root), last built
~40 min prior - a second artifact URL serving the SOURCE file, not build
output. CONTEXT.md asserted Pages was disabled; it was not. Disabled at
source (branch -> None), not merely unpublished: GitHub's own dialog
states unpublish "will not prevent it from being rebuilt."

Credential scan across all 34 commits: no token, key, or bearer anywhere.
.wrangler/cache/wrangler-account.json (25 pre-hygiene commits) carries the
Cloudflare account ID under key "id" plus an author email. Not a
credential. No history rewrite - see #13.

.gitignore corrected: *.json -> /*.json (root-anchored; the unanchored
rule would have silently swallowed src/data/*.json and blocked #8), and
public/index.html -> public/ (old rule covered one file, not the
directory).

Local hygiene, not repo state: Chrome "ask where to save each file"
disabled - it overrides the Location setting and defaults to last-used
folder, which is how strays kept landing in project dirs. Sand Castle
folder pinned "Always keep on this device."

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
    Root cause: two divergent evaluations of the same shore-boundary
    formula - isTileWater() exact-evaluated on rounded grid coords vs.
    shoreYAtScreenX() iteratively solved via an iso()-then-back round-trip.
    Status: FIX APPLIED (efba0f1), ZERO device coverage. Never deployed.
    The 2026-07-24 pass ran against pre-fix code (live build 606c0c5).
    Full pass required after deploying efba0f1: truck, Bob, crab avoidance,
    plus the tourist off-grid despawn hunk (the only behaviour-changing
    hunk, still uncovered - tourists didn't spawn).

#3  [SEV?] Tide does not visually reach the castle at peak
    Repro: (needs exact steps)
    Root cause: (blank) - suspected #2
    Status: open, untested. Requires natural tide cycle on a deployed
    build.

#4  [SEV?] Cleaner truck drives into the ocean
    Guard shipped in 7e8f335, unverified on device.
    Status: VERIFIED 2026-07-24 on live build 606c0c5 (game code 7e8f335).
    Truck drove along the tide's edge, never entered water. Verifies the
    7e8f335 guard, NOT the efba0f1 refactor.

#5  [SEV?] Bob enters the ocean
    Refactor shipped in 7e8f335, unverified on device.
    Status: VERIFIED 2026-07-24 on live build 606c0c5 (game code 7e8f335).
    Bob beelined to lure, stopped, despawned (lure single-use = expected),
    never entered water. Verifies the 7e8f335 merged nextIsWet test, NOT
    efba0f1.

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
    Unblocked 2026-07-23: /*.json anchor makes src/data/*.json trackable.

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

#12 [HIGH] GitHub Pages was live as a second artifact URL
    Found 2026-07-23 deploying from main / (root). Served repo root, i.e.
    the SOURCE file, not build output. A device pass run against that URL
    would have been meaningless. CONTEXT.md asserted Pages was disabled;
    it was not.
    Fix: branch source set to None (full disarm, not unpublish).
    Status: verified 2026-07-23 - 404 confirmed after push d06cb92, which
    was the rearm opportunity.

#13 [LOW] Cloudflare account ID + author email in public repo history
    .wrangler/cache/wrangler-account.json in 25 pre-hygiene commits,
    account ID stored under key "id". No credential exposed - no token,
    key, or bearer in any of 34 commits.
    Decision: no history rewrite. filter-repo cannot remove the email
    (commit metadata carries it on every commit regardless) and a
    force-push would invalidate golden 7e8f335, tag v0.8.10-golden,
    rollback 5b5373b, and every recorded body-receipt SHA.
    Prevention confirmed: .wrangler/ ignored at .gitignore line 3.
    Status: accepted-risk, unless repo goes private.

#14 [MED] Repo lives inside OneDrive
    C:\Users\admin\OneDrive\Sand Caslte Crashers. OneDrive syncs .git/ and
    can create conflict copies or dehydrate files git needs; a corrupted
    .git takes local history, tags, and golden refs with it. The soccer
    app - which taught every rule in WORKFLOW - has always lived at
    C:\Users\admin\Athletic-Soccer-App, outside OneDrive. Sand Castle is
    the outlier.
    Target: C:\Users\admin\Sand-Castle-Crashers (also fixes the "Caslte"
    typo and removes spaces from the path).
    Touches: deploy_scc.ps1 Set-Location, .code-workspace paths, Claude
    Code working dir, any Google Drive sync reference.
    Mitigated: folder pinned "Always keep on this device" - stops
    dehydration, does NOT stop conflict copies.
    Status: open - ships alone, own device pass.

#15 [LOW] Two soccer-app JSON files sat in repo root
    asl_backup_v4.json (173 KB) and asl_settings_v4.json, both dated
    2026-07-15. Untracked, ignored by /*.json, never in git history on
    any ref. Noticed 2026-07-23 during the robocopy listing, not created
    then. Origin unknown and not worth further archaeology: Chrome
    download settings verified clean, no recent soccer-app write
    activity, no evidence of an ongoing cause.
    Fix: moved to _scc_scratch 2026-07-23. Do not delete - possibly the
    only copy.
    Status: verified

#16 [MED] Placement ghost teal collided with WATER_SHALLOW
    The valid-placement ghost fill/stroke used teal
    rgba(100,220,200,0.18) / #7ae8d8. WATER_SHALLOW is [90,190,200]
    (~#5abec8) - near-identical. Valid tiles and shallow water read
    as the same color, against pillar 4 and the contrast budget.
    The floating drag-badge border used the same teal.
    Repro: drag a piece near the waterline; ghost and water are hard
    to separate at a glance in portrait.
    Root cause: highlight color chosen from inside the environment
    palette instead of outside it.
    Fix: both sites changed to lime rgba(212,232,90,0.20) / #dceb5c.
    Committed 11e12a0 on branch fix/lime-ghost-highlight. NOT merged,
    NOT deployed - held out of the in-flight device pass sequence so
    a red result stays bisectable.
    Status: fixed-unverified

#17 [LOW] Damp-sand band has a hard bottom edge
    The baked damp band (sandcastle_iso2.html ~line 468, dampGrad) fades
    in from transparent to 0.18 and then stops dead at MEAN_WATERLINE_Y,
    leaving a straight horizontal line across the sand at low tide.
    Present on main (confirmed by screenshot 2026-11-12); water v3's
    clear shallows and wet sand make it more noticeable.
    Likely fix: fade the band out below MEAN_WATERLINE_Y too.
    Status: open - separate change, not part of water v3.

#18 [MED] Water v3 - unverified areas (branch feature/water-v3)
    Not yet checked: portrait phones on a real device, pinch zoom, high
    tide against the castle walls, frame rate on iPad/iPhone.
    Balance numbers are first guesses (named constants, TUNE markers):
    BIGWAVE_MOAT_DMG 34, BIGWAVE_WALL_DMG 40, BIGWAVE_CASTLE_HITS 3,
    BIGWAVE_GAP_MIN/MAX 700-1500 ticks (~12-25 s), BIGWAVE_FIRST 480.
    Old per-tile foam dots removed (they showed as stripes in the
    shallows); foam now only along the real water edge.
    Ordinary-wave damage numbers (SWASH_MOAT_DMG 4, SWASH_WALL_DMG 4,
    SWASH_CASTLE_HITS 0.34) and moat dry times (MOAT_DRY_SMALL/BIG) are
    first guesses - needs play-testing across a full tide cycle.
    Big waves now arrive with no banner (J's call) - check on device
    that the draw-back before the surge is enough of a tell. Wave feel
    knobs (SWASH_SPEED_MIN/MAX, BACKWASH_DRAG/MIN) are first guesses.
    Status: open - needs coach device pass before merge.

## Deviations from WORKFLOW, accepted
- sec.3 src/dist split not done. Project is a working single-file monolith at
  v0.8.10, not day one. Large blast radius; ships alone when scheduled.
- sec.8 fixed-timestep not done. See #7.

## Standing decisions, undecided
- Repo public vs private. Public today. Private removes the #13 exposure
  including the commit-metadata email that filter-repo cannot reach, at
  near-zero cost: no Actions, no collaborators, deploys run locally.
- Where assets live when real. Root is currently a junk drawer; a tracked
  /assets/ makes root unambiguously disposable.
- #7 frame-coupled simulation: decide / defer / accept-debt permanently.
- CLAUDE.md role: fourth doc holding code invariants only, or collapse
  into the three and delete. Blocks #1.
