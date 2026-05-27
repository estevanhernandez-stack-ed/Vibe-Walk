---
name: discover
description: "Phase 1 autonomous discovery for vibe-walk. Reads the target app's orientation docs, route surface, and component composition to produce a surface inventory, anchor-readiness verdict, ranked stop shortlist, named aha-moment candidate, and — most importantly — the build/don't-build/cheaper-first verdict. Runs entirely without asking the user anything. Writes output to .vibe-walk/discovery.json."
---

# /vibe-walk:discover — Phase 1 autonomous discovery

Read [`../guide/SKILL.md`](../guide/SKILL.md) for the Sherpa persona, posture, and conventions, then follow this command.

## What this command does

Phase 1 runs entirely on the codebase. No questions until the verdict is in.

The goal: earn the right to build a tour — or surface an honest "don't build one here."

```
inventory_surfaces → anchor_readiness → build_verdict
       ↓                   ↓                  ↓
  surface list         readiness         verdict + reasons
  + count              + risk flags      (first-class output)
       ↓
  rank stops → name aha-moment → present to builder
```

## Execution procedure

### 1. Session start

Invoke `session-logger.start("discover", project_dir_basename)`. Store the returned `sessionUUID` — it pairs with the terminal entry and any friction log entries.

### 2. Locate the target app

Read `.vibe-walk/config.json` for `app_path` (set by bootstrap). If absent, ask:

```
I need the path to the app you want to tour. Absolute path or relative to here?
```

### 3. Run inventory_surfaces

```python
from discovery.inventory_surfaces import inventory
result = inventory(app_path)
```

Produces:
- `product_summary` — 1–4 sentence description from the app's orientation docs.
- `surfaces` — list of `{name, file, purpose, view}`.
- `interactive_surface_count` — integer.

If `inventory()` returns an `error` key, stop and surface the error to the builder. Do not continue with partial data.

### 4. Run anchor_readiness

```python
from discovery.anchor_readiness import assess
readiness_result = assess(app_path)
```

Produces:
- `readiness` — `"ready"` | `"needs-pass"` | `"none"`.
- `risk_flags` — list of detected risk signals.

### 5. Run build_verdict

Map the inventory + readiness outputs to the verdict signals dict:

```python
from discovery.build_verdict import decide_verdict

signals = {
    "interactive_surface_count": result["interactive_surface_count"],
    "audience":                  _infer_audience(result["product_summary"]),
    "existing_tour":             _has_existing_tour(app_path),
    "existing_intro_flow":       _has_existing_intro_flow(app_path),
    "app_category":              _infer_app_category(result["product_summary"], app_path),
    "anchor_readiness":          readiness_result["readiness"],
    "no_stable_selectors":       "no_stable_selectors" in readiness_result["risk_flags"],
    "anchor_pass_refused":       False,  # not known yet; can be overridden by builder
    "first_run_is_blank_canvas": _detect_blank_canvas(app_path, result),
    "high_urgency":              _infer_high_urgency(result["product_summary"]),
    "untourable_surface_ratio":  _calc_untourable_ratio(readiness_result),
}

verdict_result = decide_verdict(signals)
```

**Signal inference helpers (inline in the SKILL execution, not separate scripts):**

