# Athletic South LA Soccer App — Claude Code Rules

## Project
- Single-file HTML app: `index.html`
- Live URL: `athleticsouthla.athleticsouthla.workers.dev`
- GitHub: `https://github.com/Productionboyz-hub/Athletic-Soccer-App`

## Self-Report on Every Prompt
Start each response with current version number and most recent change.

## Deploy Workflow (in order)
1. `git add -A`
2. `git commit -m "vXXX: description"`
3. `git push`
4. `wrangler deploy`

- Run from CMD only — NOT PowerShell (execution policy restrictions)

## File Operations (mandatory)
Always use .NET method, never PowerShell pipeline:

```powershell
[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::ReadAllText($path)
```

## Code Rules
- No backtick template literals anywhere (Android browser compatibility)
- Stats keyed by jersey number via `statsByNum`, not slot index
- One isolated change per prompt; test on iPad before next change
- Diagnose before editing — confirm root cause before applying any fix

## LOCKED CSS — Do Not Modify Under Any Circumstances
- Portrait `#fw`: `height:0; padding-bottom:68%` (padding-bottom % trick, confirmed working iPad portrait)
- Landscape `#pg0`: CSS grid layout with 63/37 column split, pitch spanning rows 2–6
- `#pk-section{display:none !important}` in landscape media query
- Player token sizing: 4 breakpoints + orientation overrides
  - Base rule + `@media(min-width:430px)` + `@media(min-width:700px)` + `@media(min-width:900px)` + orientation:landscape overrides combined with each width breakpoint
  - Before any sizing/layout change to `.player` or similar elements, grep ALL breakpoints first — editing only the base rule has no visible effect because width breakpoints override it

## Backlog (priority order)
1. Leaderboard verification on Summary page
2. Samsung portrait layout cramping
3. Landscape mirroring
4. Summary page back-navigation
5. "Add Match for Friendlies" page (incomplete)

## Branding
- Deep navy `#1a2a4a`
- Electric teal `#00e5b0`

## Testing
- Primary test device: iPad Air (Safari)
- Secondary: Samsung devices
- Hard refresh required on Samsung — do not test via PWA Home Screen shortcut (caches stale builds)
