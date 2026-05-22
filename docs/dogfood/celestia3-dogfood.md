# Vibe-Walk Dogfood Trial — Celestia3

**Date:** 2026-05-22  
**Target:** `C:\Users\estev\Projects\Celestia3` (Next.js App Router + Firebase, astrology webapp)  
**Comparison target:** `feat/spotlight-tour` branch (6-stop Driver.js tour, hand-built cowpath)  
**Plugin version:** built at HEAD, 125 Python + 23 JS tests green  
**Headline verdict:** PARTIALLY — surface inventory accurate, aha correct, but verdict misfires on a real app and the generated tour has meaningful structural gaps vs the cowpath

---

## Phase 1 — Discovery Results

### Surface inventory (inventory_surfaces.py)

**What the script found:**
- 65 surfaces total, 36 interactive
- Correctly identified: `DashboardShell`, `NatalCompass`, `AthanorChatBar`, `WelcomeModal`, `OnboardingExperience`, `TarotDeck`, `TransitFeed`, `NumerologyView`, `SynastryView`, `TarotExplorer`, and all the service/lib layer

**What it missed or got wrong:**
1. **Product summary pulled from CLAUDE.md not README.md** — CLAUDE.md has a `<!-- gitnexus:start -->` preamble that made the raw extracted summary read as `"GitNexus — Code Intelligence"` instead of the actual product description. The script tries CLAUDE.md first (correct per orientation-doc priority), but CLAUDE.md here is a GitNexus index header, not a product description. Raw output: `"<!-- gitnexus:start --> GitNexus Code Intelligence"`. The actual product description lives in README.md. **This is a real-app failure mode the fixtures never tested.**

2. **65 surfaces surfaced when the cowpath scoped to ~8 relevant home-view surfaces** — the script correctly collected the full app surface area (services, AI layers, lib utilities, admin views) but the ranking pass in the SKILL would need to prune heavily to get to a 6-stop shortlist. Services and utilities (`CelebrityService`, `ChatService`, `SwissEphemerisService`, etc.) all show up as `[root]` surfaces — these are correctly classified as non-interactive by name-heuristic but inflate the list.

3. **`_has_existing_onboarding` scanner correctly found `OnboardingExperience.tsx`, `WelcomeModal.tsx`, `OnboardingService.ts`** — the scan works. The `.agent/` directory false-positive (`ux-guidelines.csv` matched "guide") would have fired first in worst case, but in this run the correct files were found because `.agent/` doesn't have a hard exclude in the signal helper. **Minor bug: `.agent/` should be in the skip list for `_has_existing_onboarding`.**

### Anchor readiness (anchor_readiness.py)

**Result:** `needs-pass` — **CORRECT**

- `dynamic_mount` flag raised — correct (Celestia3 uses dynamic imports for performance)
- `ssr_risk` flag raised — correct (Next.js 15)
- No `shadow_dom`, no `cross_origin_iframe` — correct
- **Notable miss: `css_modules` not flagged** — Celestia3 uses Tailwind exclusively with no CSS Modules files. The `tailwind_only` flag was also NOT raised even though className-only files dominated (117 files total vs 7 files with stable selectors = 6% coverage). The `tailwind_only` condition requires `files_with_stable == 0`; since 7 files have stable selectors, the flag doesn't fire. That's technically correct by the current logic but might be misleading — 94% Tailwind-only coverage is still a significant anchor-pass burden.

**The `needs-pass` verdict is correct.** Celestia3 had only 2 data-testid attrs originally (the cowpath process-notes confirmed this). The script measured 7 files with stable selectors / 117 total = 6% coverage — solidly in `needs-pass` territory. ✓

**What the script missed:** it did NOT report `no_stable_selectors` (correct — 7 files DO have selectors), so no false don't-build from that condition. But it also didn't distinguish the type of stable selectors. Most of those 7 files likely have `id=` on Firebase config items or test IDs, not tour-relevant elements. The anchor-readiness verdict is right for the right reasons.

### Verdict (build_verdict.py) — THE CRITICAL FAILURE

**Plugin verdict:** `don't-build`  
**Correct verdict:** `build`  
**Verdict fired:** Condition 3 — "Comprehensive onboarding already exists"

**Why this is wrong:**

`_has_existing_onboarding` correctly detected `OnboardingExperience.tsx` and `WelcomeModal.tsx`. These files exist. But the **Condition 3 signal is a type-error in disguise**: Celestia3's onboarding is a pre-dashboard cinematic flyby (3D planet intro sequence + birth-data form). It does NOT orient users to the dashboard they land on. The cowpath design spec explicitly states: *"A short spotlight tour fills that gap. It picks up after the flyby and welcome modal — it does not replace them."*

