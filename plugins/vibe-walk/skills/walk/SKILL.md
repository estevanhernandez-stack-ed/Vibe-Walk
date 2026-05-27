---
name: walk
description: "Phase 1.5 interview gates + Phase 2 tour generator for vibe-walk. Reads .vibe-walk/discovery.json, resolves the tour substrate via the decision tree (substrate_tree.py), runs five interview gates, writes .vibe-walk/build-plan.json, then orchestrates four Phase 2 steps: anchor injection (M4), tour module emission (M3), analytics wiring (M5), and trigger wiring (M7)."
---

# /vibe-walk:walk — Phase 1.5 interview gates + Phase 2 tour generator

Read [`../guide/SKILL.md`](../guide/SKILL.md) for the Sherpa persona, posture, and conventions, then follow this command.

## What this command does

Phase 1.5 is the interview between discovery and build. Five gates. The substrate decision tree runs before any question is asked — never ask what the tree already answers. Ask only to confirm the tree's resolution or to resolve an explicit override condition.

At the end of the five gates, the resolved answers land in `.vibe-walk/build-plan.json`. **Phase 2 runs four steps in sequence:** anchor injection (M4) → tour module emission (M3) → analytics wiring (M5) → trigger wiring (M7). There is one automated human gate between step 1 and step 2: if the anchor codemod routes any stop to `REVIEW_NEEDED.md`, the build halts there until the builder resolves that list. Steps 2, 3, and 4 run without further interruption once the anchor pass is clean. Step 4 produces a `WIRING.md` placement guide; the builder applies the auto-fire effect and replay control to their main component — the one human gate in step 4.

```
read discovery.json
  → run substrate_tree.resolve_substrate()
    → Gate 1: Mode
    → Gate 2: Trigger model + overlay-sequencing sub-q
    → Gate 3: Substrate — confirm or resolve override
    → Gate 4: Aha moment — confirm M1 candidate
    → Gate 5: Primary user role
      → write build-plan.json
        → Phase 2, step 1: inject_anchors.js (M4)
            → if REVIEW_NEEDED entries exist → write REVIEW_NEEDED.md → HALT
            → if anchor pass is clean → continue
        → Phase 2, step 2: emit_tour_module.emit_module(build_plan) (M3)
            → write spotlightSteps.ts + spotlightTour.ts to app tour directory
            → surface D1 cap warnings
        → Phase 2, step 3: emit_analytics.emit_analytics(build_plan) (M5)
            → write tourAnalytics.ts + TOUR_ANALYTICS.md to app tour directory
        → Phase 2, step 4: emit_trigger_wiring.emit_trigger_wiring(build_plan, host_signals) (M7)
            → assemble host_signals (framework, first_run_flag_system, main_component, existing_overlays)
            → write WIRING.md to app tour directory
            → apply safe snippets (flag extension where possible)
            → present wiring guide → builder applies effect + replay (human gate)
              → hand off (Phase 2 complete)
```

## Prerequisites

This command requires a `build` verdict from Phase 1. On entry:

1. Read `.vibe-walk/discovery.json`.
2. If absent → tell the builder to run `/vibe-walk:discover` first.
3. If `verdict != "build"` → surface the verdict and its reasons, and explain that Phase 1.5 runs only on a `build` verdict. Offer to re-run discovery.
4. If `build` → proceed.

## Execution procedure

### 1. Session start

Invoke `session-logger.start("walk", project_dir_basename)`. Store the returned `sessionUUID`.

### 2. Load discovery context

From `.vibe-walk/discovery.json`, extract and hold:

- `aha_moment` — `{surface, reason}`
- `anchor_readiness` — `{readiness, risk_flags}`
- `ranked_shortlist` — ordered list
- `product_summary` — the audience read (infer register: b2c / b2b / technical)
- `verdict_reasons` — carried for context

Infer the `framework` signal from the app path if not already present in discovery output:
- Look for `next.config.*`, `nuxt.config.*`, `svelte.config.*`, `astro.config.*`, `vite.config.*` in the app root.
- Look for `"react"` / `"next"` / `"svelte"` / `"vue"` in `package.json` `dependencies`.
- If multiple `app/` directories exist with `layout.*` → `"next-app-router"`.
- Else if `pages/` exists → `"next-pages-router"`.
- Default to `"react-spa"` for unidentifiable React apps.

### 3. Build substrate signals

