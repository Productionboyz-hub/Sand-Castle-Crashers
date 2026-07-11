# CLAUDE.md — Sand Castle Crashers

Read this before patching `sandcastle_iso2.html`. It's the durable memory for this
project — every Claude Code session should read it regardless of which chat
started the work.

## Project

- Single-file vanilla JS + Canvas 2D game: `sandcastle_iso2.html` (~2472 lines
  as of v0.5.1). No framework, no build step, no bundler.
- Deploy: Cloudflare **Worker** (`sand_castle_worker.js` via `wrangler.toml`)
  — see "Deploy routine" section below. Do NOT assume static Pages.
- Editing model: structural changes/new features → `str_replace` patches only,
  never full-file rebuilds. Constant tuning → direct edit via `Ctrl/Cmd+F` on
  named constants.
- Game type (design decision, locked): **endless-wave survival**. Score = waves
  survived. Difficulty ramp = discrete waves with rebuild breaks between them
  (build phase / defend phase state machine). Enemies scale per wave.

## Locked architecture — do not restructure without explicit confirmation

### Render loop order (`render()`, driven by `requestAnimationFrame`)

1. `tick++`
2. Camera/zoom ease toward `camAngleDest` / `camZoomDest`
3. Tide phase advance; `shoreD` eases toward target
4. Wave ring spawn / update / prune
5. `buildWaterTex()` — only every 3rd tick
6. Clear canvas + `drawSky()`
7. Build + depth-sort all `GCOLS × GROWS` tiles by rotated `(col + row)`
8. Draw each tile (water fill, or sand + shore wet-tint) + foam + wave rings
9. `drawMoat(tick)`, `drawCastle(tick)`
10. `tickDeterioration()`
11. `if (!gameOver) tickEnemies()`
12. `drawPlacedPieces()`, `drawEnemies()`, `drawCastleHUD()`
13. `if (gameOver) drawGameOver()`
14. Update HUD text
15. `drawGhost(tick)`
16. `requestAnimationFrame(render)`

Order matters: `tickEnemies()` must run after `tickDeterioration()` and before
the draw calls, so damage dealt this frame is visible this frame.

### Coordinate pipeline — always route through `rotateGrid()` / `iso()`

- `rotateGrid(col, row)` rotates around pivot `(ORBIT_PIVOT_C, ORBIT_PIVOT_R)`
  = `(5.5, 5.5)` by `camAngle` (radians).
- `iso(col, row, z)` calls `rotateGrid()` internally, then applies
  `TW()/TH()` (tile size scaled by `camZoom`).
- **Any new draw function must go through `iso()`.** Hand-rolled screen-position
  math that skips `rotateGrid()` will look fine at `camAngle = 0` and silently
  desync at every other rotation angle.
- `screenToGrid()` is the inverse, used for placement hit-testing — keep it
  consistent with `iso()`.

### Enemy system

- All enemy types share one flat array: `enemies[]`. No per-type arrays.
- Common fields: `type` (`'crab' | 'tourist' | 'bird' | 'bob'`), `col`, `row`,
  `hp`, `state` (`'active' | 'scared'`), plus a damage/scared timer. Type-specific
  fields are added ad hoc (e.g. crab: `legPhase`, `landTimer`; bird: `orbitAngle`,
  `altitude`, `poopTimer`).
- **Damage-chain pattern** (locked — new enemy types must follow this order):
  1. Blocked by a moat piece on that tile? → damage the moat piece, don't advance.
  2. `nearestPiece()` within range? → damage that piece.
  3. Otherwise → `damageCastle()` directly.
- Tap-to-scare is uniform across types: `hp` decrements per tap; at 0, enemy
  enters `state = 'scared'`, retreats, and despawns after
  `ENEMY_SCARED_DURATION` frames.

### Castle HP / game state

- Current game-status state is only `castleHP` (0–100) and `gameOver` (bool).
  **No score or wave counter exists yet** — that's the next build step, not
  already-locked behavior.
