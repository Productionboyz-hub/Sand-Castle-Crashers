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

## Art direction
Scope of the reference (DECIDED): Sand Castle Crashers is a defense
game. The Sandcastle (Bubblebird Studio) reference governs art
direction only - palette, lighting, tide and surf polish, decor,
washed-ashore collectibles. It does not govern design intent. Waves,
piece decay, enemies, castle HP and the loss condition all stay.
Where the reference's calm-sandbox feel conflicts with combat
readability, readability wins - see the contrast budget below.

Reference target: soft, sun-bleached, low-saturation tropical beach.
Saturation is spent almost entirely on water; sand and castle stay
pale and warm.

Lighting (locked - every sprite and every draw call obeys this):
- Sun from upper LEFT, warm. Shadows fall on RIGHT faces.
- Shadowed faces take a faint cool blue tint (sky bounce), not just a
  darker version of the lit color.
- Every piece and entity gets a soft blurred elliptical contact
  shadow, warm grey-brown at ~20% alpha. Never black.
- No hard outlines. Soft, rounded edges.

Palette:
  Dry beach sand   #EDDFC4  sun-lit #F7ECD8  shadowed #CBB795
  Wet sand band    #C2A47E  deepest (foam edge) #A6875F
  Castle piece     lit #EFE0C4  top #E2CFAC  shadow #C2A87F
                   crevice #A98D66
  Water            shallow #7FD4C8  mid #35A8A8  deep #1C6E7E
  Foam             #FFFFFF at 70-85% alpha, breaking edge #EAF7F4
  Contact shadow   #8A7355 at ~20% alpha
  Decor accents    driftwood #A98763  seaweed #4F7A55
                   shell #F5E6DE  pebble #9AA3A0

Castle sand sits slightly cooler and darker than dry beach sand, or
the castle loses separation from the ground.

Contrast budget: the environment stays soft and low-contrast. All
contrast is reserved for interactive and threatening elements -
enemies, damaged pieces, placement feedback - so pillar 4 (readable
at a glance in portrait) survives the softer palette.

Sprite generation: pieces are generated externally as isolated PNGs
with transparent backgrounds, 2:1 dimetric, matching the lighting
rules above. No ground, no base, no cast shadow baked in - contact
shadows are drawn at runtime.

## Stack
Vanilla JavaScript (ES6+), HTML5 Canvas 2D. No framework, no bundler.
Source: `sandcastle_iso2.html` (single file).
Build output: `public/index.html` (generated, gitignored, never hand-edit).

## Repo
https://github.com/Productionboyz-hub/Sand-Castle-Crashers

## Live URL
https://sand-castle-crashers.athleticsouthla.workers.dev
This is the ONLY live URL. GitHub Pages is deliberately disabled - it was
found LIVE on 2026-07-23 serving repo root, and disabled at source
(branch -> None). Unpublishing alone does not prevent rebuild. Re-verify
it 404s after any push that could rearm it.

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
