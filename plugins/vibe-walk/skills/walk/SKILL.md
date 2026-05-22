---
name: vibe-walk:walk
description: "Phase 1.5 interview gates for vibe-walk. Reads .vibe-walk/discovery.json, resolves the tour substrate via the decision tree (substrate_tree.py), then runs five interview gates — mode, trigger model, substrate confirmation, aha moment, and primary user role — asking only to confirm or resolve overrides. Writes resolved answers to .vibe-walk/build-plan.json. Hands off to Phase 2 (M3, not yet built)."
---

# /vibe-walk:walk — Phase 1.5 interview gates

Read [`../guide/SKILL.md`](../guide/SKILL.md) for the Sherpa persona, posture, and conventions, then follow this command.

## What this command does

Phase 1.5 is the interview between discovery and build. Five gates. The substrate decision tree runs before any question is asked — never ask what the tree already answers. Ask only to confirm the tree's resolution or to resolve an explicit override condition.

At the end of this SKILL, the resolved answers land in `.vibe-walk/build-plan.json`. **Phase 2 (the actual tour generation) is built in M3.** For now this SKILL writes the plan and hands off gracefully.

```
read discovery.json
  → run substrate_tree.resolve_substrate()
    → Gate 1: Mode
    → Gate 2: Trigger model + overlay-sequencing sub-q
    → Gate 3: Substrate — confirm or resolve override
    → Gate 4: Aha moment — confirm M1 candidate
    → Gate 5: Primary user role
      → write build-plan.json
        → hand off (Phase 2 not yet built — M3)
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
    "needs_async_mount_wait":     "dynamic_mount" in anchor_readiness["risk_flags"],
    "heavily_animated":           False,      # unknown until Gate 3 override
    "wants_idiomatic_react":      False,      # unknown until Gate 3 override
    "bundle_size_sensitive":      False,      # unknown until Gate 3 override
}

substrate_result = resolve_substrate(signals)
```

**Signal inference helpers (inline in SKILL execution, not separate scripts):**

- `_infer_framework` — scan app root for config files and package.json (see step 2). Returns a framework string.
- `_detect_multi_route` — if `ranked_shortlist` items span more than one distinct `view` value → `True`. If `view` is missing or all items share one view → `False`.

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
(welcome modal, cookie banner, terms prompt, free-trial nudge, etc.)

Knowing the sequence prevents stacking — the tour should queue behind the welcome
modal AND a qualifying first action, not fire on raw modal-close.

→ List anything that fires on first visit, or "none."
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

**Purpose:** confirm Phase 1's aha-moment candidate. This becomes step 1 of the tour.

**What to say:**

```
Gate 4 of 5 — Aha moment

Phase 1 named this as the aha-moment candidate:
  <aha_moment["surface"]> — <aha_moment["reason"]>

Step 1 of the tour routes here. Everything before it is approach; this is the payoff.

→ Confirmed? Or do you have a different surface in mind?
```

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

### 7. Hand-off message

```
Build plan written to .vibe-walk/build-plan.json.

Resolved:
  Mode:       walkthrough (v1)
  Trigger:    <trigger_model>
  Substrate:  <substrate> — anchor: <anchor_attr>
  Aha moment: <aha_moment.surface>
  Role:       <primary_user_role>

Phase 2 (tour generation) is coming in M3. When it lands, run /vibe-walk:walk again
and it will pick up from this build plan automatically.
```

### 8. Friction-logger triggers summary

For `/vibe-walk:walk`, fire `friction-logger.log()` when:

| Condition | friction_type | confidence |
|---|---|---|
| Builder changes the substrate after tree resolved one | `default_overridden` | `low` |
| Builder asks for more than 5 steps at any point | `guardrail_pushed` | `medium` — capture requested count |
| A REVIEW_NEEDED anchor item (future M4) is declared "can't anchor this" | `anchor_unresolvable` | `high` |

### 9. Session end

Invoke `session-logger.end()` with:
- `sessionUUID` from step 1
- `outcome`: `"completed"` | `"abandoned"` | `"error"`
- `verdict`: `"build"` (carried; always build by this point)
- `key_decisions`: `["substrate: <X>", "trigger: <Y>", "aha: <surface>", "role: <Z>"]`
- `user_pushback`: `true` if the builder overrode the substrate or aha candidate
- `friction_notes`: array of any friction signals captured this run
- `tour_built`: `false` (M3 not yet built)
- `anchor_review_needed`: `null` (M4 not yet built)

## Hard rules

- **Run substrate_tree before asking anything.** Never ask what the tree already answers.
- **Never ask multiple gates at once.** Keep them sequential. Gate 2's sub-question is the only in-gate compound — and it fires immediately after Gate 2's main question.
- **Intro.js is not available.** Reject any attempt to select it with a clear reason (AGPL-3).
- **Shadow DOM stops → untourable.** No substrate work-arounds this. Present the options and let the builder decide.
- **The build plan is authoritative.** Phase 2 (M3) reads it. Write it completely before presenting the hand-off message.
- **Don't run Phase 2 here.** M3 is not yet built. The SKILL ends at the build-plan write + hand-off message.

## Cross-references

- Guide (Sherpa persona + posture): [`../guide/SKILL.md`](../guide/SKILL.md)
- Substrate decision tree: `../../scripts/build/substrate_tree.py`
- Session logger: [`../session-logger/SKILL.md`](../session-logger/SKILL.md)
- Friction logger: [`../friction-logger/SKILL.md`](../friction-logger/SKILL.md)
- Discovery output: `.vibe-walk/discovery.json` (Phase 1 input)
- Build plan output: `.vibe-walk/build-plan.json` (Phase 2 input)
- Conventions (D1–D6): [`../guide/references/conventions.md`](../guide/references/conventions.md)
- Friction triggers: [`../guide/references/friction-triggers.md`](../guide/references/friction-triggers.md)
- Prev phase: [`../discover/SKILL.md`](../discover/SKILL.md) (M1)
- Next phase: Phase 2 generator (M3, not yet built)
