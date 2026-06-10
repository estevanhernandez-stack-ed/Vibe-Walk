# Changelog

All notable changes to the vibe-walk plugin are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] — 2026-06-09 · keyboard/AT contract — focus return + emit-time a11y assertions

GAP-11 of the quality-net gap analysis (vibe-plugins `docs/quality-net-gap-analysis-2026-06-09.md`). The emitted tour runs in front of brand-new users — the highest-stakes accessibility surface a host app has — and nothing verified it.

### Added

- **Focus return in the emitted runner.** `spotlightTour.ts` now captures `document.activeElement` before `drive()` and restores it in `onDestroyed` — closing the tour hands keyboard focus back instead of stranding it on `document.body`.
- **`diagnostics/a11y_assertions.py`** — mechanical keyboard/AT contract checks over any emitted tour: keyboard control enabled, escape hatch intact (ESC + close button), nav buttons present, focus return wired, destroy hook present, per-step popover copy. fail/warn severities. A script, not a checklist — prose-only enforcement rots (the family's GAP-02 lesson).
- **`/walk` emit-time gate** — fail-level findings block hand-off; warn-level findings surface verbatim in the hand-off message.
- **`/vitals` Check #9** — host-side a11y assertions beside the anchor-drift check (#8). Report sums now run to 9.
- 14 new tests including emitter self-coherence (the emitter's own output must pass its own gate). Suite at 219.

### Migration note (GAP-22 discipline)

Tours emitted by **v0.2.0 and earlier lack the focus-return pair** — `/vitals` Check #9 reports them as `focus-return-missing` (warn). Re-emit with v0.3.0, or hand-add the `document.activeElement` capture + `.focus()` restore around `driver()`. Verified against the real Celestia3 walk-emitted tour: passes every fail-level assertion, warns exactly on focus return, as expected for a v0.2.0 emission.

### Fixed

- Personal-path docstring example scrubbed from `emit_tour_module.py` (promotion-checklist burn-down row cleared).

## [0.2.0] — 2026-06-09 · i18n-ready step copy

### Added

- **`spotlight.i18n.json`** — step copy externalized to a sibling translation file keyed `spotlight.step.<anchor>.{title,description}`; the emitted `spotlightSteps.ts` reads keys through a `t()` helper with inline English fallbacks.

### Migration note (backfilled — owed since release)

Tours emitted by **v0.1.0 carry inline-only copy** with no i18n file and no `t()` helper. They keep working untouched (fallbacks are the same strings), but to localize a v0.1.0 tour you must re-emit with v0.2.0+ — there is no in-place upgrade path. This note was demanded by the v0.2.0 followups ledger and never shipped; backfilled 2026-06-09 under the promotion-checklist contract-change rule (GAP-22).

## [0.1.0] — 2026-06-08 · first release

Initial marketplace release: discovery with the build/don't-build verdict, Driver.js spotlight tour emission with the human-gated anchor pass, 6-event analytics adapter, trigger wiring, session + friction logging.
