"""
emit_trigger_wiring.py — M7 trigger wiring emitter.

Pure function. No I/O. No side effects.

emit_trigger_wiring(build_plan: dict, host_signals: dict) -> dict
  Returns {
    "files":       {"WIRING.md": "<contents>"},
    "snippets":    {"flag": str, "auto_fire_effect": str, "replay": str},
    "wiring_guide": str,   # mirror of WIRING.md content (convenience)
    "warnings":    [str],
  }

Generates the trigger integration for the host's framework (React/Next first-class).

Three wiring artifacts:

  1. flag snippet
     Extends the host's existing onboarding-state system (from
     host_signals["first_run_flag_system"]) by adding a sibling flag
     (hasSeenSpotlight) alongside the existing ones.
     If no existing system is detected → minimal localStorage fallback + warning.

  2. auto_fire_effect snippet
     A React useEffect that fires startSpotlightTour(onDone) once, gated on:
       - trigger model is auto-once-replay OR auto-once-no-replay
       - onboarding complete AND welcome/intro overlay(s) dismissed
       - hasSeenSpotlight flag unset
     onDone sets the flag. Empty/N/A when trigger_model == "on-demand".

  3. replay snippet
     A persistent, ungated <button onClick={replaySpotlightTour}> JSX control.
     No flag check. Fires any time the user wants a replay.

  4. WIRING.md
     Precise host-specific placement guide: which file to add the flag to,
     where to place the effect (the host's main authenticated/dashboard component),
     where to add the replay control.

host_signals keys:
  framework            (str)  — e.g. "react", "next-app-router", "react-spa"
  first_run_flag_system (dict | None)
      {
        "file":           str   — path to the file owning first-run flags
        "existing_flags": list  — names of existing flags (e.g. ["hasSeenWelcome"])
      }
      None if no existing system was detected.
  main_component (dict | None)
      {
        "file": str  — path to the main authenticated/dashboard component
        "name": str  — component name
      }
      None if not detected.
  existing_overlays (list)  — names of overlays that fire on first login

Decision constraints honored:
  _seed.md §3 Phase 2 item 6 — "reuse the host's existing onboarding-state system —
    never invent a parallel store"; trigger model auto-once+replay; persistent ungated replay.
  overlay-sequencing rule — queue behind welcome modal, not stack.

Source: docs/inputs/research/_seed.md §3 Phase 2, M7 spec.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The new sibling flag name this plugin adds
_SIBLING_FLAG = "hasSeenSpotlight"
_SIBLING_FLAG_SETTER = "setHasSeenSpotlight"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def emit_trigger_wiring(build_plan: dict, host_signals: dict) -> dict:
    """
    Emit trigger-wiring snippets + WIRING.md from a resolved build-plan and
    host_signals.

    Parameters
    ----------
    build_plan : dict
        The fully resolved .vibe-walk/build-plan.json. Required keys:
        trigger_model, first_login_overlays, app_path.
    host_signals : dict
        Detection output from the SKILL's discovery pass. Keys documented in
        module docstring.

    Returns
    -------
    dict:
        "files"       — {"WIRING.md": <contents>}
        "snippets"    — {"flag": str, "auto_fire_effect": str, "replay": str}
        "wiring_guide" — str (same as files["WIRING.md"])
        "warnings"    — list of warning strings (empty when fully clean)
    """
    warnings: list[str] = []

    trigger_model: str = build_plan.get("trigger_model", "auto-once-replay")
    first_login_overlays: list = build_plan.get("first_login_overlays", [])

    flag_system: Optional[dict] = host_signals.get("first_run_flag_system")
    main_component: Optional[dict] = host_signals.get("main_component")
    existing_overlays: list = host_signals.get("existing_overlays", [])
    framework: str = host_signals.get("framework", "react")

    # Merge overlays from build-plan + host_signals for completeness
    all_overlays = list(dict.fromkeys(first_login_overlays + existing_overlays))

    # -------------------------------------------------------------------------
    # 1. Flag snippet
    # -------------------------------------------------------------------------
    flag_snippet, flag_warnings = _emit_flag_snippet(flag_system)
    warnings.extend(flag_warnings)

    # -------------------------------------------------------------------------
    # 2. Auto-fire effect snippet
    # -------------------------------------------------------------------------
    auto_fire_snippet = _emit_auto_fire_effect(
        trigger_model, flag_system, all_overlays, framework
    )

    # -------------------------------------------------------------------------
    # 3. Replay snippet
    # -------------------------------------------------------------------------
    replay_snippet = _emit_replay_snippet()

    # -------------------------------------------------------------------------
    # 4. WIRING.md
    # -------------------------------------------------------------------------
    if main_component is None:
        warnings.append(
            "No main component detected in host_signals. "
            "The auto-fire effect placement in WIRING.md is best-effort — "
            "identify your main authenticated/dashboard component and place "
            "the effect there."
        )

    wiring_md = _emit_wiring_md(
        build_plan, host_signals, flag_system, main_component, all_overlays, trigger_model
    )

    snippets = {
        "flag":             flag_snippet,
        "auto_fire_effect": auto_fire_snippet,
        "replay":           replay_snippet,
    }

    return {
        "files":        {"WIRING.md": wiring_md},
        "snippets":     snippets,
        "wiring_guide": wiring_md,
        "warnings":     warnings,
    }


# ---------------------------------------------------------------------------
# Flag snippet emitter
# ---------------------------------------------------------------------------

def _emit_flag_snippet(flag_system: Optional[dict]) -> tuple[str, list[str]]:
    """
    Emit the flag snippet. If flag_system is detected, emit a sibling addition.
    If None, emit a localStorage fallback and a warning.
    """
    warnings: list[str] = []

    if flag_system is None:
        # Fallback: minimal localStorage implementation
        warnings.append(
            "No first-run flag system detected in the host app. "
            "Emitting a localStorage fallback for the tour-seen flag. "
            "Recommendation: integrate hasSeenSpotlight into your existing "
            "user-preferences or onboarding-state store once one is identified."
        )
        snippet = _localStorage_flag_snippet()
        return snippet, warnings

    # Extending the existing system
    flag_file = flag_system.get("file", "your preferences file")
    existing_flags = flag_system.get("existing_flags", [])
    existing_sample = existing_flags[0] if existing_flags else "hasSeenWelcome"

    snippet = _sibling_flag_snippet(flag_file, existing_sample, existing_flags)
    return snippet, warnings


def _sibling_flag_snippet(flag_file: str, existing_sample: str, all_existing: list) -> str:
    """
    Emit a snippet showing how to add hasSeenSpotlight as a sibling flag
    alongside the existing ones in the detected flag system.
    """
    existing_list = ", ".join(all_existing) if all_existing else existing_sample
    return f"""\
