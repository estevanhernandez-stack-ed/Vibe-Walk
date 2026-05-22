# Scope — Vibe-Walk

> Compressed /scope (pattern mm): the idea is fully formed upstream. This adopts, not re-derives.
> Source of truth: `docs/inputs/research/_seed.md` §3 + `docs/inputs/2026-05-21-vibe-walk-grand-plan.md`.

**What we're building:** a Claude Code plugin (vibe-* family) that autonomously reads an app's user-facing surfaces, decides whether an onboarding tour is even warranted, and when it is, generates a short, instrumented, replayable Driver.js spotlight tour with a human-gated anchor-injection pass.

**The reframe that defines the scope:** "don't build a tour" is a first-class output. The plugin earns the tour before building it.

**In scope (v1):**
- Phase 1 autonomous discovery + the "should we build a tour?" verdict.
- Phase 1.5 interview gates (mode, trigger, substrate, aha, role).
- Phase 2 build: drop-in Driver.js tour module, anchor codemod, analytics wiring, replay.
- vibe-* self-evolution scaffolding (session-logger, friction-logger, evolve-walk).

**Out of scope (v2+, locked this session):**
- Training mode (B2B curriculum) — routed at the mode gate, not built.
- Config-only JSON output (Shape B) — gated exception, deferred.
- Non-web platforms (desktop/mobile-native/CLI).
- Cross-view tour orchestration.

**Success:** a marketplace-ready plugin that, on a real app, produces either a good tour or an honest "don't build one" — grounded in the research seed. First dogfood: re-generate the Celestia3 tour through the plugin and compare to the hand-built one.