- `_infer_audience` — scan product_summary for keywords: "expert", "power user", "admin", "developer", "engineer", "analyst" → `"domain_expert"`; "B2B", "team", "enterprise" → `"b2b"`; else `"b2c"`.
- `_has_existing_tour` — scan app_path for files matching `*tour*`, `*spotlight*`, `*coachmark*`, `*walkthrough*` (case-insensitive), OR `package.json` containing tour library names (`driver.js`, `shepherd.js`, `react-joyride`, `intro.js`, `reactour`). Skip directories: `node_modules`, `.git`, `.agent`. If found → `True` (sets `existing_tour` → fires don't-build Condition 3). **Do NOT match on `*onboard*`, `*welcome*`, `*guide*`, `*intro*`, `*flyby*` — those are signup/intro flows that are complementary to a tour, not redundant.**
- `_has_existing_intro_flow` — scan app_path for files matching `*onboard*`, `*welcome*`, `*intro*`, `*guide*`, `*flyby*` (case-insensitive). Skip directories: `node_modules`, `.git`, `.agent`. If found → `True` (sets `existing_intro_flow` — used by the walk phase for trigger sequencing, NOT a don't-build signal). **Example: Celestia3's `OnboardingExperience.tsx` + `WelcomeModal.tsx` → `existing_intro_flow=True`, `existing_tour=False` → verdict is still `build`.**
- `_infer_app_category` — "CLI", "command-line", "terminal" in summary → `"cli"`; "calculator", "converter", "generator" + single page → `"single_purpose"`; else `"web_app"`.
- `_detect_blank_canvas` — surface list contains a canvas/whiteboard/drawing surface AND no data-seeded content found → `True`.
- `_infer_high_urgency` — "emergency", "incident", "real-time alert", "critical" in summary → `True`.
- `_calc_untourable_ratio` — count shadow_dom + cross_origin_iframe flags; divide by total surface count. If either flag present and < 5 surfaces → 0.6.

### 6. Rank candidate stops

From the surface list, select 8–12 stops ranked by **centrality-to-first-success**:

1. **Step 1 candidate** = the surface most directly tied to the aha moment (the single action that makes a new user say "this is worth it"). Pick the most-linked-to action surface (look for `button`, `form`, or primary CTA in the file).
2. **Rank remaining surfaces** by:
   - Is it on the critical first-run path? (pages/components loaded on first login)
   - Does it have interactive elements? (buttons, forms, inputs)
   - Is it page-level vs component-level? (prefer pages for early steps)
   - Does its name suggest value delivery? (chart, dashboard, report, export, share)

Prune surfaces that are navigation-only (header/footer with no unique CTA), utility helpers, or loading states. Cap the shortlist at 12.

### 7. Name the aha-moment candidate

State it explicitly:

```
Aha-moment candidate: <ComponentName> — <one sentence why this is the first-success moment>
```

This becomes the tour's **emotional payoff stop**. Its placement depends on tour length:
- **<= 3 stops**: aha-moment is step 1 (immediate payoff — short tours benefit from it).
- **4-5 stops**: aha-moment is placed near the END (earned-payoff arc — build context first).

The Phase 1.5 Gate 4 confirms this placement with the builder.

### 8. Write discovery.json

Write to `.vibe-walk/discovery.json` (create `.vibe-walk/` if absent):

```json
{
  "schema_version": 1,
  "timestamp": "<ISO 8601>",
  "app_path": "<absolute path>",
  "product_summary": "<from inventory>",
  "surfaces": [...],
  "interactive_surface_count": <int>,
  "anchor_readiness": {
    "readiness": "<ready|needs-pass|none>",
    "risk_flags": [...]
  },
  "ranked_shortlist": [
    {"name": "<surface name>", "file": "<path>", "rank_reason": "<why>"}
  ],
  "aha_moment": {
    "surface": "<name>",
    "reason": "<one sentence>"
  },
  "verdict": "<build|don't-build|cheaper-first>",
  "verdict_reasons": [...]
}
```

### 9. Present the verdict

**The verdict is first-class.** Present it with the same weight whether it's "build" or "don't-build." Never bury it.

#### Format — "build"

```
Verdict: BUILD A TOUR

App: <product_summary — first sentence>
Surfaces: <N> interactive surfaces found.
Anchor readiness: <ready|needs-pass|none> (<risk flags if any>)

Aha-moment candidate: <name> — <reason>

Ranked stop shortlist (<N> candidates):
  1. <name> — <rank_reason>
  2. <name> — <rank_reason>
  ...

Next: /vibe-walk:walk — run the 5 interview gates and build the tour.
```

#### Format — "don't-build"

```
Verdict: DON'T BUILD A TOUR HERE

<reason 1>
<reason 2>
...

A spotlight tour layered on this app is unlikely to help — and may actively
train users to dismiss future guidance.

Next options:
  - Address the blocking condition(s) above, then re-run /vibe-walk:discover --refresh.
  - Accept the verdict and invest elsewhere.
  - Or override — run /vibe-walk:walk anyway. The verdict is advisory; the walk
    SKILL will surface these reasons and ask once before proceeding. Your read
    on the app beats the plugin's heuristic when you have context the plugin lacks.
```

#### Format — "cheaper-first"

```
Verdict: DO SOMETHING CHEAPER FIRST

<reason>

Recommended: add empty-state design or sample-data seeding before building a tour.
The blank-canvas first-run problem (Linear/Supabase pattern) has higher ROI than
a spotlight tour when users have nothing to react to yet.

Next options:
  - Implement the cheaper move first, then re-run /vibe-walk:discover --refresh.
  - Or override — run /vibe-walk:walk anyway. The walk SKILL will surface this
    verdict and ask once before proceeding. Useful when the cheaper move is
    out of scope or you've already planned it as a follow-up.
```

### 10. Friction-logger triggers

Invoke `friction-logger.log()` if:

- **Builder overrides the verdict** (e.g., on `don't-build` or `cheaper-first`, chooses to proceed via `/vibe-walk:walk`):
  - `friction_type: "verdict_overridden"`, `confidence: "high"`
  - `symptom`: "Agent verdict was <X>, builder chose to proceed with build."
  - This is the **highest-signal friction event** in the plugin. The verdict is advisory — overrides are legitimate, not failures. The signal exists so `/vibe-walk:evolve-walk` can track whether overrides correlate with successful or failed tours over time and tune the verdict's signal weights accordingly.

- **Builder rejects the ranked shortlist wholesale** ("none of these stops are right"):
  - `friction_type: "shortlist_rejected"`, `confidence: "medium"`

### 11. Session end

Invoke `session-logger.end()` with:
- `sessionUUID` from step 1
- `outcome`: `"completed"` | `"abandoned"` | `"error"`
- `verdict`: the verdict string
- `key_decisions`: `["verdict: <X>", "aha: <surface name>", "<N> candidate stops ranked"]`
- `user_pushback`: `true` if the builder overrode the verdict or shortlist
- `friction_notes`: array of any friction signals captured
- `tour_built`: `false` (discovery never builds)
- `anchor_review_needed`: `null`

## Hard rules

- **Phase 1 asks nothing.** The five interview gates (mode, trigger, substrate, aha, role) are Phase 1.5. Don't ask them here.
- **Present the verdict first, always.** Don't bury it after the surface list.
- **Don't nudge toward "build."** A don't-build verdict is a success — it saved the builder from wasted work.
- **If inventory() errors, stop.** Partial data produces a meaningless verdict.
- **discovery.json is authoritative.** The bare router reads it to determine next step. Write it completely before presenting output.

## Cross-references

- Guide (Sherpa persona + posture): [`../guide/SKILL.md`](../guide/SKILL.md)
- Session logger: [`../session-logger/SKILL.md`](../session-logger/SKILL.md)
- Friction logger: [`../friction-logger/SKILL.md`](../friction-logger/SKILL.md)
- Scripts: `../../scripts/discovery/inventory_surfaces.py`, `anchor_readiness.py`, `build_verdict.py`
- Discovery output: `.vibe-walk/discovery.json`
- Conventions (D1–D6): [`../guide/references/conventions.md`](../guide/references/conventions.md)
- Friction triggers: [`../guide/references/friction-triggers.md`](../guide/references/friction-triggers.md)
- Next phase: [`../walk/SKILL.md`](../walk/SKILL.md) (M2)
