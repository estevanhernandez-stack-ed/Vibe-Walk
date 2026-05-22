# Spec — Vibe-Walk

> Compressed /spec (pattern mm). The technical blueprint IS the grand plan.
> Source of truth: `docs/inputs/2026-05-21-vibe-walk-grand-plan.md` + `docs/inputs/research/_seed.md` §2.

## Architecture

vibe-* family plugin (templated on vibe-iterate): SKILL-driven, autonomous-first, Level 2/3 self-evolution. Two-phase engine (discovery → build) with an interview gate. Scripts in Python/Node do the heavy lifting (surface reader, verdict, substrate tree, emitters, anchor codemod); SKILLs orchestrate.

## File structure

Per the grand plan (matches the vibe-* convention):
```
plugins/vibe-walk/.claude-plugin/plugin.json
plugins/vibe-walk/skills/{vibe-walk(router), guide(+references), bootstrap, discover, walk, session-logger, friction-logger, evolve-walk, vitals}/SKILL.md
plugins/vibe-walk/scripts/{discovery, build, anchors}/...
```

## Build constraints (D1-D6, non-negotiable — seed §2)

- **D1** 5-step cap (default 3-4); state honestly. **D2** drop-in module default; config-only deferred. **D3** Driver.js default + override tree (NextStep `id`, shadow-DOM wall, Intro.js rejected). **D4** `data-tour="<kebab>"` anchor contract. **D5** 6-event analytics + `TOUR_ANALYTICS.md`. **D6** 4-gate codemod auto-inject + `REVIEW_NEEDED.md` halt.

## Substrate decision tree

Adopt verbatim from `_seed.md` §3 (Phase 1.5 substrate tree). The plugin executes it; asks only to confirm/resolve overrides.

## Testing

Scripts are unit-tested against fixture repos (tour-worthy app, single-purpose tool → don't-build, no-stable-selectors → anchor-pass-needed). Verdict logic gets a truth-table test. SKILL behavior verified via plugin-validator + skill-reviewer + dogfooding on Celestia3.

## Deployment

Solo repo `estevanhernandez-stack-ed/Vibe-Walk` → canary; ref-bump in `vibe-plugins/.claude-plugin/marketplace.json` → stable. Tag naming: plain `vX.Y.Z`. Confirm before any GitHub remote/push.