Populate the `signals` dict for `resolve_substrate()`:

```python
from build.substrate_tree import resolve_substrate

signals = {
    "framework":                  _infer_framework(app_path),
    "tour_spans_multiple_routes": _detect_multi_route(discovery, ranked_shortlist),
    "has_shadow_dom_stops":       "shadow_dom" in anchor_readiness["risk_flags"],
    "output_shape":               "module",   # default; may change at Gate 3
    "needs_async_mount_wait":     _detect_async_mount_in_stops(ranked_shortlist, app_path),
    "heavily_animated":           False,      # unknown until Gate 3 override
    "wants_idiomatic_react":      False,      # unknown until Gate 3 override
    "bundle_size_sensitive":      False,      # unknown until Gate 3 override
}

substrate_result = resolve_substrate(signals)
```

**Signal inference helpers (inline in SKILL execution, not separate scripts):**

- `_infer_framework` — scan app root for config files and package.json (see step 2). Returns a framework string.
- `_detect_multi_route` — if `ranked_shortlist` items span more than one distinct `view` value → `True`. If `view` is missing or all items share one view → `False`.
- `_detect_async_mount_in_stops` — scan ONLY the source files listed in `ranked_shortlist` (the planned tour stop files, not the whole repo) for `import(` / `React.lazy(` patterns. Return `True` only if a tour stop file itself uses dynamic imports or lazy loading. **Do NOT use the repo-wide `dynamic_mount` flag from `anchor_readiness` for this signal** — the flag fires on ANY dynamic import in the repo (e.g. performance lazy-loading for unrelated views). Mapping it repo-wide would force `react-joyride` substrate for apps like Celestia3 whose tour stops are all eagerly rendered. If in doubt, default to `False` and confirm at Gate 3.

### 4. Run the five interview gates

Keep each gate separate. Do not merge. Do not ask multiple questions in one turn unless the sub-question is part of the same gate (Gate 2 has one sub-question that always fires).

---

#### Gate 1 — Mode

**Purpose:** confirm walkthrough (v1) vs training (v2). Usually inferable; confirm anyway.

**What to say:**

```
Gate 1 of 5 — Mode

Phase 1 reads this as a <b2c warm / b2b authoritative / technical sparse> product,
which points to walkthrough mode (v1) — a short, skippable spotlight tour.

Training mode (v2) is a different architecture: objectives, exercises, quizzes, role
gates. It is deferred and not yet built.

→ Walkthrough (v1), confirmed? Or is this a training use case (v2, deferred)?
```

**Defaults:**
- Answer is almost always walkthrough (v1). Training is v2 and not built.
- If the builder says training → note it, explain it is deferred to v2, and proceed with walkthrough unless they want to stop.

**Friction trigger:** none at this gate (confirmation, not override territory).

---

#### Gate 2 — Trigger model

**Purpose:** how and when the tour fires.

**What to say:**

```
Gate 2 of 5 — Trigger model

Three options:
  A. Auto-once + replay (default) — fires once on first qualifying action, skippable,
     with a persistent replay entry point.
  B. On-demand only — user initiates manually (help menu, "?" button, etc.).
  C. Auto-once, no replay — fires once; no replay. Not recommended — locks out the
     ~38% of users who dismiss in the first few seconds.

Default is A.

→ Which trigger model? (A / B / C)
```

**Immediately follow with the sub-question (same gate, sequential):**

```
Sub-question: What other modals, banners, or overlays fire on first login?
(welcome modal, cookie banner, terms prompt, free-trial nudge, intro flyby, etc.)

Knowing the sequence prevents stacking — the tour should queue behind the welcome
modal AND a qualifying first action, not fire on raw modal-close.

→ List anything that fires on first visit, or "none."
```

**Pre-fill from discovery when `existing_intro_flow=True`:**
If Phase 1's signal assembly detected `existing_intro_flow=True` (signup/onboarding/welcome files
found — e.g. `OnboardingExperience.tsx`, `WelcomeModal.tsx`), pre-fill the sub-question answer:

```
Sub-question: What other modals, banners, or overlays fire on first login?

Phase 1 detected an intro/onboarding flow in this app:
  <list of detected files matching *onboard*, *welcome*, *intro*, *flyby*>

Recommendation: the tour should fire AFTER this flow completes + a qualifying first
dashboard action (not on raw onboarding-close). Default trigger: auto-once + replay.

→ Confirm this sequencing, or describe the actual first-login overlay order.
```