The current signal logic collapses **"onboarding of any kind exists"** into **"comprehensive onboarding exists that makes a tour redundant."** That's not the same thing. A birth-data entry flow and a dashboard-orientation tour serve orthogonal purposes.

**The real signal needed:** not just "does an onboarding flow exist?" but "does the existing onboarding orient users to the SAME surface the tour would cover?" The Condition 3 description in `build_verdict.py` even says "comprehensive onboarding" — but `_has_existing_onboarding` just scans for file name matches, with no concept of "comprehensive" or "same-surface."

**Impact:** this is the highest-severity bug found. On Celestia3 — the literal reference app the plugin was built against — the verdict is a false negative. Every app with a signup/onboarding flow that doesn't yet have a dashboard tour would misfire here.

---

## Phase 1.5 — Substrate Resolution

**Framework correctly identified:** `next-app-router`  
**tour_spans_multiple_routes:** `False` — correct. All 6 cowpath stops are on the home/compass view.

**Substrate result:** `driver.js` (default, confirm_only=True) — **CORRECT match with cowpath.**

The cowpath chose Driver.js. The substrate tree resolves to Driver.js (default path, since single-route, no shadow DOM, no animation override). ✓

**One concern:** `dynamic_mount` flag from anchor_readiness was raised app-wide (Celestia3 uses dynamic imports broadly). The SKILL.md maps `dynamic_mount` flag → `needs_async_mount_wait=True` signal → substrate becomes `react-joyride` (mandatory, Branch 5). But the tour stops are all on the home/compass view which renders eagerly — dynamic imports are for other views. The mapping is **too aggressive**: a repo-wide `dynamic_mount` flag does not mean every tour stop is behind an async mount. The cowpath confirmed this: Driver.js worked fine on these stops.

**If the SKILL ran as written**, it would resolve `react-joyride` instead of `driver.js` — a substrate mismatch with the cowpath.

---

## Phase 2 — Generated Files vs Hand-Built

### spotlightSteps.ts comparison

| Dimension | Plugin-generated | Hand-built (feat/spotlight-tour) |
|---|---|---|
| Stop count | 5 (D1 cap triggered) | 6 |
| Anchor selector | `[data-tour="…"]` | `#tour-…` (id selectors) |
| Stop order | NatalCompass first (aha-first rule) | Sidebar nav first (journey order) |
| Copy quality | Serviceable (derived from purpose string) | Tighter, more idiomatic |
| Side/align cycle | Mechanical (right/bottom/bottom/top/left) | Deliberate per stop |

**The 5-stop cap vs 6-stop cowpath:** D1 is a hard cap at 5. The cowpath shipped 6. The plugin fires a warning and trims to 5, dropping `athanor-chat` (the lowest-ranked stop). The 6-stop cowpath choice was deliberate — Athanor is the AI escape hatch and the team decided 6 was worth it. **The plugin's cap is correct by the D1 rule, but the D1 rule may need revisiting.** The cowpath team explicitly chose 6. Either: (a) the rule should be "warn at 5, hard-cap at 7" to allow one step of override room, or (b) D1 is right and the cowpath was slightly over-scoped. Not a plugin bug — a design constraint to revisit.

**Anchor contract mismatch:** This is **a real structural gap.** The hand-built tour uses `id` selectors (`#tour-sidebar-nav`, `#tour-natal-chart`). The plugin emits `data-tour` selectors (`[data-tour="sidebar-nav"]`). Both are legitimate anchor contracts, but they don't match. The hand-built tour was built before the plugin existed and chose `id` (additive, no class pollution). The plugin enforces `data-tour` per the SKILL's D4 convention. For Celestia3 specifically, the anchor inject pass would need to change strategy.

**Stop ordering:** The plugin reorders to aha-moment first (NatalCompass step 1). The cowpath placed sidebar nav first, natal chart fifth. The cowpath reasoning was explicit: "start with orientation (sidebar), build to the payoff (natal chart)." The plugin's aha-first rule inverts this — user gets the emotional payoff at step 1 with no orientation context. This is a **debatable design choice, not a bug**, but it's worth flagging: aha-first is the right call for short tours (2–3 stops) but can feel disjointed on a 5-stop tour where context-first works better.

**Copy quality:** The plugin's copy is derived from the `purpose` field extracted by `inventory_surfaces.py`. Quality is serviceable but rougher than the hand-written copy. Example:

