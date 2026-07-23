# STATE

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
