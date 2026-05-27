# Vibe-Walk

> **Persona:** This repo inherits **The Architect** from `~/.claude/CLAUDE.md`. No need to re-establish — just adds project context below.

Vibe-Walk is a Claude Code plugin (10th in the Vibe family). It reads a host app's user-facing surfaces, returns an honest **build / don't-build / cheaper-first** verdict, and — when the verdict is `build` — emits a short, instrumented, replayable Driver.js spotlight tour with a human-gated anchor pass. **Earning the tour is the differentiator.** A tour vendor would never ship the willingness to say "don't build one"; that is the trust spine.

## Tech Stack

- **Languages:** Python 3.13 (discovery + emitters) and Node.js (jscodeshift codemod + tour-module fixtures).
- **Tests:** `pytest` (Python, 174+ tests under `tests/`) and `jest` (JS, 23+ tests under `plugins/vibe-walk/scripts/anchors/__tests__/` — `testMatch: **/__tests__/**/*.test.js`, intentionally narrow so `.jsx` fixtures aren't collected as suites).
- **Plugin substrate:** Markdown SKILLs under `plugins/vibe-walk/skills/`, manifest at `plugins/vibe-walk/.claude-plugin/plugin.json`, scripts under `plugins/vibe-walk/scripts/`.
- **Emitted tour stack:** Driver.js (default substrate, MIT) → TypeScript module (`spotlightSteps.ts` + `spotlightTour.ts`). Override substrates: React Joyride, Reactour, NextStep.js. **Intro.js is never an option** (AGPL-3 license poison for host apps).
- **Distribution:** Canary via this solo repo, stable via [`estevanhernandez-stack-ed/vibe-plugins`](https://github.com/estevanhernandez-stack-ed/vibe-plugins) marketplace.

## What's where

| Path | What it is |
|---|---|
| `plugins/vibe-walk/.claude-plugin/plugin.json` | Plugin manifest (name, version, marketplace voice description). |
| `plugins/vibe-walk/skills/` | Nine SKILLs: `vibe-walk` (bare router), `bootstrap`, `discover` (M1, Phase 1), `walk` (M2, Phase 1.5 + Phase 2), `vitals`, `evolve-walk`, `guide` (non-invocable shared behavior), `session-logger`, `friction-logger`. |
| `plugins/vibe-walk/skills/guide/references/` | The contract source: `sherpa-persona.md`, `posture.md`, `conventions.md` (the D1–D6 build constraints), `friction-triggers.md`. **Read `conventions.md` before changing anything in the emitters or codemod.** |
| `plugins/vibe-walk/scripts/discovery/` | Phase 1 readers: `inventory_surfaces.py`, `anchor_readiness.py`, `build_verdict.py`. |
| `plugins/vibe-walk/scripts/build/` | Phase 1.5 + 2 emitters: `substrate_tree.py`, `emit_tour_module.py`, `emit_analytics.py`, `emit_trigger_wiring.py`. |
| `plugins/vibe-walk/scripts/anchors/inject_anchors.js` | The 4-gate jscodeshift anchor-injection codemod (D6). Auto-inject is conservative by design; everything ambiguous halts via `REVIEW_NEEDED.md`. |
| `tests/` | Python tests + fixtures. `fixtures/` includes `tour_worthy_app`, `single_purpose_tool`, `no_selectors_app`, `blank_canvas_app` — the four verdict shapes the discovery layer must call correctly. |
| `docs/` | Cart-cycle artifacts: `scope.md`, `prd.md`, `spec.md`, `checklist.md`, `reflection.md`, `builder-profile.md`. |
| `docs/inputs/` | The cycle's research corpus — grand plan, seed, and 6 personified researcher write-ups under `research/findings/`. **The seed (`docs/inputs/research/_seed.md`) is the source of decisions D1–D6.** |
| `docs/dogfood/` | Celestia3 dogfood A/B reference and `celestia3-output/` (a generated artifact — regenerate; do not hand-edit). |
| `.mcp.json` | Project-scoped 626Labs MCP binding (decisions log, project context). |
| `.claude/` | Local Claude Code settings only — no project-pinned agents yet (see Step 5 proposals). |
| `.vibe-walk/` | **Gitignored** runtime state written by the bootstrap SKILL (`config.json`). |

## How the plugin works at runtime

Three phases, kept structurally separate so the discovery verdict is trustworthy before any code is generated:

### Phase 1 — discover (autonomous, no questions)

`/vibe-walk:discover` runs the discovery scripts against the host app's repo. `inventory_surfaces.py` reads the route + page surface; `anchor_readiness.py` scans for stable selectors (`id`, `data-*`) vs class-name anchoring (forbidden by D4); `build_verdict.py` weights the signals and returns one of: `build`, `don't-build`, `cheaper-first` (with the suggested cheaper move, e.g., fix the empty state instead). The named **aha moment** rides alongside the verdict — Step 1 of any built tour routes there.

### Phase 1.5 — walk gates (only when verdict = `build`)

Five gates, resolved by the substrate decision tree before being asked — the plugin never asks what it can already determine. Order: mode (walkthrough v1 vs training v2 deferred) → trigger model → substrate (D3) → aha-moment confirmation → primary user role.

### Phase 2 — emit + inject + wire

`emit_tour_module.py` writes the drop-in TypeScript module (Shape A — "you own the code"). `inject_anchors.js` runs the 4-gate codemod (D6) — auto-injects only the provably safe subset, routes everything else to `REVIEW_NEEDED.md` and **halts the build** until the human resolves it. `emit_analytics.py` wires the six-event schema (D5) into the host's analytics system and writes `TOUR_ANALYTICS.md` naming the host activation event + 7d/14d attribution windows. `emit_trigger_wiring.py` wires the flag + auto-fire + replay (M7).

### Commands

| Command | What it does |
|---|---|
| `/vibe-walk` | Bare router. Reads `.vibe-walk/` state, recommends next step, hands to bootstrap on first run. |
| `/vibe-walk:discover` | Phase 1 — autonomous discovery + verdict. |
| `/vibe-walk:walk` | Phase 1.5 gates + Phase 2 emit/inject/wire. Requires `build` verdict from discover. |
| `/vibe-walk:vitals` | Structural self-test. Read-only. |
| `/vibe-walk:evolve-walk` | L3 self-evolution. Reads `~/.claude/plugins/data/vibe-walk/` session + friction logs, proposes plugin improvements, never auto-applies. |

## Common tasks

| You want to… | Path / command |
|---|---|
| Run the full test suite | `npm test` (Python first, then JS). Individual: `npm run test:py`, `npm run test:js`. |
| Add a new emitter | New module under `plugins/vibe-walk/scripts/build/`, tests under `tests/`, wire it into `skills/walk/SKILL.md` Phase 2 — **don't skip the wiring step (see cycle #16 reflection)**. |
| Change a build constraint (D1–D6) | Edit `plugins/vibe-walk/skills/guide/references/conventions.md` first, then propagate to emitters. The conventions file is the spec; the code follows it, not the other way around. |
| Add a new substrate to the decision tree | `plugins/vibe-walk/scripts/build/substrate_tree.py` + tests in `tests/test_substrate_tree.py`. Check D3 license rules before adding (no AGPL-3). |
| Tighten / loosen the 4-gate anchor injection | `plugins/vibe-walk/scripts/anchors/inject_anchors.js` + JSX fixture in `plugins/vibe-walk/scripts/anchors/__tests__/` + test case in `inject_anchors.test.js`. Loosening means more auto-inject — argue the case in a decision log entry. |
| Add a verdict edge case | Add a fixture under `tests/fixtures/`, then a case in `tests/test_build_verdict.py`. The four canonical fixtures are pinned regression cases — extend, don't rename. |
| Cut a marketplace release | Bump `plugins/vibe-walk/.claude-plugin/plugin.json` version, tag the repo, bump the ref in the marketplace `marketplace.json`. **Verify `pwd` before running `git` / `gh` if you `cd`'d during the session.** |
| Inspect / wipe local plugin state | `~/.claude/plugins/data/vibe-walk/` (session + friction logs, local-only). |

## Conventions

- **Commits:** Conventional commits. Active types in this repo: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`. Scope on the plugin where it helps (`feat(vibe-walk/m4): …`, `fix(walk): …`).
- **Style — Python:** Standard 4-space indent, type-hinted public functions, narrow imports. Tests mirror module path under `tests/`.
- **Style — JS:** The codemod stays vanilla jscodeshift; no transpile step. Tests are plain `.test.js` under `__tests__/` so the narrow `testMatch` keeps fixtures from being mis-collected as suites.
- **SKILLs:** YAML frontmatter (`name`, `description`) is load-bearing. Keep the description specific enough that the SKILL-loader picks the right one — the `guide` SKILL is non-invocable and must say so in its description.
- **Generated artifacts are build outputs, not source.** `docs/dogfood/celestia3-output/` is regenerated by the plugin — refresh it, don't edit it. The same rule covers any `__pycache__/` and `.vibe-walk/` directories.
- **Anchor contract (D4) is non-negotiable.** Tour stops anchor on `data-tour="<kebab-semantic-name>"`. Class-name anchoring is forbidden (CSS Modules hashes + Tailwind utilities aren't stable). NextStep is the lone `id="tour-<name>"` exception, encoded in the substrate tree.
- **Honest evidence.** The 5-step cap (D1) cites curve direction + cognitive-load theory — not vendor-specific percentages. The plugin's credibility tracks the honesty of its claims; don't quietly upgrade weak evidence in copy or output.

## Decisions log

Significant decisions log to the **626Labs Dashboard MCP** via `mcp__626labs__manage_decisions` (HTTP server bound by `.mcp.json` at the repo root). Auto-bind at session start: read `git config --get remote.origin.url` → call `mcp__626labs__manage_projects` with `findByRepo` and the remote URL → bind silently on an exact match. Tag every decision with the bound project ID.

The bar: *would future-you (or someone asking "why this approach?") want to know this in 3–6 months?*

Especially:

- **Changes to D1–D6** (step cap, output shape, substrate defaults, anchor contract, analytics schema, anchor-injection boundary) — these are the load-bearing constraints. Any drift gets a decision.
- **Verdict-logic shifts** in `build_verdict.py` — e.g., the cycle-#16 split of `existing_intro_flow` from `existing_tour`. The differentiator must call the differentiating case correctly; record why a weighting changed.
- **New substrate added or removed** from the decision tree, with license check.
- **Auto-inject gate loosened or tightened** in the codemod — the 4-gate rule trades false positives for false negatives; every move on that dial is a decision.
- **Marketplace release decisions** — what shipped in a tag, what's deferred, why the version bump.
- **Momentous-hurdle moments** — when a wall was crossed that should have stopped the work (e.g., the P0 verdict bug surfacing at dogfood, post 197-green tests).

Skip the routine: ran tests, fixed typo, renamed a variable, updated a comment. If unbound (no project match): set `projectId: null` and tag with `vibe-walk` in the description.

For trajectory-level moves (training mode v2 scope, non-web platforms, marketplace strategy), also push to the dashboard's strategic Architect via `mcp__626labs__bridge_context_to_architect`.

## Knowledge & taste

The repo is the system of record. Tacit conventions worth preserving live here:

- **The build contract (D1–D6):** `plugins/vibe-walk/skills/guide/references/conventions.md`. Read first, then code.
- **The persona + posture:** `plugins/vibe-walk/skills/guide/references/sherpa-persona.md`, `posture.md`. Sherpa is the in-plugin voice — the Architect persona still applies to the repo work itself.
- **The research seed:** `docs/inputs/research/_seed.md` — 12 resolved decisions, sourced. The plugin's design rests on this, not on a single cowpath.
- **The cowpath:** `docs/dogfood/celestia3-dogfood.md` + the Celestia3 PRs (#12 hand-built, #16 plugin-generated) — the real-app A/B that grounds the discovery verdict.
- **What review caught:** `docs/reflection.md` (cycle #16 close) — four lessons about why structural-green ≠ works on a real app. The next cycle starts with these.
- **Things the agent kept getting wrong** in cycle #16 — record corrections here when they surface, instead of re-explaining them every session.

## What NOT to do

- **Don't ship Intro.js as a substrate.** AGPL-3 — license poison for the host app. If a user requests it, the right answer is "no — here's why," not a config flag.
- **Don't auto-inject `data-tour` outside the 4-gate.** D6 is conservative on purpose: false positives in the codemod corrupt the host's source. The build *should* halt at `REVIEW_NEEDED.md`; that halt is the safety guarantee, not friction to smooth away.
- **Don't anchor on class names.** D4. CSS Modules hashes and Tailwind utilities are not stable across builds. The only `id`-based exception is NextStep, encoded in the substrate tree.
- **Don't upgrade the 5-step evidence to fake precision.** The completion-cliff direction is well-supported; the specific percentages are single-vendor (Chameleon) and not independently replicated. Carry it honestly in copy and output.
- **Don't hand-edit `docs/dogfood/celestia3-output/`.** It's a generated artifact — when the emitters change, regenerate. The same rule covers `__pycache__/`, `node_modules/`, and `.vibe-walk/`.
- **Don't build a milestone's script in isolation without wiring it into the live `walk` flow in the same step.** Cycle #16 shipped M3–M5 scripts the orchestrator never called; the validator caught it, but the dogfood would have caught it sooner. **Wire as you build.**
- **Don't drift the version pair.** The plugin manifest version and the marketplace `marketplace.json` ref must move in lockstep when cutting a stable release. Drift = silent install confusion.
- **Don't leak telemetry.** All session + friction logging is local-only under `~/.claude/plugins/data/vibe-walk/`. No network calls; no analytics from the plugin itself. The README promises this.
- **Don't bury the don't-build verdict.** `don't-build` and `cheaper-first` are first-class outputs, weighted equally with `build`. Burying them collapses the trust spine.

## References

- Cycle reflection: `docs/reflection.md`
- Cycle artifacts: `docs/scope.md`, `docs/prd.md`, `docs/spec.md`, `docs/checklist.md`
- Grand plan: `docs/inputs/2026-05-21-vibe-walk-grand-plan.md`
- Research seed (source of D1–D6): `docs/inputs/research/_seed.md`
- Public README (marketplace copy): `README.md`
- Marketplace home: [estevanhernandez-stack-ed/vibe-plugins](https://github.com/estevanhernandez-stack-ed/vibe-plugins)
- Sibling Vibe plugins: vibe-cartographer (build), vibe-doc (docs), vibe-iterate (ship cycles), vibe-keystone (CLAUDE.md bootstrap), vibe-wrap (session close), vibe-thesis (writing), thesis-engine (research feeder)