// Add {_SIBLING_FLAG} as a sibling flag alongside {existing_list}
// File: {flag_file}
//
// In your preferences type / interface, add:
//   {_SIBLING_FLAG}: boolean;
//
// In your initial state / default values, add alongside {existing_sample}:
//   {_SIBLING_FLAG}: false,
//
// Expose a setter (alongside existing setters):
//   const [{_SIBLING_FLAG}, {_SIBLING_FLAG_SETTER}] = useState<boolean>(
//     prefs?.{_SIBLING_FLAG} ?? false
//   );
//   // or, for a reducer/store pattern:
//   // {_SIBLING_FLAG_SETTER}(true) updates the same prefs object
//
// This extends {flag_file} — not a new store.
// Pattern: same as {existing_sample} but for the spotlight tour.
"""


def _localStorage_flag_snippet() -> str:
    """Emit a minimal localStorage fallback for the tour-seen flag."""
    return f"""\
// hasSeenSpotlight — localStorage fallback
// (No first-run flag system was detected. Integrate into your prefs store
//  once identified — replace this with a sibling flag alongside your existing ones.)

const SPOTLIGHT_FLAG_KEY = 'hasSeenSpotlight';

export function getHasSeenSpotlight(): boolean {{
  try {{
    return localStorage.getItem(SPOTLIGHT_FLAG_KEY) === 'true';
  }} catch {{
    return false; // SSR / private-browsing guard
  }}
}}

