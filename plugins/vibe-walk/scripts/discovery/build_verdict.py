"""
build_verdict.py — Phase 1 discovery core: the "should we build a tour?" verdict.

Pure function. No I/O. No side effects.

The verdict is a FIRST-CLASS output — equal weight to "build."  The plugin
exists to earn the tour before building it. This module is the enforcement
mechanism for that stance.

Decision source: docs/inputs/research/_seed.md §3 Phase 1 step 6.

Accepted signals dict keys
--------------------------
interactive_surface_count : int
    Number of distinct interactive user-facing surfaces discovered.

audience : str
    One of: "b2c", "b2b", "technical", "domain_expert", "power_user".
    "domain_expert" and "power_user" are the don't-build signals.

existing_tour : bool
    True if a same-surface in-product guided tour / spotlight / coachmark /
    walkthrough library is already present. This is the precise don't-build
    signal: stacking a new tour on an existing one trains dismiss-reflex.
    Detected via patterns like *tour*, *spotlight*, *coachmark*, *walkthrough*
    and the presence of tour libraries (driver.js, shepherd, intro, joyride,
    reactour).

existing_onboarding : bool  [BACKWARD-COMPAT ALIAS for existing_tour]
    Legacy name. Still accepted. Treated identically to existing_tour=True.
    New callers should use existing_tour instead. Signup/intro/welcome flows
    that do NOT cover the same surface as the proposed tour should NOT set
    this — use existing_intro_flow instead.

existing_intro_flow : bool
    True if a pre-dashboard signup / intro / flyby / welcome flow is present.
    This is NOT a don't-build signal — a signup flow and a dashboard-orientation
    tour are complementary, not redundant. This signal informs TRIGGER
    SEQUENCING in the walk phase (tour fires AFTER the intro flow completes),
    not the build verdict.

app_category : str
    One of: "web_app", "single_purpose", "cli", "code_surface", "saas", ...
    "single_purpose", "cli", "code_surface" are don't-build signals.

anchor_readiness : str
    One of: "ready", "needs-pass", "none".
    "none" + anchor_pass_refused=True → don't-build.

no_stable_selectors : bool
    True if no stable id/data-* selectors were found anywhere.

anchor_pass_refused : bool
    True if the host has indicated they will not accept an anchor-injection pass.
    Combined with no_stable_selectors → don't-build.

first_run_is_blank_canvas : bool
    True if the first-run surface is blank (no content, no examples).
    → cheaper-first (empty-state / sample-data enhancement first).

high_urgency : bool
    True if the use context is high-urgency (users will not sit through a tour).

untourable_surface_ratio : float
    Fraction of surfaces that are shadow DOM / cross-origin iframe / untourable.
    >= 0.5 → don't-build.

Returns
-------
dict with keys:
    verdict : str  — "build" | "don't-build" | "cheaper-first"
    reasons : list[str]  — non-empty when not "build"; empty list for clean build.
"""

from __future__ import annotations

# Threshold below which "too few surfaces" fires.
_MIN_SURFACES = 5

# Audience values that indicate domain experts / power users.
_EXPERT_AUDIENCES = {"domain_expert", "power_user"}

# App categories that are out of scope or single-purpose.
_DONT_BUILD_CATEGORIES = {"single_purpose", "cli", "code_surface"}

# Ratio threshold above which untourable surfaces "dominate."
_UNTOURABLE_DOMINANCE_THRESHOLD = 0.5