- `damageCastle()` is the sole mutator and early-returns if `gameOver`.
- Restart (click/touchend while `gameOver`) resets: `castleHP`, `gameOver`,
  `placedPieces`, `enemies`, `poopSplats`, and all four spawn timers
  (`crabSpawnTimer`, `touristSpawnTimer`, `birdSpawnTimer`, `bobSpawnTimer`).
  **Any new persistent state (score, wave number) must be added to this reset
  list too, or it'll survive across restarts incorrectly.**

## Known failure modes — check every patch against these

- **Switch/case scoping collisions.** A `const t` collision inside a
  switch/case previously broke the eraser on drawbridge pieces. Fixed by
  renaming to `tf`/`gf`/`db1`/`db2`. Watch for any new `const`/`let` declared
  inside a bare `case` block.
- **Missing top-level declarations.** `let tick` has been lost during
  insertions before. It's anchored immediately before `render()` is invoked at
  the bottom of the file — don't let an insertion push it out of scope.
- **Eraser must bypass `isTileWater()` entirely.** The eraser was previously
  blocked near shore because it ran through the same water-tile gate as normal
  placement. Eraser logic must skip that check.
- **Geometry must route through `rotateGrid()`.** See coordinate pipeline
  above — this is the single most common way new features silently break at
  non-zero camera angles.
- **Comment anchors (`// ──` section markers) are load-bearing.** They define
  module boundaries used for targeted patching and navigation. Preserve them
  exactly; don't rename or remove during unrelated edits.

## How to hand changes to J (the human)

J often works from mobile and is not assumed to know editor/terminal
conventions by heart. When a change requires manual steps on J's machine,
give **literal, numbered, step-by-step instructions**, and be explicit about
*which surface* each step happens in:

- **VS Code editor** — say exactly what to `Ctrl+F` for, what line/anchor to
  find, and show the exact before/after code block to paste.
- **VS Code integrated terminal** vs. **standalone PowerShell** — these are
  different. Say which one to open (`` Ctrl+` `` for the integrated terminal;
  Start menu → PowerShell for standalone) and give commands in PowerShell
  syntax, since J is on Windows. Don't give bash-only syntax without a
  PowerShell equivalent.
- **Browser dev console** (F12 → Console) — if a step involves checking a
  console error or running a quick JS snippet, say so explicitly and give the
  exact snippet.
- Never assume a step is obvious. "Commit and push" should be spelled out as
  the actual git commands (or the VS Code Source Control UI clicks) the first
  time it appears in a session.

## Deploy routine — Worker-based (IMPORTANT, read before deploying)

The live site is served by a **Cloudflare Worker**, not static Pages:

- `wrangler.toml`: `name = "sand-castle-crashers"`, `main = "sand_castle_worker.js"`
- `sand_castle_worker.js` embeds the ENTIRE game HTML inside a single backtick
  template literal and returns it as the fetch response.
- Deploy scripts: `deploy.ps1` / `deploy_scc.ps1` (PowerShell, presumably run
  `wrangler deploy`).
- **Known state (July 2026):** the HTML embedded in the Worker is a stale,
  divergent prototype (labeled v0.6.1 — different piece system, no orbit
  camera, no enemies). It is NOT generated from `sandcastle_iso2.html`. The
  live site does not reflect the current game until this is reconciled.

### Embedding constraints (source of the backtick rule)

Because the game ships inside a Worker template literal:
- Backticks (`` ` ``) in game code terminate the wrapper string → Worker breaks.
- `${...}` in game code gets interpolated by the Worker's JS → silent corruption.
- `</script>` must be escaped as `<\/script>` inside the embedded string.
- The current `sandcastle_iso2.html` contains ~10 template literals with
  `${}` — it CANNOT be pasted into the Worker as-is. Either convert those to
  string concatenation first, or change the serving strategy (see open
  decision below).

### X-Worker-Ver header

Not yet implemented. When touching the Worker, add a version header to the
Response (matches the Soccer App pattern), e.g.:
`headers: { 'Content-Type': 'text/html; charset=utf-8', 'X-Worker-Ver': '<version>' }`
so a deploy can be confirmed via browser dev tools → Network → response headers.

### Serving strategy (DECIDED July 2026: static assets)