**Friction trigger:** none at this gate (defaults are well-reasoned; the sub-question is informational).

---

#### Gate 3 — Substrate

**Purpose:** confirm the decision-tree result. Ask only to confirm or resolve an override.

**What to say when substrate_result.confirm_only is True (default driver.js):**

```
Gate 3 of 5 — Substrate

Decision tree resolved: Driver.js (default)
Reason: <substrate_result["reason"]>
Anchor contract: data-tour="<kebab-semantic-name>"

→ Confirmed? Or do you want to override? (If yes to override, tell me which library
  and why — react-joyride, reactour, or nextstep.js only; Intro.js is not available.)
```

**What to say when substrate_result.confirm_only is False (mandatory or forced path):**

```
Gate 3 of 5 — Substrate

Decision tree resolved: <substrate_result["substrate"]> (mandatory)
Reason: <substrate_result["reason"]>
Anchor contract: <substrate_result["anchor_attr"] == "id" ? 'id="tour-<name>"' : 'data-tour="<kebab-semantic-name>"'>

This is a forced path — the tree detected a condition that makes other substrates
unsuitable. You can override, but do so knowingly.

→ Confirmed, or do you want to override?
```

**If substrate is "untourable":**

```
Gate 3 of 5 — Substrate

The decision tree found shadow DOM stops in the planned tour.
Shadow DOM is a hard wall — no substrate resolves it.

Affected risk flags: <anchor_readiness["risk_flags"] filtered to shadow_dom>

Options:
  A. Remove the shadow DOM stop(s) from the shortlist, then re-run Gate 3.
  B. Scope the tour around the shadow boundary (tour stops on non-shadow elements only).
  C. Abort — the planned tour cannot be built as scoped.

→ Which option?
```

**Version sub-question (fires only for config-only or nextstep.js paths):**

```
Sub-question (substrate version): What version of driver.js does your app use?
(e.g., "1.3.4", "latest", "not installed")

Config-only output requires a pinned driver.js major version to avoid silent
key-skew. If not v1.x, the SKILL will fall back to drop-in module output (Shape A).
```

**Friction trigger:**
- If the builder overrides the tree's resolution:
  - `friction_type: "default_overridden"`, `confidence: "low"`
  - `symptom`: "Tree resolved <X>; builder chose <Y>."

---

#### Gate 4 — Aha moment

**Purpose:** confirm Phase 1's aha-moment candidate and its position in the tour.

**Position rule (context-dependent — encode this in the gate message):**
- **<= 3 stops**: aha-moment is step 1 (aha-first — immediate payoff).
- **4-5 stops**: aha-moment is placed near the END (orientation-first → earned-payoff arc).
  The emitter places it at position `n-2` (second-to-last) to build context before the payoff.

**What to say:**

```
Gate 4 of 5 — Aha moment

Phase 1 named this as the aha-moment candidate:
  <aha_moment["surface"]> — <aha_moment["reason"]>

Tour has <N> stops. Position rule:
  <IF N <= 3>: Step 1 routes here — immediate payoff.
  <IF N >= 4>: Orientation-first arc — this stop appears near the END (step <N-1> of <N>),
               after context has been built up. The cowpath arc: orient → explore → payoff.

→ Confirmed? Or do you have a different surface in mind?
```

**If the builder wants to override the position rule:**
- Accept it. Note the override. The emitter's `_order_stops_contextually` handles placement;
  if the builder wants aha-first on a 5-stop tour, document the override in build-plan.json
  (`aha_position_override: "first"`) so the emitter can be extended to honor it in a future version.
  For now, document it as a builder note — don't hold up the build.

**If the builder names a different surface:**
- Accept it. Update `aha_moment` in working state. Do not re-litigate.

---

#### Gate 5 — Primary user role

**Purpose:** identify whether the product has role-diverse users that warrant separate tours.

**Read Phase 1's product_summary audience signal first:**
- B2C or single-role product → skip the branching question; confirm single-tour mode.
- B2B or "team / org / workspace" language → ask.

**What to say (B2B / role-diverse path):**

```
Gate 5 of 5 — Primary user role

The app serves multiple user roles. Role-diverse products sometimes need
two separate tours (e.g., setup/admin persona vs day-to-day operator persona).

For this run, what is the primary user role?
  A. Setup / admin — configuring the workspace, inviting teammates, setting up
     integrations.
  B. Day-to-day operator — the end user who runs the core workflow.
  C. Single tour covers both — roles overlap enough to share one tour.

→ Which role, or C?
```

