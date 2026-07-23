# SANDCASTLE CRASHERS — WORKFLOW BLUEPRINT

Governing process doc. Written from the ASL soccer-app postmortem. Every rule here exists because its absence cost a session, a version, or live data.

Read order for any fresh chat: **CONTEXT.md → STATE.md → this doc.**

---

## 0. ITEM ZERO — collapse the context docs (do this before any code)

Right now the project has three docs: `sandcastle-crashers-context.md`, `-context-1.md`, `-context-1-1.md`. Two of them are wrong and you don't know which two. This is precisely how the soccer app lost time: a doc that was true at v170 still read as authoritative at v330 and quietly misdirected every fresh session.

**Do now:**
1. Read all three. Merge into ONE `CONTEXT.md`.
2. Delete the other two from the project. Not rename, not archive-in-place — delete. Git keeps history if you want it.
3. Never create `-1`, `-copy`, `-final`, `-v2`. One filename per role, forever, rewritten in place.

---

## 1. DOCUMENT ARCHITECTURE — exactly three docs, no overlap

| Doc | Contains | Changes | Rule |
|---|---|---|---|
| `CONTEXT.md` | What the game is, repo URL, live URL, stack, hosting, target devices, core design pillars | Rarely | **Zero version numbers. Zero state.** If it can go stale, it doesn't belong here |
| `STATE.md` | Current version, commit SHA, golden build, rollback tier, live receipt, open backlog, next action | Every session | The ONLY source of truth for "where are we" |
| `WORKFLOW.md` | This doc — process, receipts, device-pass rules, anti-patterns | Rarely | Amended only after a new failure teaches something |

**The no-duplication law:** no fact appears in two docs. If a version number, filename, or URL is written in two places, one of them will eventually be wrong and you won't know which. When in doubt, a doc points at `STATE.md` instead of restating it.

**Staleness audit:** at every golden promotion, re-read `CONTEXT.md` and `WORKFLOW.md` for anything the promotion falsified. Fix immediately, in the same session. A stale doc is a defect with a long fuse.

---

## 2. ROLES — unchanged, and non-negotiable

- **This chat** — tech lead, architect, approvals gatekeeper. Writes specs and reviews diffs. Does not build.
- **Claude Code** — builder. Diagnoses, then implements approved diffs. Nothing else.
- **You (J)** — shuttle prompts, approve every diff, run every test.

**Builder test claims are invalid.** If Claude Code says "verified working," that is an assertion, not evidence. The only valid test result is one you ran yourself and can screenshot. This rule cost the soccer app a fake-green device pass; don't relearn it.

---

## 3. REPO LAYOUT — split from day one

The soccer app was a 1.1MB single HTML file for 300+ versions, then the split at v330 introduced a pipeline bug that silently served frozen code for every deploy after it. Start split, and prove the pipeline once, on day one, before there's anything to lose.

```
/src/            ← all source. Every edit happens here.
  /systems/      ← game logic modules (spawn, pathing, economy, waves)
  /data/         ← balance & content as DATA, not code (see §8)
  /render/
/build.ps1       ← concatenates/bundles src → dist
/dist/           ← build output. NEVER hand-edited. Gitignored or clearly marked generated.
/_archive/       ← superseded goldens. Nothing live ever lives here.
CONTEXT.md  STATE.md  WORKFLOW.md
```

**Hard rules:**
- Edits in `src/` only. Never in `dist/`. Never in a monolith.
- One build command. If there are two ways to produce a build, they will diverge.
- **Serve `dist/` and only `dist/`.** Verify on day one that the deployed path is the build output path. The soccer app's config pointed at repo root while the build wrote to `dist/` — every deploy for ~10 versions served frozen code while reporting the new version number. Prove this once, now, with a deliberate visible change.
- Build script normalizes line endings (LF). CRLF drift makes every future golden diff a whole-file false positive.

---

## 4. THE LOOP — every change, no exceptions

