<p align="center">
  <img alt="Vibe Walk — earn the tour first, then generate an instrumented spotlight walkthrough" src="https://626labs.dev/assets/brand/plugins/vibe-walk-banner-1500x500.png" />
</p>

# Vibe Walk

**Reads your app's user-facing surfaces, decides whether a spotlight tour is worth building, and — when it is — generates a short, instrumented, replayable Driver.js tour with a human-gated anchor pass.**

[![stable](https://img.shields.io/github/v/tag/estevanhernandez-stack-ed/Vibe-Walk?label=stable&color=17d4fa)](https://github.com/estevanhernandez-stack-ed/Vibe-Walk/tags)

## What it does

Most onboarding tools assume a tour is always the answer. Vibe Walk does not — it earns the tour first.

- **An honest build/don't-build verdict, as a first-class output.** "Don't build a tour here" is weighted the same as "build one." A tour layered on an already-intuitive UI trains users to dismiss future guidance. A tour on a blank-canvas first-run surface has lower ROI than fixing the empty state. A power-user tool doesn't need a spotlight tour at all. The plugin checks for these conditions and tells you honestly — that's what makes the "build" verdict trustworthy when it comes. Sherpa, the Vibe Walk persona, is a guide who will recommend against the summit when the conditions are wrong.
- **Names the aha moment.** The single action that makes a new user say "this is worth it." Step 1 of any built tour routes here.
- **Generates onboarding only when it earns one.** When the verdict is `build`, you get a drop-in, instrumented, replayable Driver.js spotlight tour — you own the emitted code, same model as shadcn.
- **A human-gated anchor pass.** Stable `data-tour` selectors are auto-injected only where it's provably safe; everything ambiguous halts for your review.
- **A 6-event analytics adapter.** Wired into your existing analytics system, measuring downstream activation — not tour completion, which is a trap metric.
- **Walkthrough vs training mode.** Walkthrough ships in v1; training mode is architecturally distinct and deferred to v2 (see scope below).
- **Reuses your existing first-run state.** The tour queues behind whatever else already fires on first login — it doesn't stack on top.

## How it works

### Phase 1 — discover (autonomous)

Run `/vibe-walk:discover` in the target app's repo. The plugin reads, entirely on your codebase:

- Orientation docs (README, DOCS, CLAUDE.md, THEME)
- The route surface
- Page files and their component composition
- Existing onboarding / tour / tooltip code

It produces a real verdict before anything is built:

1. A product summary and audience read (B2C / B2B / technical) — this sets the copy register.
2. A user-facing surface inventory: panels, regions, tabs, modals, floating widgets.
3. A named aha-moment candidate — the action that makes a new user say "this is worth it." Step 1 of any built tour routes here.
4. A ranked shortlist of 8–12 candidate stops, ranked by centrality to first success.
5. An anchor-readiness verdict: are there stable selectors (`id`, `data-*`) to anchor to, or is this an anchor-pass job first?
6. **The verdict** — `build` / `don't-build` / `cheaper-first (add empty-state or sample-data)`. Never buried, always presented with equal weight.

Phase 1 asks you nothing. The verdict lands; you decide.

### Phase 1.5 and Phase 2 — walk (five interview gates, then build)

Run `/vibe-walk:walk`. The substrate decision tree resolves before any question is asked — the plugin never asks what it can already determine. Five gates, kept separate:

1. **Mode** — walkthrough (v1, built) vs training (v2, deferred).
2. **Trigger model** — auto-once + replay (default), on-demand, or auto-once no-replay. Includes a sub-question about what else fires on first login — the tour queues behind it, not on top.
3. **Substrate** — Driver.js by default; the tree routes to React Joyride, Reactour, or NextStep.js when the app warrants it. Intro.js is not available (AGPL-3).
4. **Aha moment** — confirm Phase 1's candidate. This becomes step 1.
5. **Primary user role** — for role-diverse products, may branch into two tours.

After the five gates, the plugin builds:

- **Tour module** — a drop-in Driver.js module (default): a `spotlightSteps.ts` config array and a `spotlightTour.ts` runner with `start(onDone)`, SSR guard, progress indicator ("3 of 5"), and persistent replay export. You own the code — same model as shadcn. Steps are capped at 5 (default 3–4); the plugin warns and asks for approval before exceeding that.
- **Anchor-injection pass** — `data-tour="<kebab-semantic-name>"` attributes added to the relevant components via a jscodeshift codemod. The codemod auto-injects only the provably safe subset (intrinsic HTML tags, directly-imported named components, single unambiguous root return, no HOC / dynamic / render-prop, idempotent). Everything else goes into `REVIEW_NEEDED.md` with a per-item reason code. Phase 2 halts until you resolve that list.
- **Analytics wiring** — six events bound to Driver.js substrate hooks, emitted into your existing analytics system: `tour_started`, `tour_step_viewed`, `tour_step_advanced`, `tour_skipped`, `tour_completed`, `tour_replayed`. A `TOUR_ANALYTICS.md` is generated naming the events, the host activation event, and the 7d/14d attribution windows. The success criterion is downstream activation, not tour completion — the latter is a trap metric.
- **Replay entry point** — persistent, ungated, zero-hunt. Tours that can't be replayed lock out the users who dismissed in the first four seconds.

**The 5-step guardrail, stated honestly:** completion drops sharply past 5 steps. The shape of that curve is consistent across sources and grounded in cognitive-load theory, but the specific numbers come from a single vendor's platform data and have not been independently replicated. The guardrail sits conservatively below the observed cliff — treat it as directional, not a proven constant.

### Commands

| Command | What it does |
|---|---|
| `/vibe-walk` | Bare router — reads project state, recommends the next step, asks before launching. First run hands off to bootstrap. |
| `/vibe-walk:discover` | Phase 1 autonomous discovery + the build/don't-build verdict. |
| `/vibe-walk:walk` | Phase 1.5 interview gates + Phase 2 build. Reads the discovery verdict; on non-`build` verdicts, surfaces the read and asks once before proceeding — advisory, not gating. |
| `/vibe-walk:vitals` | Structural self-test — checks plugin.json, all nine SKILLs, all scripts, guide references, and friction-trigger wiring. Read-only. |
| `/vibe-walk:evolve-walk` | L3 self-evolution — reads session + friction logs and proposes improvements to the plugin. Never auto-applies. |

## Validated on

Celestia3 — cycle #16, A/B against the hand-built version.

## Install

**Stable (recommended) — as a Claude Code plugin via the marketplace:**

```text
/plugin marketplace add estevanhernandez-stack-ed/vibe-plugins
/plugin install vibe-walk@vibe-plugins
```

**Canary — track this repo's `main`:**

```text
/plugin install vibe-walk@estevanhernandez-stack-ed/Vibe-Walk
```

## v1 scope and what's deferred

**v1 (this release):**
- Walkthrough mode — a short, skippable, instrumented spotlight tour.
- Drop-in module output (Shape A) — you own the emitted TypeScript.
- Web only — the anchor contract requires DOM selectors.
- Driver.js as the default substrate; decision-tree overrides to React Joyride, Reactour, NextStep.js.

**Deferred to v2:**
- Training mode — objectives, exercises, quizzes, role gates. Architecturally distinct from walkthrough; not a v1 extension.
- Config-only JSON output (Shape B) — emitted only when a non-developer owns the ongoing tour-content editing cycle, driver.js is pinned, and updates decouple from deploy. Not built; not a co-equal default mode.
- Non-web platforms (desktop-native, mobile-native, CLI).
- Cross-view orchestration — v1 default is single-view tours.

## No telemetry, self-evolving

All session and friction logging is local-only under `~/.claude/plugins/data/vibe-walk/`. Nothing leaves the machine. Vibe Walk uses that local log to self-evolve — `/vibe-walk:evolve-walk` reads session + friction history and proposes improvements to itself, never auto-applying. You can inspect or delete the directory at any time; the plugin will still function, it just loses its session memory for self-evolution.

## Part of the Vibe ecosystem

Part of the **[Vibe Plugins](https://github.com/estevanhernandez-stack-ed/vibe-plugins)** marketplace from [626 Labs](https://626labs.dev) — foundations and process pillars for AI-assisted creation.

```text
/plugin marketplace add estevanhernandez-stack-ed/vibe-plugins
```

## License

MIT — *Imagine Something Else.*