**What to say (B2C / single-role path):**

```
Gate 5 of 5 — Primary user role

Phase 1 reads this as a single-role product. One tour, one audience.

→ Confirmed, or is there a secondary user type worth a separate tour?
```

**Friction trigger:** none at this gate.

---

### 5. Resolve substrate overrides (if Gate 3 produced an override)

If the builder chose a different substrate in Gate 3, re-run `resolve_substrate()` with the updated signals to validate:

- If they picked a React-specific library for a non-React app → block it; explain why; offer the mandatory path.
- If they picked `intro.js` (any casing) → reject it: "Intro.js uses AGPL-3 — it is a commercial license requirement for typical host apps. Not available." Fall back to the tree's resolution.
- Otherwise accept the override and log the friction signal.

### 6. Write build-plan.json

Write to `.vibe-walk/build-plan.json` (create `.vibe-walk/` if absent):

```json
{
  "schema_version": 1,
  "timestamp": "<ISO 8601>",
  "app_path": "<from discovery.json>",
  "mode": "walkthrough",
  "trigger_model": "<auto-once-replay | on-demand | auto-once-no-replay>",
  "first_login_overlays": ["<list from Gate 2 sub-q, or []>"],
  "substrate": "<resolved substrate string>",
  "anchor_attr": "<data-tour | id>",
  "substrate_reason": "<substrate_result['reason']>",
  "substrate_overridden": <true | false>,
  "driver_js_version": "<from version sub-q, or null>",
  "aha_moment": {
    "surface": "<confirmed surface name>",
    "reason": "<reason>"
  },
  "primary_user_role": "<admin | operator | single>",
  "two_tour_branching": <true | false>,
  "ranked_shortlist": "<carried from discovery.json>",
  "anchor_readiness": "<carried from discovery.json>"
}
```

### 7. Invoke Phase 2

Phase 2 runs four steps in the fixed order below. **Do not skip or reorder.**

#### Step 1 — Anchor injection (M4)

Build an `anchorPlan` from the ranked shortlist: one entry per stop, mapping each stop's component file path to its `data-tour` anchor name (derived from the stop's kebab-cased surface name). Run `inject_anchors.js` as a jscodeshift transform via the CLI:

```bash
node_modules/.bin/jscodeshift \
  -t plugins/vibe-walk/scripts/anchors/inject_anchors.js \
  --parser tsx \
  --plan='<JSON.stringify(anchorPlan)>' \
  <component_file_paths...>
```

Collect any `_lastReviewEntries` produced by the transform. If there are review entries — components the codemod could not safely auto-inject — call `emitReviewNeededMd(entries, path.join(app_path, 'REVIEW_NEEDED.md'))` to write the file, then **HALT** with the message below. Do not proceed to step 2.

**HALT message (fires when REVIEW_NEEDED entries exist):**

```
Anchor injection: <N_clean> of <N_total> stops auto-injected. <N_review> require human review.

REVIEW_NEEDED.md written to <app_path>/REVIEW_NEEDED.md.

The build is paused. Resolve every item in that file before continuing:
  — For each item, either add data-tour="<anchor-name>" to the correct element manually,
    or document why the stop should be removed from the tour plan.

When every item is resolved, re-run /vibe-walk:walk. The gates will not re-run;
the build will resume from the anchor pass with the updated file state.
```

If the anchor pass is fully clean (zero review entries, all stops auto-injected), surface a brief confirmation and continue to step 2 immediately.

```
Anchor injection: all <N> stops auto-injected cleanly. Continuing to module emission.
```

#### Step 2 — Emit tour module (M3)

```python
from build.emit_tour_module import emit_module
result = emit_module(build_plan)  # build_plan is the dict written to build-plan.json

# Surface any warnings (D1 cap, split recommendation, etc.)
for w in result["warnings"]:
    print(f"  {w}")

# Write emitted files to the app's tour directory
# Default target: src/components/tour/ (or equivalent for the app's structure)
for rel_path, contents in result["files"].items():
    write_to_app_tour_dir(app_path, rel_path, contents)
```

Surface any D1 cap warnings to the builder before moving to step 3.

#### Step 3 — Wire analytics (M5)