- Plugin: `"Your sky at birth, in 3D. Hover planets and inspect aspects — the heart of Celestia"` (acceptable)
- Cowpath: `"Your sky at birth, in 3D. Hover planets and inspect aspects — the heart of Celestia."` (identical, actually)

The copy turned out close for the stops that had good purpose strings. The fallback cases (derived from PascalCase splitting) are weaker: `"NatalCompass"` → title `"NatalCompass"` (not split to "Natal Compass") — PascalCase splitting doesn't fire on the `name` field when the anchor name differs from the surface name.

**popoverClass:** Plugin emits `celestia3-spotlight` (derived from dir name). Cowpath uses `celestia-spotlight`. Minor naming difference — functionally equivalent, but breaks CSS if someone copies the cowpath's `spotlight-tour.css` and expects the class name to match.

### spotlightTour.ts comparison

| Dimension | Plugin-generated | Hand-built |
|---|---|---|
| SSR guard | ✓ `typeof window === 'undefined'` check | ✗ Missing in cowpath |
| `replaySpotlightTour` export | ✓ Present | ✗ Missing in cowpath |
| `nextBtnText`, `prevBtnText`, `doneBtnText` | ✗ Not set | ✓ Set ('Next', 'Back', 'Begin') |
| CSS import | `driver.js/dist/driver.css` | `driver.js/dist/driver.css` + `./spotlight-tour.css` |
| `startSpotlightTour` signature | ✓ Matches | ✓ Matches |

**The plugin wins on two fronts:** SSR guard (the cowpath lacked it — would break Next.js SSR), and `replaySpotlightTour` export (cowpath had no replay export). These are genuine improvements over the hand-built version.

**The plugin misses:** custom button labels and the app-themed CSS. The `spotlight-tour.css` import (cosmic dark glass theme) is a Celestia3-specific touch the plugin can't generate — that's expected. But `nextBtnText`/`prevBtnText`/`doneBtnText` are config the plugin should either ask about or default better.

### tourAnalytics.ts + TOUR_ANALYTICS.md

Not in the cowpath at all — the design spec explicitly notes "Analytics on tour completion — not wired now." The plugin generates these correctly and the TOUR_ANALYTICS.md calls out the Celestia3 dark-data decision by name, which is accurate. **This is a genuine plugin win.** Every future app gets analytics scaffolding that Celestia3 didn't have.

---

## Prioritized Fixes (feeding /evolve)

### P0 — Verdict false negative on apps with pre-dashboard onboarding

**Bug:** `_has_existing_onboarding` fires on any file named `*onboard*`, `*tour*`, etc. `build_verdict.py` Condition 3 treats this as "comprehensive onboarding" and returns `don't-build`. Celestia3 — the reference app — misfires.

**Fix:** Condition 3 needs a richer signal. Options:
- Add an `onboarding_covers_same_surface` boolean to the signals dict — True only when the detected onboarding is a dashboard-orientation-style walkthrough (check for tour/spotlight patterns specifically), False when it's a signup/intro flow.
- Rename the signal `has_same_surface_onboarding` and tighten `_has_existing_onboarding` to only return True when `*tour*` or `*spotlight*` patterns are found (not just `*onboard*` or `*guide*`).
- Alternatively, downgrade Condition 3 from hard don't-build to a cheaper-first warning when `existing_onboarding` is True but `*tour*`/`*spotlight*` patterns are absent.

### P1 — `dynamic_mount` flag maps too aggressively to substrate

**Bug:** `dynamic_mount` in anchor_readiness risk_flags → SKILL maps to `needs_async_mount_wait=True` → substrate tree → `react-joyride` mandatory. But the flag is repo-wide; the tour stops may not be behind async mounts. Result: wrong substrate for Celestia3.

**Fix:** Either (a) don't propagate `dynamic_mount` to `needs_async_mount_wait` by default — instead, make it a Gate 3 sub-question ("do any of your planned tour stops live behind a lazy import or portal?"), or (b) add a second check in anchor_readiness that specifically scans the planned tour stop files for dynamic mount patterns, not the whole repo.

### P1 — Product summary reads wrong orientation doc on tool-augmented repos

**Bug:** CLAUDE.md priority is correct for typical repos, but many real-world repos have CLAUDE.md prefixed with tooling preamble (GitNexus, AI index headers, CI status blocks). The first-paragraph extraction falls through to GitNexus boilerplate.

**Fix:** In `_extract_first_paragraph`, skip lines matching known tooling headers (`<!-- gitnexus:start -->`, `<!-- AI-INDEX`, `[!NOTE]` blocks at the top). Or try README.md as a fallback when the extracted summary is below a quality threshold (length < 30 chars, or starts with `<!--`).