export function setHasSeenSpotlight(value: boolean): void {{
  try {{
    localStorage.setItem(SPOTLIGHT_FLAG_KEY, String(value));
  }} catch {{
    // SSR / storage-quota guard — fail silently
  }}
}}
"""


# ---------------------------------------------------------------------------
# Auto-fire effect emitter
# ---------------------------------------------------------------------------

def _emit_auto_fire_effect(
    trigger_model: str,
    flag_system: Optional[dict],
    overlays: list,
    framework: str,
) -> str:
    """
    Emit the auto-fire useEffect snippet.
    Returns empty string for on-demand trigger model.
    """
    if trigger_model == "on-demand":
        return ""  # On-demand: no auto-fire; only the replay control is needed

    # Detect overlay gating condition
    overlay_gate = _overlay_gate_expression(overlays)

    # Detect flag getter pattern
    if flag_system is not None:
        flag_check = f"!{_SIBLING_FLAG}"
        flag_setter_call = f"{_SIBLING_FLAG_SETTER}(true);"
        flag_dep = _SIBLING_FLAG
        import_note = (
            f"// Import {_SIBLING_FLAG} and {_SIBLING_FLAG_SETTER} from your preferences hook."
        )
    else:
        flag_check = "!getHasSeenSpotlight()"
        flag_setter_call = "setHasSeenSpotlight(true);"
        flag_dep = "/* localStorage — no dep needed */"
        import_note = (
            "// Import getHasSeenSpotlight and setHasSeenSpotlight from your "
            "trigger-wiring module."
        )

    overlay_dep = _overlay_dep_name(overlays) if overlays else None
    dep_array = _build_dep_array(flag_system, overlay_dep)

    overlay_comment = ""
    if overlays:
        overlay_names = ", ".join(overlays)
        overlay_comment = (
            f"  // Overlay-sequencing: queue behind {overlay_names} — don't stack.\n"
            f"  // Fire only after all first-login overlays are dismissed.\n"
        )

    return f"""\
{import_note}
// Import startSpotlightTour from './spotlightTour' (emitted by vibe-walk).
// Place this hook call inside your main authenticated/dashboard component.

useEffect(() => {{
{overlay_comment}\
  // Gate 1: onboarding complete + overlays dismissed
  // Gate 2: spotlight flag not yet set
  if ({overlay_gate} && {flag_check}) {{
    startSpotlightTour(() => {{
      // onDone: set the flag so the tour never auto-fires again
      {flag_setter_call}
    }});
  }}
}}, [{dep_array}]);
"""


def _overlay_gate_expression(overlays: list) -> str:
    """
    Build the overlay-dismissed gate expression.
    If overlays were detected, references a boolean prop/state for the overlay dismissal.
    Falls back to a generic isOnboardingComplete condition.
    """
    if not overlays:
        return "isOnboardingComplete"

    # Use the first overlay's name as the primary gate (the blocking one)
    primary = overlays[0]
    # Convert WelcomeModal → isWelcomeModalDismissed
    camel = _to_camel_lower(primary)
    return f"isOnboardingComplete && !{camel}Visible"


def _overlay_dep_name(overlays: list) -> Optional[str]:
    """Derive the dependency name for the useEffect dep array from the first overlay."""
    if not overlays:
        return None
    primary = overlays[0]
    camel = _to_camel_lower(primary)
    return f"{camel}Visible"


def _build_dep_array(flag_system: Optional[dict], overlay_dep: Optional[str]) -> str:
    """Build the useEffect dependency array content."""
    deps = []
    if flag_system is not None:
        deps.append(_SIBLING_FLAG)
    else:
        deps.append("/* localStorage — stateless */")
    if overlay_dep:
        deps.append(overlay_dep)
    deps.append("isOnboardingComplete")
    return ", ".join(deps)


# ---------------------------------------------------------------------------
# Replay snippet emitter
# ---------------------------------------------------------------------------

def _emit_replay_snippet() -> str:
    """
    Emit a persistent, ungated 'Take the Tour' replay control.
    No flag check. Calls replaySpotlightTour on click.
    """
    return """\
{/* Replay entry point — persistent, ungated. */}
{/* Place in your help menu, settings panel, or nav footer. */}
{/* No flag check — fires any time the user wants a replay. */}
<button
  onClick={replaySpotlightTour}
  className="take-the-tour-btn"
  type="button"
>
  Take the Tour
</button>
"""


# ---------------------------------------------------------------------------
# WIRING.md emitter
# ---------------------------------------------------------------------------

def _emit_wiring_md(
    build_plan: dict,
    host_signals: dict,
    flag_system: Optional[dict],
    main_component: Optional[dict],
    overlays: list,
    trigger_model: str,
) -> str:
    """
    Emit a precise, host-specific placement guide for the trigger wiring.
    """
    app_path = build_plan.get("app_path", "your app")
    app_name = Path(app_path).name if app_path else "your app"

    # Flag section
    if flag_system:
        flag_file = flag_system.get("file", "your preferences file")
        existing_flags = flag_system.get("existing_flags", [])
        existing_sample = existing_flags[0] if existing_flags else "hasSeenWelcome"
        flag_section = f"""\
## Step 1 — Add the first-run flag

**File:** `{flag_file}`

Add `{_SIBLING_FLAG}` as a sibling flag alongside your existing flags \
({', '.join(existing_flags) if existing_flags else existing_sample}).

This extends your current onboarding-state system — not a new store.
Apply the `flag` snippet from `snippets["flag"]` to this file.

```
// In your preferences type:
{_SIBLING_FLAG}: boolean;

// In your default/initial state, alongside {existing_sample}:
{_SIBLING_FLAG}: false,
```
"""
    else:
        flag_section = f"""\