1. **Diagnose** — Claude Code reports what the code actually does before proposing anything. Scope claims verified by grep, not asserted.
2. **Diff reviewed in this chat** — full diff pasted verbatim, not summarized.
3. **Explicit approval** — with any riders attached to the diff itself, not to a separate message. Riders travel with the diff or they get lost.
4. **Build** — `build.ps1`, syntax check, validators.
5. **Receipt** — see §5. Not a claim. A receipt.
6. **Device pass** — you, on the target device. See §7.
7. **Promote or roll back** — green promotes to golden; anything else rolls back to the prior golden.

Skipping step 1 is what produces "fixes" that address a symptom's neighbor. Skipping step 5 is what produces a version number with no build behind it.

---

## 5. RECEIPTS — the lesson that cost the most

**Definition: a receipt is proof derived from the artifact itself. Anything a human or a tool typed by hand is a claim.**

The soccer app used a version header for months. It was a hardcoded string in the worker config, set independently of which build actually shipped. It read v331 while serving v321 content. It was a claim wearing a receipt's clothes.

**Receipt design for this project — build it before the first deploy:**

1. `build.ps1` injects, at build time, from git: the short commit SHA + build timestamp + version.
2. That stamp is written into the **bundle body**, not a header or a config file. It appears in at least two places: an HTML comment and a visible in-game build label (title screen corner is fine).
3. The deploy receipt is a **grep of the served body**:
   ```
   curl -s "https://<live-url>/?cb=$(date +%s)" -H "Cache-Control: no-cache" | grep -oE '<!-- build [a-f0-9]{7} -->|>build [a-f0-9]{7}<'
   ```
   Must return **two lines, both showing the intended commit SHA**. One line = the other injection point is broken. Wrong SHA = you did not deploy what you think you deployed.
4. Check cache status on any mismatch: cache HIT with a stale SHA → wait and re-curl. Cache MISS with a stale SHA → real origin problem, **stop, do not proceed to device pass.**

**Corollary:** the stamp must come from git, never typed. A hand-typed version can be typed while the wrong file ships. A commit SHA cannot.

---

## 6. VERSIONING, GOLDEN, ROLLBACK

- **Golden** = the last build that passed a full device pass *on actually-served content*. Recorded in `STATE.md` with version, commit, tag, and body-receipt SHA.
- **Rollback tier** = the previous golden. Always exactly one. Known-good, one command away.
- Tag every golden (`v12-stable`). Untagged goldens are rumors.
- **Never promote on a receipt you didn't verify.** The soccer app minted a golden that certified the *previous* version's behavior by accident, because the served body was frozen. It wasn't corrupt, but it was meaningless.
- Superseded goldens move to `_archive/`. Nothing live shares a directory with something dead.

---

## 7. DEVICE PASS

**Target devices:** define in `CONTEXT.md`. Name one **primary** — the one whose result is authoritative when devices disagree.

**Item zero, every pass involving persisted data:** back up the save file, and count/record the save state *before* you start. Name any throwaway entity explicitly before creating it, so you know exactly what to delete after. The soccer app learned this from an archive-touching batch where nobody knew the before-count.

**Rules:**
- Test the actual served build, not a local build. They are different artifacts until proven identical.
- **Stop and report on any unexpected result.** Never retry silently. A retry that works hides an intermittent bug — the worst kind in a game with a simulation loop.
- Screenshots over pasted console dumps (cheaper on context, and harder to fake).
- Cold start counts. Test after a hard reload with cleared cache, not just warm.
- Write the pass as numbered steps *before* running it. A pass you improvise is a pass you can't repeat.

---

## 8. GAME-SPECIFIC HAZARDS (the ones a web app doesn't have)

**Balance data is data, not code.** Tower costs, enemy HP, wave composition, damage curves → `src/data/*.json`. Tuning must never require a code diff, a syntax check, and a full validation loop. This is the single highest-leverage decision for a tower-defense build; it converts most of your future changes from engineering into editing.

**Fixed-timestep simulation, decoupled from render.** Game logic advances in fixed steps; rendering interpolates. Frame-rate-dependent logic means the game plays differently on your phone than your desktop, and every balance number becomes device-specific. Non-negotiable, and near-impossible to retrofit.

**Seeded RNG.** All randomness goes through one seeded generator. A bug you can't reproduce is a bug you can't fix; with a seed, "wave 14 on seed 8823" is a reproducible test case.

