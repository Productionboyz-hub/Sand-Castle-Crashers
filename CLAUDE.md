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
