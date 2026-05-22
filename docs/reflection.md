# Reflection — Vibe-Walk (Cart cycle #16)

> Closed 2026-05-22. Builder: Estevan (architect persona, fully-autonomous). First 626Labs marketplace plugin born from a research swarm. From a faulty memory note ("vibe-spotlight") to the 10th plugin in the family, in one session.

## What landed

- **A working, published plugin.** Vibe-Walk v0.1.0 — canary (solo GitHub repo) + stable (marketplace.json entry). 197 tests (174 Python + 23 JS), plugin-validator PASS.
- **The differentiator first.** M1 — autonomous discovery + a first-class "should we build a tour?" verdict — was built before anything else, per the research seed's #1 recommendation. A tour vendor would never ship the willingness to say "don't build one"; that's the trust spine.
- **Research-seeded, not vibe-seeded.** A personified research tree (Sherpa director + 6 wave-1 researchers + 3 wave-2 deep-dives) produced `_seed.md` — 12 resolved decisions with sourced evidence — before the grand plan. The plugin's design rests on the field's best patterns, not just our one Celestia3 cowpath.
- **Dogfooded on a real app, end to end.** Ran the plugin against Celestia3, generated a tour, wired it in (PR #16), and rendered the actual spotlight. The hand-built tour (PR #12) is the A/B baseline.

## What the review gates caught (and why they earned their keep)

This cycle is a clean argument for layered verification — each gate caught something the prior layer couldn't:

1. **The plugin-validator caught the integration seam.** All 7 milestones built their scripts in isolation with green tests, but the `walk` orchestrator only invoked `emit_module` — it never wired the anchor codemod or analytics, and the hand-off *lied* that analytics was "the only remaining step." Tests were green; the plugin didn't actually work end to end. Fixed by wiring M4+M5 into Phase 2.
2. **The dogfood caught a P0 the 197 tests missed.** `build_verdict` returned `don't-build` on Celestia3 — the differentiator getting the differentiating call *wrong on its own reference app* — because the "existing onboarding" signal conflated a signup/intro flyby with a redundant dashboard tour. Fixtures were clean; the real app was messy. Split `existing_tour` from `existing_intro_flow`; pinned a regression test to the exact Celestia3 case.
3. **Manual verification caught stale artifacts + a jest mis-config.** The saved dogfood output was pre-ordering-fix (aha-first); regenerated. Bare jest mis-collected `.jsx` fixtures as failed suites; fixed `testMatch`.
4. **The builder caught the missing capability.** "Wire the generated tour — that should be part of the plugin" exposed that the plugin dropped files but never wired the *trigger* (flag + auto-fire + replay). Became M7.

The through-line: **structural green ≠ works.** Every real defect this cycle lived in the gap between "tests pass" and "runs on a real app." Same lesson as the Celestia3 tour that started all this.

## What to tighten next time

- **Wire as you build, don't integrate at the end.** Milestones M1-M6 each built + tested a script in isolation; the `walk` orchestrator fell behind, so M3-M5 shipped scripts the live flow never called. A per-milestone "is this invoked by the flow yet?" check would have caught it before the validator did.
- **Regenerate saved artifacts when the generator changes.** The dogfood output went stale the moment the ordering fix landed; nothing forced a refresh. Treat generated-sample dirs as build outputs, not commits.
- **Dogfood earlier.** The P0 verdict bug existed from M1; it surfaced only at the dogfood gate near the end. A "run discovery against one real app" check right after M1 would have caught it 5 milestones sooner.
- **The step-ceiling evidence is still single-vendor.** Carried honestly into the plugin's copy, but it remains the weakest claim in the seed. Worth independent corroboration before v1.0.

## How we worked

- **Cowpath-first, then research-seed.** Did one real job by hand (the Celestia3 tour), captured the pattern, then ran a research swarm to harden it before formalizing via Cart. The combination — lived experience + field research — produced a far stronger spec than either alone.
- **Subagent-driven TDD throughout.** Fresh implementer per milestone, controller review between. When the platform threw 529s on subagent spawn, fell back to inline building (M0) without losing the thread — agents are a tool in the kit, not a dependency.
- **Fully-autonomous with phase checkpoints.** The builder set direction at forks (scope narrowings, ordering rule, publish gate) and let the chain run between. Trust-on-shape held.
- **Honest reporting over momentum.** Surfaced the P0, the stale artifacts, the lying hand-off, the platform 529s — none buried under the win. The dogfood "failure" was the cycle's best moment.

## Status

Cycle #16 closed. Vibe-Walk v0.1.0 live in the marketplace (canary + stable). Celestia3 generated-tour PR #16 open as the dogfood A/B vs the hand-built #12. v2 backlog: training mode, config-only output, non-web platforms, cross-view orchestration, independent corroboration of the step-ceiling.