**Save schema versioning from save #1.** Every save carries `schemaVersion`. Loaders handle every prior version or refuse to load and say why. Silent partial loads corrupt saves.

**Save migration = copy, never move.** Direct inheritance from the soccer app's worst defect class:
- Never delete-then-recreate. A delete-then-re-add pattern in the soccer app had a window where a seed function fired into the gap and re-created a record with a garbage ID. That is live data loss, not a design smell.
- Migration completeness is tracked by an explicit **marker**, never by "is the target empty." An empty target and a not-yet-migrated target look identical, and any seeding logic will helpfully fill it in for you.
- Migrations must be idempotent — re-running produces the same result. Half-failure then resumes safely on next load.
- Any seed/default-population routine is **gated on the migration marker.**

**Performance budget, stated in `CONTEXT.md`.** e.g. "60fps with 200 active entities on [primary device]." Measured on device, not desktop. Check it at each golden promotion, not at the end.

**Async operations get visible feedback, tied to the FULL operation.** The soccer app shipped a spinner that hid ~2s before the operation actually finished, leaving a dead gap where the app felt broken. Feedback ends when the *last* step completes — including re-render — not when an inner await resolves.

---

## 9. BATCH DISCIPLINE

- **~5 changes per batch.** Larger batches make failed device passes un-bisectable.
- **Scope-contained.** Backlog items not named in the batch are not touched. If the builder finds something adjacent and tempting, it goes to backlog — it does not go in the diff.
- Anything with a large blast radius (save format, core loop, build pipeline) ships **alone**, with its own device pass.
- Big features need full session headroom. Don't start one with a quarter tank of context.

---

## 10. BACKLOG FORMAT

Numbered, permanent IDs, in `STATE.md`:

```
#7  [SEV] Short title
    Repro: exact steps
    Expected / Actual:
    Root cause: (blank until diagnosed — never guess in writing)
    Status: open | designed | in-batch-v14 | fixed-unverified | verified
```

`fixed-unverified` is a real status and matters. Nothing is `verified` without your device pass.

---

## 11. SESSION HANDOFF

Last thing every session, rewrite the top of `STATE.md`:

```
## STATE — <date>
Live: v__ (commit ___), body receipt verified: yes/no
Golden: v__ (tag ___)     Rollback: v__ (commit ___)
Last device pass: <date>, <device>, GREEN/RED, steps run
Backlog changes: opened #__, closed #__
NEXT ACTION: <one sentence, specific enough to start cold>
```

Context budget is a hard constraint. A session that ends without a handoff wastes the next session's first twenty minutes rediscovering where you were.

---

## 12. ANTI-PATTERN QUICK LIST

Each of these is a real soccer-app defect, generalized:

| Anti-pattern | Rule |
|---|---|
| Hand-set version header treated as deploy proof | Receipts come from the artifact (§5) |
| Build writes to one path, server reads another | One build output, one served path, proven day one (§3) |
| Delete-then-re-add a record | Update in place; never open a window for a seeder to race into (§8) |
| "Is it empty?" as a migration check | Explicit marker (§8) |
| Static check treated as behavior proof | "The code exists" ≠ "it works on device" (§7) |
| Builder reports its own test as passing | Coach-run passes only (§2) |
| Three docs with near-identical names | One filename per role (§1) |
| Spinner tied to an inner await | Feedback ends when the operation ends (§8) |
| Approval rider sent separately from the diff | Riders travel with the diff (§4) |
| Balance change requires a code deploy | Balance is data (§8) |

---

## 13. FILL THESE IN (before first build)

These are unknowns from my side — answer them in `CONTEXT.md`:

1. Stack — vanilla JS + Canvas? A framework? (Note: the soccer app's no-JSX-served constraint was device-specific to that app; it does not automatically apply here — but decide deliberately, don't inherit by accident.)
2. Hosting + deploy command.
3. Target devices, and which is primary.
4. Where saves live — localStorage? IndexedDB? Server? This determines the whole §8 migration story.
5. Performance budget number.

---

*Amend this doc only when a new failure teaches something. Every rule above is paid for.*