```python
from build.emit_analytics import emit_analytics
analytics_result = emit_analytics(build_plan)

for w in analytics_result["warnings"]:
    print(f"  {w}")

for rel_path, contents in analytics_result["files"].items():
    write_to_app_tour_dir(app_path, rel_path, contents)
```

Merges into the same tour directory as step 2. `tourAnalytics.ts` is designed to import cleanly alongside `spotlightTour.ts` — the wiring guide in `TOUR_ANALYTICS.md` covers the integration.

#### Step 4 — Wire the trigger (M7)

Assemble `host_signals` from discovery context and any signals gathered during Phase 1 / Phase 1.5:

```python
host_signals = {
    "framework":             _infer_framework(app_path),   # reuse from step 2 signal inference
    "first_run_flag_system": _detect_first_run_flag_system(app_path),
    "main_component":        _detect_main_component(app_path),
    "existing_overlays":     build_plan.get("first_login_overlays", []),
}
```

**`_detect_first_run_flag_system(app_path)`** — scan for preferences/settings/prefs files that contain boolean flags with names matching `*seen*`, `*onboard*`, `*welcome*`, `*intro*`:
- Look in `src/hooks/`, `src/store/`, `src/context/`, `src/lib/`, `src/utils/` for files named `*pref*`, `*setting*`, `*user*`, `*onboard*`.
- If found: return `{"file": <rel_path>, "existing_flags": [<list of flag names>]}`.
- If not found: return `None` (triggers localStorage fallback + warning in the emitter).

**`_detect_main_component(app_path)`** — identify the main authenticated/dashboard component:
- For Next.js: `src/app/(authenticated)/page.tsx`, `src/app/dashboard/page.tsx`, or the layout file one level below the root.
- For React SPA: look for `Dashboard.tsx`, `Home.tsx`, `App.tsx` in `src/pages/` or `src/views/`.
- Return `{"file": <rel_path>, "name": <component_name>}` or `None`.

```python
from build.emit_trigger_wiring import emit_trigger_wiring

wiring_result = emit_trigger_wiring(build_plan, host_signals)

for w in wiring_result["warnings"]:
    print(f"  {w}")

# Write WIRING.md to the app's tour directory alongside the other Phase 2 files
for rel_path, contents in wiring_result["files"].items():
    write_to_app_tour_dir(app_path, rel_path, contents)
```

**Apply safe snippets:** if `host_signals["first_run_flag_system"]` was detected and its file is unambiguously a preferences/hook file (not a class component or utility with mixed concerns), apply the flag addition automatically as an additive edit. Otherwise present it to the builder as a snippet to apply manually.

**Human gate — present the wiring guide:**

```
Trigger wiring: WIRING.md written to <app_path>/src/components/tour/WIRING.md.

The plugin has generated exact snippets for the four trigger wiring steps:
  1. Flag addition — extend <flag_file> with hasSeenSpotlight (sibling to <existing_flag>).
  2. Auto-fire effect — place the useEffect in <main_component> (<comp_file>).
  3. Replay control — add the "Take the Tour" button to your help menu or nav.
  4. Permalink trigger (optional) — sibling useEffect that opens the tour on
     ?tour URL params for changelog emails / external "Take the tour" links.

Open WIRING.md for exact placement instructions and the snippets to apply.
This is the one remaining human step — the plugin cannot safely auto-edit
your main component.
```

Surface any `wiring_result["warnings"]` (e.g., no flag system detected, no main component found) before presenting the guide.

### 8. Hand-off message

```
Build complete.

Build plan:   .vibe-walk/build-plan.json
Tour dir:     src/components/tour/

Resolved:
  Mode:       walkthrough (v1)
  Trigger:    <trigger_model>
  Substrate:  <substrate> — anchor: <anchor_attr>
  Aha moment: <aha_moment.surface>
  Role:       <primary_user_role>
  Steps:      <N> of <original_count> (D1 cap: 5 max)

Files written:
  spotlightSteps.ts  — <N>-stop DriveStep[] array, data-tour anchors
  spotlightTour.ts   — driver() runner, showProgress, SSR guard, replay export
  tourAnalytics.ts   — 6-event analytics adapter (replace the stub with your provider)
  TOUR_ANALYTICS.md  — event schema, attribution windows, analytics wiring guide
  WIRING.md          — trigger wiring guide: flag, auto-fire effect, replay, permalink

<if warnings>
Notes:
  <warnings listed here>
</if>

Next: open WIRING.md and follow the four steps to complete trigger wiring:
  1. Add hasSeenSpotlight to <flag_file> (sibling to your existing flags).
  2. Place the auto-fire useEffect in <main_component> (<comp_file>).
  3. Add the "Take the Tour" replay button to your help menu or nav.
  4. (Optional) Add the permalink useEffect for ?tour URL-based deep-links.

Also open TOUR_ANALYTICS.md and replace the trackTourEvent stub with your
analytics provider call.
```

