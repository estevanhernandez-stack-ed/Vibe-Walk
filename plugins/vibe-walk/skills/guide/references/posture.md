# Posture — how vibe-walk operates

The operating stance every command inherits. Four principles, in priority order.

## 1. Autonomous-first

Do the reading before asking. Phase 1 (discovery) runs entirely on the codebase — docs, routes, components, existing onboarding — and produces a verdict and a shortlist before the builder is asked anything. Same DNA as vibe-doc (reads the codebase for technical docs) and vibe-iterate (reads codebase + competitors for next features). The read target here is the **user-facing surface area**; the audience for the output is **end users**, not developers.

## 2. Earn the tour

"Don't build a tour" is a first-class Phase 1 output, equal in weight to "build one." The best products in their categories often reject spotlight tours as a primary mechanism, and a tour layered on an already-intuitive UI does net-negative damage by training a dismiss reflex. The plugin's first job is to decide whether a tour helps — then build a good one only if it does. Don't-build conditions and the "cheaper-first" recommendation (empty-state / sample-data) are in [`conventions.md`](conventions.md) and the research seed.

## 3. Honest evidence

The step-count completion guardrail rests on single-vendor, unreplicated data. State it that way — cite the curve direction and cognitive-load theory, never a fake-precise percentage. When the plugin warns or explains, its credibility tracks the honesty of its claims. Mark anything unverified as such.

## 4. Reuse, don't reinvent

Apps that warrant a tour usually already track some first-run state. Find it and extend it (the inaugural Celestia3 job added `hasSeenSpotlight` beside the existing `hasSeenWelcome`). Never invent a parallel store. Discover existing onboarding before designing, so the tour sequences after it instead of piling on.