### P2 — Anchor contract mismatch: `data-tour` vs `id` selectors

**Gap:** Plugin hardcodes `data-tour` selectors via D4. Cowpath (and the substrate_tree for nextstep.js path) used `id` selectors. The anchor inject pass will produce one contract; any hand-adjusted anchors may be on the other.

**Fix:** This isn't a clear bug — D4 is an explicit decision. But: document in the SKILL's Gate 3 anchor-contract message that `id` is also acceptable as a manually-applied alternative, and that `inject_anchors.js` will use `data-tour` but existing `id` attrs will work if the tour steps reference them directly.

### P2 — Aha-moment first ordering vs journey ordering

**Gap:** Plugin reorders NatalCompass to step 1. Cowpath intentionally put sidebar nav first (orientation → payoff). On 5+ stop tours, journey order (orientation-first) is more usable.

**Fix:** Change the aha-first rule to: "aha moment is step 1 on tours of 3 steps or fewer; on tours of 4+ steps, aha moment is the last step before utility/escape-hatch stops." Or make the aha-first ordering a Gate 4 confirmation choice: "Discovery ranked [NatalCompass] as the aha moment. Should it lead the tour (immediate payoff) or close it (earned payoff)?"

### P3 — D1 cap at 5 warrants review against the Celestia3 precedent

**Gap:** Cowpath shipped 6 stops deliberately. The D1 cap at 5 trims Athanor (the AI escape hatch). The trim warning is correctly surfaced.

**Fix / decision:** Consider raising D1 to 7 as a soft cap (warn at 6, hard-cap at 7), or keep 5 but make the "split tour" recommendation more actionable — emit a second `spotlightSteps.advanced.ts` stub with the trimmed stops so the builder has something to work with immediately.

### P3 — `nextBtnText`/`prevBtnText`/`doneBtnText` not in emitted runner

**Gap:** Cowpath set `doneBtnText: 'Begin'` (contextually perfect for Celestia3). Plugin emits none.

**Fix:** Add a Gate 2 optional sub-question for custom button labels, or emit sensible defaults (`nextBtnText: 'Next'`, `prevBtnText: 'Back'`, `doneBtnText: 'Done'`) and let the builder edit.

---

## Summary Scorecard

| Dimension | Result | Notes |
|---|---|---|
| Surface inventory accuracy | **Partial** | All 6 cowpath surfaces found among 65 total; ranking/pruning is manual SKILL work |
| Existing onboarding detection | **Correct detection, wrong conclusion** | Files found correctly; verdict treatment is wrong (P0 bug) |
| Aha-moment candidate | **Correct** | NatalCompass identified and named correctly |
| Anchor readiness verdict | **Correct** | `needs-pass` — matches cowpath expectation |
| Build/don't-build verdict | **Wrong** | `don't-build` returned; correct answer is `build` |
| Substrate resolution | **Correct path, risky signal** | `driver.js` via default is right; `dynamic_mount` would corrupt it if SKILL ran as-written |
| Generated tour structure | **Partial** | Driver.js, SSR guard, replay export — all wins; anchor contract, stop order, cap mismatch |
| Generated copy quality | **Acceptable** | Close to cowpath for well-documented stops; degrades on PascalCase-only surfaces |
| Analytics output | **Better than cowpath** | Cowpath shipped dark; plugin generates full 6-event adapter |

---

## Final verdict

**DONE_WITH_CONCERNS**

The plugin is not publishable in current form. The P0 verdict bug is a disqualifying false negative on the reference app itself. Fix P0 + P1, re-run this trial, confirm verdict flips to `build`, then publish.

The generated tour — once the verdict clears — is deployable with a few edits: anchor contract alignment (`data-tour` → `id` or vice versa), stop-order adjustment, custom button labels. The analytics output is genuinely better than the cowpath and should be kept as a selling point.

---

## Artifacts

Generated plugin output under `docs/dogfood/celestia3-output/`:
- `discovery.json` — full surface inventory, readiness, ranked shortlist, aha candidate
- `build-plan.json` — substrate-resolved build plan (corrected signals)
- `spotlightSteps.ts` — 5-stop DriveStep[] array (D1-capped, aha-first)
- `spotlightTour.ts` — driver() runner with SSR guard + replay export
- `tourAnalytics.ts` — 6-event analytics adapter
- `TOUR_ANALYTICS.md` — wiring guide

Comparison target read from: `git show feat/spotlight-tour:src/components/tour/spotlightSteps.ts` and `spotlightTour.ts`.