## Step 1 — Add the first-run flag

**No existing flag system detected.** Using a localStorage fallback.

Apply the `flag` snippet from `snippets["flag"]` — it creates
`getHasSeenSpotlight()` and `setHasSeenSpotlight()` helpers.

**Recommendation:** once you identify your onboarding-state store, migrate
this flag to a sibling position alongside your existing flags. Never maintain
two parallel stores long-term.
"""

    # Effect placement section
    if main_component:
        comp_name = main_component.get("name", "your main component")
        comp_file = main_component.get("file", "your main component file")
        effect_section = f"""\
## Step 2 — Place the auto-fire effect

**Component:** `{comp_name}`
**File:** `{comp_file}`

This is your main authenticated/dashboard component — the right place for the
auto-fire effect because it mounts once per session after authentication.

Apply the `auto_fire_effect` snippet from `snippets["auto_fire_effect"]`:
  1. Import `startSpotlightTour` from `./spotlightTour`.
  2. Import `{_SIBLING_FLAG}` and `{_SIBLING_FLAG_SETTER}` from your preferences hook.
  3. Add the `useEffect` call inside `{comp_name}` (not in a child component).

**Human gate:** confirm the placement — this is the one edit the plugin cannot
safely auto-apply. Once confirmed, the effect fires exactly once on first visit.
"""
    else:
        effect_section = f"""\
## Step 2 — Place the auto-fire effect

**Main component: not detected.** Place the auto-fire effect in the component
that mounts once per session after authentication — typically your main dashboard
or home component.

Apply the `auto_fire_effect` snippet from `snippets["auto_fire_effect"]`:
  1. Import `startSpotlightTour` from `./spotlightTour`.
  2. Import your flag getter/setter.
  3. Add the `useEffect` call inside your main authenticated component.

**Human gate:** identify and confirm the target component before applying.
"""

    # Overlay sequencing note
    if overlays:
        overlay_names = ", ".join(overlays)
        overlay_note = f"""\

**Overlay sequencing:** the effect gates on `{overlay_names}` being dismissed.
Queue behind, don't stack — the tour fires only after all first-login overlays
have closed AND the user has completed a qualifying first action.
"""
    else:
        overlay_note = ""

    # Replay section
    replay_section = f"""\
## Step 3 — Add the replay control

**Where:** any persistent surface the user can reach at any time — help menu,
settings panel, navigation footer, or a floating "?" button.

Apply the `replay` snippet from `snippets["replay"]`. It renders a
`<button onClick={{replaySpotlightTour}}>Take the Tour</button>` control.

Import `replaySpotlightTour` from `./spotlightTour` at the top of the file
where you add this control.

This control is **ungated** — no flag check, no onboarding requirement.
It fires any time the user wants a replay.
"""

    # Analytics note
    analytics_note = """\
## Step 4 — Wire analytics (see TOUR_ANALYTICS.md)

Open `TOUR_ANALYTICS.md` and replace the `trackTourEvent` stub with your
analytics provider call. This is the remaining wiring step alongside the
effect + replay placement above.
"""

    # On-demand note
    on_demand_note = ""
    if trigger_model == "on-demand":
        on_demand_note = """\
> **Trigger model: on-demand.** No auto-fire effect is needed — the replay
> control in Step 3 is the only entry point. Skip Step 2.

"""

    return f"""\
# WIRING.md — Trigger wiring guide for {app_name}

Generated by vibe-walk M7. Apply these three steps to complete the tour wiring.
The plugin has generated exact snippets; your job is to place them.

{on_demand_note}\
{flag_section}
{effect_section}{overlay_note}
{replay_section}
{analytics_note}
---

**After applying all steps:** the tour fires once on first visit (gated on
onboarding + overlay dismissal), sets the flag so it never re-fires, and
exposes a persistent replay control.

Files from this Phase 2 run:
  - `spotlightSteps.ts` — tour step definitions
  - `spotlightTour.ts` — `startSpotlightTour()` + `replaySpotlightTour`
  - `tourAnalytics.ts` — 6-event analytics adapter
  - `TOUR_ANALYTICS.md` — event schema + attribution windows
  - `WIRING.md` — this file
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_camel_lower(name: str) -> str:
    """
    Convert PascalCase or kebab-case to lowerCamelCase.
    'WelcomeModal' → 'welcomeModal'
    'welcome-modal' → 'welcomeModal'
    """
    if "-" in name:
        parts = name.split("-")
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])
    if name and name[0].isupper():
        return name[0].lower() + name[1:]
    return name
