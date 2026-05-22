# Checklist — Vibe-Walk

> /checklist: M0 bite-sized for the current /build; M1-M6 carried at milestone level (bite-sized
> just-in-time per milestone). Full detail: `docs/inputs/2026-05-21-vibe-walk-grand-plan.md`.

## M0 — Repo + plugin scaffold (current /build target)

- [ ] **0.1** `plugins/vibe-walk/.claude-plugin/plugin.json` — name `vibe-walk`, marketplace-voice description, version 0.0.1.
- [ ] **0.2** `skills/guide/SKILL.md` + `references/sherpa-persona.md` (the guide who leads the walk; earn-the-tour, honest-evidence posture), `posture.md`, `conventions.md` (anchor contract D4, output conventions), `friction-triggers.md`. Template on vibe-iterate's guide.
- [ ] **0.3** `skills/vibe-walk/SKILL.md` — bare router: reads `.vibe-walk/` state, recommends next step, hands to bootstrap on first run. Template on vibe-iterate's bare router.
- [ ] **0.4** `skills/bootstrap/SKILL.md` — first-run config → `.vibe-walk/config.json`. Template on vibe-iterate's bootstrap.
- [ ] **0.5** `skills/session-logger/SKILL.md` + `skills/friction-logger/SKILL.md` — copy vibe-iterate's, adapt data path to `~/.claude/plugins/data/vibe-walk/`.
- [ ] **0.6** `skills/evolve-walk/SKILL.md` — L3 self-evolution, named `evolve-walk` from the start (per pending-renames convention).
- [ ] **0.7** Validate: plugin-validator agent passes; SKILL frontmatter parses; commit.

**M0 acceptance:** plugin loads; `/vibe-walk` router runs and hands to bootstrap on first run; self-evolution trio present and structurally valid.

## Milestones ahead (bite-sized at their /build)

- [ ] **M1** Phase 1 discovery + "should we build a tour?" verdict — THE differentiator (build first after scaffold). Scripts: `inventory_surfaces.py`, `anchor_readiness.py`, `build_verdict.py`; `skills/discover/SKILL.md`.
- [ ] **M2** Phase 1.5 interview gates + substrate decision tree (`scripts/build/substrate_tree.py`; gates in `skills/walk/SKILL.md`).
- [ ] **M3** Phase 2 tour generator — drop-in Driver.js module (`scripts/build/emit_tour_module.py`).
- [ ] **M4** Anchor-injection codemod — 4-gate + REVIEW_NEEDED (`scripts/anchors/inject_anchors.js`).
- [ ] **M5** Analytics wiring + replay (`scripts/build/emit_analytics.py`).
- [ ] **M6** Self-evolution complete + vitals + README + marketplace prep.

**Dogfood gate (before /reflect):** re-generate the Celestia3 tour through the plugin; compare to the hand-built PR #12 tour.
