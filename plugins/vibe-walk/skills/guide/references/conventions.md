# Conventions — vibe-walk output decisions

The resolved design decisions every command honors. These are non-negotiable build constraints. Source of truth: this cycle's research seed (`docs/inputs/research/_seed.md` §2, decisions D1–D6).

## D1 — Step-count cap

Generated tours are hard-capped at **5 steps**, default 3–4. Step one routes to the named aha moment. To exceed 5, warn and require explicit approval; suggest splitting into a first-run tour + a separate feature-discovery tour. State the ceiling honestly: completion declines steeply past 5 steps per single-vendor (Chameleon) data — cite the curve direction and cognitive-load theory, not specific percentages.

## D2 — Output shape

Default output is a **dropped-in tour module** (the "you own the code" model). Config-only JSON is deferred — its version-skew failure mode is silent, so it is a gated exception for v2, not a co-equal mode. v1 ships one emitter template.

## D3 — Substrate

Default substrate is **Driver.js** (small, framework-agnostic, MIT, serializable steps). Override only on the documented conditions (React-specific needs, Next.js multi-route → NextStep with `id` anchoring, animated surfaces → Reactour, async mount → React Joyride). **Never Intro.js** (AGPL-3 — license poison for host apps). **Shadow DOM is a hard wall** — mark the stop untourable.

## D4 — Anchor contract

Anchor tour stops with `data-tour="<kebab-semantic-name>"` — globally unique, no step numbers in the value. Class-name anchoring is forbidden (CSS Modules hashes and Tailwind utilities are not stable). NextStep is the lone exception: it targets `id="tour-<name>"`.

## D5 — Analytics

Wire the six-event schema to the substrate's callbacks: `tour_started`, `tour_step_viewed`, `tour_step_advanced`, `tour_skipped`, `tour_completed`, `tour_replayed` — plus the host's own activation event. Emit a `TOUR_ANALYTICS.md` naming the events, the activation event, and the attribution windows (7-day adoption, 14-day retention). Never ship a tour dark; completion alone is a trap metric.

## D6 — Anchor-injection boundary

Auto-inject `data-tour` only when all four gates hold: (a) intrinsic HTML tag or directly-imported named component, (b) single unambiguous root return, (c) no HOC / dynamic import / render-prop, (d) the attribute is absent (idempotent). Everything else routes to `REVIEW_NEEDED.md` with a per-item reason code, and **the build halts** until the human resolves the list.