### 9. Friction-logger triggers summary

For `/vibe-walk:walk`, fire `friction-logger.log()` when:

| Condition | friction_type | confidence |
|---|---|---|
| Builder changes the substrate after tree resolved one | `default_overridden` | `low` |
| Builder asks for more than 5 steps at any point | `guardrail_pushed` | `medium` — capture requested count |
| A REVIEW_NEEDED anchor item is declared "can't anchor this" (stop removed from plan) | `anchor_unresolvable` | `high` |

### 10. Session end

Invoke `session-logger.end()` with:
- `sessionUUID` from step 1
- `outcome`: `"completed"` | `"abandoned"` | `"error"`
- `verdict`: `"build"` (carried; always build by this point)
- `key_decisions`: `["substrate: <X>", "trigger: <Y>", "aha: <surface>", "role: <Z>"]`
- `user_pushback`: `true` if the builder overrode the substrate or aha candidate
- `friction_notes`: array of any friction signals captured this run
- `tour_built`: `true` (Phase 2 complete — anchors injected, module emitted, analytics wired, trigger wiring generated)
- `anchor_review_needed`: `true` if the build halted at REVIEW_NEEDED, `false` if fully clean
- `trigger_wiring_warnings`: array of any warnings from emit_trigger_wiring (e.g., no flag system detected)

## Hard rules

- **Run substrate_tree before asking anything.** Never ask what the tree already answers.
- **Never ask multiple gates at once.** Keep them sequential. Gate 2's sub-question is the only in-gate compound — and it fires immediately after Gate 2's main question.
- **Intro.js is not available.** Reject any attempt to select it with a clear reason (AGPL-3).
- **Shadow DOM stops → untourable.** No substrate work-arounds this. Present the options and let the builder decide.
- **The build plan is authoritative.** All three Phase 2 steps read from it. Write it completely before invoking any Phase 2 step.
- **REVIEW_NEEDED halts the build.** Never proceed to step 2 (module emission) if step 1 (anchor injection) produced any review entries. The halt is the contract.
- **D1 is enforced by the emitter.** If emit_module returns warnings, surface them to the builder before presenting the hand-off.
- **Phase 2 order is fixed: anchors → module → analytics → trigger wiring.** Never reorder. Never skip. Analytics (M5) and trigger wiring (M7) both run unconditionally after module emission — they complete in the same session.
- **Never invent a parallel first-run store.** emit_trigger_wiring extends the host's existing onboarding-state system. If none is detected, it emits a localStorage fallback and a warning — present that warning to the builder.
- **The trigger wiring human gate is placement, not approval.** WIRING.md contains exact snippets; the builder's only job is placing them in the right files. Don't re-ask for approval of the trigger model (that was Gate 2).

## Cross-references

- Guide (Sherpa persona + posture): [`../guide/SKILL.md`](../guide/SKILL.md)
- Substrate decision tree: `../../scripts/build/substrate_tree.py`
- Anchor codemod: `../../scripts/anchors/inject_anchors.js` (M4)
- Tour module emitter: `../../scripts/build/emit_tour_module.py` (M3)
- Analytics emitter: `../../scripts/build/emit_analytics.py` (M5)
- Trigger wiring emitter: `../../scripts/build/emit_trigger_wiring.py` (M7)
- Session logger: [`../session-logger/SKILL.md`](../session-logger/SKILL.md)
- Friction logger: [`../friction-logger/SKILL.md`](../friction-logger/SKILL.md)
- Discovery output: `.vibe-walk/discovery.json` (Phase 1 input)
- Build plan output: `.vibe-walk/build-plan.json` (Phase 2 input)
- Conventions (D1–D6): [`../guide/references/conventions.md`](../guide/references/conventions.md)
- Friction triggers: [`../guide/references/friction-triggers.md`](../guide/references/friction-triggers.md)
- Prev phase: [`../discover/SKILL.md`](../discover/SKILL.md) (M1)
