# Builder Profile

<!-- Autonomous /onboard run (Cart cycle #16). Returning builder; all values pulled from
     ~/.claude/profiles/builder.json (fresh, no decay) + this cycle's research seed. No interview. -->

## Who They Are
Estevan ("Mr. Solo Dolo"). Builder and outsider, runs 626Labs out of Fort Worth, TX. 20+ years PC/Windows experience. Vibe coder — architects and ships through AI agents rather than writing code directly. Has shipped ~10 deployed apps and seven Claude Code plugins to the 626Labs marketplace. Active Vibe Cartographer contributor. This is his 16th Cart cycle.

## Technical Experience
**Experienced.** Languages: TypeScript, Python, JavaScript, Luau, C#, HTML/CSS, C++. Frameworks: React 19, Next.js, Vite, TailwindCSS, Firebase, FastAPI, Flask, Express, .NET 8/9, Azure, Expo/React Native, Playwright, and the Windows app stack. AI-agent experience: deep — runs Claude Code as an autonomous build system with structured checklists and subagent delegation; built and shipped vibe-cartographer, vibe-doc, vibe-test, vibe-taker. No hand-holding needed.

## Mode
**Builder** (brisk). Autonomy: **fully-autonomous** (per unified profile). Build-mode preference: iterative-prototype. This cycle runs auto-style with checkpoints at phase boundaries (builder's Q3 choice).

## Project Goals
Build **Vibe-Walk** — a Claude Code plugin (vibe-* marketplace family) that autonomously reads an app's user-facing surfaces, decides whether an onboarding tour is even warranted ("don't build a tour" is a first-class verdict), and when warranted generates a short, instrumented, replayable Driver.js spotlight tour with a human-gated anchor-injection pass. v1 = walkthrough mode, drop-in module output, web only. Success = a plugin that earns the tour before building it, grounded in the research seed, ready to pin into the marketplace.

## Design Direction
Not a visual app — it's a CLI/markdown-driven plugin. Voice/persona is **Sherpa** (the guide who leads the walk), defined in the research seed. Output it generates must match each host app's look. Builder's creative sensibility (clean, functional, high-contrast, honest) governs the plugin's own copy — especially the honest framing of the step-count guardrail.

## Prior SDD Experience
Deep. 15 completed Cart cycles. Established pattern (mm): preps the spec upstream with an agent, then uses Cart to wrap up the build — so /scope, /prd, /spec compress to pointer-stubs against the prepped spec, and Cart's value lands at /checklist + /build. That pattern is in full force here: the research seed (`docs/inputs/research/_seed.md`) and grand plan (`docs/inputs/2026-05-21-vibe-walk-grand-plan.md`) are the upstream spec prep.

## Architecture Docs
**Yes — extensive, carried into `docs/inputs/`:**
- `research/_seed.md` — 12 resolved design decisions + GENERATE/ASK/AVOID + the plugin's three-phase shape.
- `2026-05-21-vibe-walk-grand-plan.md` — the master plan (7 milestones, file structure matched to the vibe-* convention, build constraints).
- `2026-05-21-vibe-walk-build-design.md` — the build design + the four locked decisions.
- `process-notes.md` (cowpath) — lessons from the inaugural Celestia3 spotlight tour.
- The full research corpus (6 Wave-1 findings + 3 Wave-2 deep-dives).
Structure follows the vibe-* convention (plugins/vibe-walk/skills/ + .claude-plugin/plugin.json), templated on vibe-iterate. `/spec` does not start from defaults — it adopts the grand plan.