def decide_verdict(signals: dict) -> dict:
    """
    Apply the don't-build condition list and return the verdict + reasons.

    Evaluation order:
      1. cheaper-first conditions (blank canvas)
      2. don't-build conditions (in spec order)
      3. build (clean)

    The cheaper-first verdict is separate from don't-build because it carries a
    concrete positive recommendation (add empty-state / sample-data), whereas
    don't-build is a hard stop.  When both could fire, cheaper-first is checked
    first so the more actionable recommendation surfaces.
    """
    dont_build_reasons: list[str] = []
    cheaper_first_reasons: list[str] = []

    # ------------------------------------------------------------------
    # Cheaper-first: blank canvas first-run
    # ------------------------------------------------------------------
    if signals.get("first_run_is_blank_canvas", False):
        cheaper_first_reasons.append(
            "First-run surface is a blank canvas — empty-state or sample-data "
            "enhancement has higher ROI than a tour here (Linear/Supabase pattern)."
        )

    # ------------------------------------------------------------------
    # Don't-build conditions (from _seed.md §3 step 6)
    # ------------------------------------------------------------------

    # Condition 1: fewer than ~5 interactive surfaces
    count = signals.get("interactive_surface_count", 0)
    if count < _MIN_SURFACES:
        dont_build_reasons.append(
            f"Too few interactive surfaces ({count}) — a tour needs enough distinct "
            f"stops to be worth the cognitive overhead (~{_MIN_SURFACES} minimum)."
        )

    # Condition 2: domain-expert / power-user audience
    audience = signals.get("audience", "b2c")
    if audience in _EXPERT_AUDIENCES:
        dont_build_reasons.append(
            f"Audience is '{audience}' — domain experts and power users find "
            "spotlight tours patronising and frequently dismiss them on sight."
        )

    # Condition 3: existing in-product tour/spotlight already present
    # Fire when:
    #   - existing_tour=True  (the precise new key), OR
    #   - existing_onboarding=True  (legacy key — backward-compat alias)
    # Do NOT fire on existing_intro_flow=True alone — a signup/welcome/flyby
    # flow is complementary to a dashboard-orientation tour, not redundant with it.
    # The Celestia3 case: OnboardingExperience.tsx (birth-data flyby) + WelcomeModal
    # → existing_intro_flow=True, but the dashboard tour is still needed → build.
    existing_tour = signals.get("existing_tour", False) or signals.get("existing_onboarding", False)
    if existing_tour:
        dont_build_reasons.append(
            "An in-product guided tour / spotlight / walkthrough already covers this "
            "surface — stacking a new tour on top trains a dismiss reflex without "
            "adding real value."
        )

    # Condition 4: single-purpose tool
    category = signals.get("app_category", "web_app")
    if category in _DONT_BUILD_CATEGORIES:
        dont_build_reasons.append(
            f"App category is '{category}' — single-purpose tools, CLI products, "
            "and code-surface products are out of scope for spotlight tours."
        )

    # Condition 5: no stable selectors AND anchor pass refused
    no_selectors = signals.get("no_stable_selectors", False)
    pass_refused = signals.get("anchor_pass_refused", False)
    if no_selectors and pass_refused:
        dont_build_reasons.append(
            "No stable selectors (id / data-*) found anywhere AND the host has "
            "declined an anchor-injection pass — tour stops cannot be reliably "
            "targeted without either."
        )

    # Condition 6: high-urgency use context
    if signals.get("high_urgency", False):
        dont_build_reasons.append(
            "High-urgency use context — users will not sit through a guided tour "
            "when they need results immediately."
        )

    # Condition 7: CLI / code-surface product (also covered by category above,
    # but explicit check guards against partial category values)
    if category == "cli" and category not in _DONT_BUILD_CATEGORIES:
        dont_build_reasons.append(  # pragma: no cover  (unreachable given _DONT_BUILD_CATEGORIES)
            "CLI / code-surface product — outside the web-selector substrate scope."
        )

    # Condition 8: untourable surfaces dominate
    ratio = signals.get("untourable_surface_ratio", 0.0)
    if ratio >= _UNTOURABLE_DOMINANCE_THRESHOLD:
        dont_build_reasons.append(
            f"Untourable surfaces (shadow DOM / cross-origin iframe) account for "
            f"{ratio:.0%} of the surface area — tour stops cannot be placed on "
            "the majority of the app."
        )

    # ------------------------------------------------------------------
    # Verdict resolution
    # ------------------------------------------------------------------

    # cheaper-first wins when its condition fires and there are no hard
    # don't-build conditions (blank canvas + a tour-viable app → improve first).
    # When don't-build conditions also fire, don't-build takes precedence
    # because the app has structural blockers beyond just the blank canvas.
    if cheaper_first_reasons and not dont_build_reasons:
        return {"verdict": "cheaper-first", "reasons": cheaper_first_reasons}

    if dont_build_reasons:
        # Include cheaper-first reasons in don't-build output when both fired,
        # so the caller sees the full picture.
        return {"verdict": "don't-build", "reasons": dont_build_reasons + cheaper_first_reasons}

    return {"verdict": "build", "reasons": []}