- Game HTML lives at `public/index.html` (copy of `sandcastle_iso2.html`).
- `wrangler.toml` has an `[assets]` block: `directory = "./public"`, `binding = "ASSETS"`.
- `sand_castle_worker.js` is a ~12-line thin Worker: fetches the static asset,
  stamps `X-Worker-Ver`, returns it. No embedded HTML — never go back to embedding.
- Deploy = update `public/index.html` to match `sandcastle_iso2.html`, bump
  `WORKER_VER` in the Worker, run `wrangler deploy`.
- Verify deploy: browser F12 → Network → reload → click the document request →
  Response Headers → `X-Worker-Ver` matches.

### Version numbering

Old embedded prototype said v0.6.1; iso file was v0.5.x. Reconciled at
**v0.7.0** (July 2026). Single version line from here: game header comment,
`<title>`, and `WORKER_VER` all move together.

## Build plan (current sequence)

One verified change per prompt, diagnose-before-fix discipline:

1. ~~Create `CLAUDE.md`~~ — this file
2. Remove debug immediate-spawn of Bird/Bob (currently called at file end,
   right before `let tick = 0` — comments say "for testing")
3. Add score + wave counter (state + HUD)
4. Add wave phase system (build/defend state machine with rebuild breaks)
5. Add per-wave difficulty scaling

## Backtick template literals — soft constraint only

The old hard reason (Worker embedded the game in a template literal) is GONE —
the game is now served as a static asset. Remaining guidance:
- Existing template literals in the game file are fine; leave them.
- Prefer concatenation in new patches only because `${}` inside backticks is
  fragile for `str_replace` exact-matching; quote generous context when a
  patch touches a backtick line.

---

## Session log — post-v0.7.2 divergence

### Version state (as of this audit)

- **Line 1 comment, `<title>`, `WORKER_VER`**: all still read `v0.7.2` — **stale**.
  Actual content is at v0.7.8 per git log. None of the incremental sessions
  updated the version line in the HTML or the Worker. Next session must bump
  all three before deploying.
- `sandcastle_iso2.html` == `public/index.html` byte-for-byte ✓
- `sand_castle_worker.js` WORKER_VER still `'v0.7.2'` — X-Worker-Ver header
  will report wrong version until bumped.

---

### Changes made since v0.7.2 (by area)

#### CSS / Layout (lines 9–130)

| What changed | Detail |
|---|---|
| `body` | Removed flex centering; now `overflow:hidden; width:100vw; height:100vh` |
| `#hud` | Moved inside `#game-wrap`; now `position:absolute; bottom:6px; left:50%; transform:translateX(-50%)` overlay |
| `#game-wrap` | Changed from `display:inline-block` to `width:100vw; height:100vh` |
| `#toolbox, #countertoolbox` | Merged shared ruleset; added `-webkit-overflow-scrolling:touch`; `max-height:calc(100% - 16px)` |
| `#countertoolbox` | **New element** — `left:6px`, green border `rgba(100,200,120,0.25)` |
| `.counter-btn` + variants | **New classes** — mirror `.tool-btn` with green accent for countermeasure buttons |

#### HTML (lines 128–150)

- `<div id="countertoolbox">` added (left side, before `#toolbox`)
- `<div id="hud">` moved from after `#game-wrap` to inside it

#### New constants (lines 187–200)

```
const _GRID_DIAG = GCOLS + GROWS;   // 32 — diagonal tile span
const _FIT_ZOOM  = Math.min(         // auto-fit zoom on load
  (SW * 0.82) / (_GRID_DIAG * TW_BASE / 2),
  (SH * 0.78) / (_GRID_DIAG * TH_BASE / 2)
);
```
- `OY` now computed: `(SH - _GRID_DIAG * TH_BASE * _FIT_ZOOM / 2) * 0.32`
  (was `SH * 0.06`)
- `camZoom` and `camZoomDest` initialised to `_FIT_ZOOM` (was `1.0`)

#### Modified orbit-drag guards (lines 252, 271)

- `canvas mousedown` and `canvas touchstart` both now check
  `if (selectedPiece || selectedCounter) return;`

#### New state variables (lines 952–953)

