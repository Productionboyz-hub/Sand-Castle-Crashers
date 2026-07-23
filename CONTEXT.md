# Sandcastle Crashers - CONTEXT

## What it is
Browser-based isometric tower-defense / builder. The player constructs a sand
castle on a beach grid and defends it against beachgoers and the tide.

## Core design pillars
1. Build and defend in alternating phases - player triggers each wave.
2. Everything decays. Pieces lose health continuously; the sea is a standing
   threat, not an enemy type.
3. Indirect defense. The player places countermeasures that redirect or trap
   enemies rather than attacking them.
4. Readable at a glance on a phone held in portrait.

## Stack
Vanilla JavaScript (ES6+), HTML5 Canvas 2D. No framework, no bundler.
Source: `sandcastle_iso2.html` (single file).
Build output: `public/index.html` (generated, gitignored, never hand-edit).

## Repo
https://github.com/Productionboyz-hub/Sand-Castle-Crashers

## Live URL
https://sand-castle-crashers.athleticsouthla.workers.dev
This is the ONLY live URL. GitHub Pages is disabled deliberately.

## Hosting & deploy
Cloudflare Worker (`sand_castle_worker.js`) serving static assets from
`./public` via the ASSETS binding. Config: `wrangler.toml`.

Deploy command: `.\deploy_scc.ps1`  (no arguments)
Commit and push BEFORE running it - the script refuses a dirty tree.

The script is the only way to produce a build. It stamps the git short SHA
into the body at two injection points, deploys, then reads the served body
back and verifies both stamps match. Served path == build output path.

## Target devices
Primary: <TBD - phone or iPad; primary result is authoritative on disagreement>
Secondary: <TBD>

## Saves
<TBD - localStorage or none. Determines whether WORKFLOW sec.8 migration rules
apply at all.>

## Performance budget
<TBD - e.g. "60fps with N active enemies on primary device." Measured on
device, checked at each golden promotion.>

## Origin
Ported from an earlier prototype, SANDS OF FATE, which established the enemy
roster and core gameplay concepts.

## Where else to look
Current version, golden, rollback, backlog -> STATE.md
Process, receipts, device-pass rules -> WORKFLOW.md
