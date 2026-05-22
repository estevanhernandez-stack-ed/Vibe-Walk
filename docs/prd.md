# PRD — Vibe-Walk

> Compressed /prd (pattern mm). Requirements = the seed's GENERATE/ASK/AVOID contract.
> Source of truth: `docs/inputs/research/_seed.md` §4 + §3.

## Functional requirements

**FR1 — Discovery (Phase 1).** Read README/DOCS/CLAUDE.md + route surface + components; produce: product+audience summary, user-facing surface inventory, named aha-moment candidate, ranked stop shortlist (8-12), anchor-readiness verdict + risk flags.
**FR2 — Verdict (Phase 1, first-class).** Emit build / don't-build / cheaper-first, applying the don't-build condition list (seed §3 step 6). Equal weight to "build."
**FR3 — Interview gates (Phase 1.5).** Five gates: mode · trigger model (+ "what else fires on first login?") · substrate (run the decision tree, ask only to confirm) · aha moment · primary role.
**FR4 — Tour generation (Phase 2).** Drop-in Driver.js module: ≤5 steps (default 3-4), step 1 → aha; benefit-led copy ≤25 words/step; progress indicator; SSR guard; onboarding-state reuse; persistent ungated replay.
**FR5 — Anchor injection (Phase 2).** `data-tour="<kebab-name>"` codemod; auto-inject only the 4-gate-safe subset; everything else → `REVIEW_NEEDED.md`; halt for human resolution.
**FR6 — Analytics (Phase 2).** Wire the 6-event schema to substrate hooks + emit `TOUR_ANALYTICS.md` (events + host activation event + 7d/14d windows). Never ship dark.

## Acceptance criteria (per the seed)

- Honest step-ceiling framing in the plugin's own copy (curve direction, not fake-precise %).
- Substrate decision tree resolves correctly across all branches; Intro.js always rejected (AGPL).
- Codemod is idempotent; REVIEW_NEEDED reason-coded; build halts until resolved.
- Don't-build verdict fires on the documented signals (truth-table tested).
- Self-evolution skills present and structurally valid.

## Guardrails (AVOID — seed §4)

>5 steps without approval · auto-fire into onboarding debt · class-name anchoring · feature-labeling/condescending copy · shadow-DOM/iframe anchoring · Intro.js · auto-injecting unsafe cases · two emitter templates by default · merging tour+training configs · building a tour when a don't-build condition fires.