```js
let selectedCounter  = null;  // 'lightning' | null — active countermeasure
let lightningStrikes = [];    // [{x, y, timer, maxTimer}] — bolt animations
```

#### New section: `// ── COUNTERMEASURES ──` (lines 951–1088)

- `const COUNTERS = [{ id:'lightning', label:'Lightning', drawIcon(ctx,cx,cy){…} }]`
- `counterToolboxEl` — pointer to `#countertoolbox` DOM element
- `COUNTERS.forEach(…)` — builds counter buttons into left panel; each button
  has `click`, `touchstart`, `mousedown` handlers that set `selectedCounter`
  and clear `selectedPiece` (mutually exclusive with build tools)
- `activateLightning(sx, sy)` — finds nearest active bird within 120 px via
  `iso(e.col, e.row, e.altitude)`, sets `hp=0 / state='scared'`, pushes
  `{x, y, timer:22, maxTimer:22}` into `lightningStrikes`
- `drawLightningStrikes()` — draws fading three-pass jagged bolt (glow / yellow
  core / white centre); ages and splices expired entries

#### Modified: Escape keydown (line 927)

Now also sets `selectedCounter = null` and removes `.counter-btn.selected`.

#### Modified: toolbox button `touchstart` (line ~903)

Removed `isDragging = true` — was causing premature placement on simple taps.
Also now clears `selectedCounter = null` and deselects counter buttons.

#### Modified: `window.touchmove` (line 1130)

Added `isDragging = true` — drag state is only set once actual finger movement
is detected, keeping tap-to-select clean.

#### Modified: `placePiece()` (lines ~1193–1209)

After successful placement: `selectedPiece = null`, `isDragging = false`,
deselects all `.tool-btn.selected` — the "land and release" behaviour.

#### Modified: `window.touchend` (lines 1120–1129)

Removed `isDragging` requirement. Now places if `selectedPiece` is set **and**
the lift point is within canvas bounds (`0 ≤ sx ≤ canvas.width`, etc.).

#### Modified: `startWave()` (line 1599)

`birdSpawnTimer = ENEMY_BIRD_SPAWN_RATE` (was `0`) — one bird spawns on the
very first tick of every wave instead of waiting 600 ticks.

#### Modified: `// ── TAP TO SCARE / COUNTERMEASURE DISPATCH ──` (lines 2059–2092)

Anchor renamed from `// ── TAP TO SCARE ──`. Canvas `click` and `touchend`
handlers now dispatch to `activateLightning()` when `selectedCounter === 'lightning'`
before falling through to `tryScareEnemy()`.
`tryScareEnemy()` now skips birds (`if (e.type === 'bird') continue`).

#### Modified: render loop (line 2743)

`drawLightningStrikes()` inserted between `drawEnemies()` and `drawCastleHUD()`.

---

### Architecture violation flags (do not fix without review)

#### 🔴 Restart reset list — missing new state

Both restart handlers (canvas `click` and `touchend`, lines 1728–1755) are
**missing resets for**:
- `lightningStrikes.length = 0` — in-flight bolt animations survive restart
- `selectedCounter = null` — selected countermeasure persists across restart

Per CLAUDE.md rule: any new persistent state must be added to both restart
handlers. Fix before shipping multiplayer or any scenario where stale bolt
animations or tool state at restart would matter.

#### 🟡 Render loop step 12 split

CLAUDE.md lists step 12 as `drawPlacedPieces()`, `drawEnemies()`, `drawCastleHUD()`
as a group. `drawLightningStrikes()` is now inserted between `drawEnemies()` and
`drawCastleHUD()`. Visually correct (bolts over enemies, under HUD) — but the
locked spec should be updated to include this step explicitly.

#### 🟡 `// ── CANVAS SIZE` anchor comment stale

Body still reads "change 740/520 to resize the game window" — those hardcoded
values no longer exist (now uses `_FIT_ZOOM`). Anchor name is preserved ✓ but
the inline note is misleading.

---

### Comment anchors status

All `// ──` section markers present and intact. Two new anchors added:
- `// ── COUNTERMEASURES ───` (line 951)
- `// ── LIGHTNING STRIKE ─────` (line 1030)
