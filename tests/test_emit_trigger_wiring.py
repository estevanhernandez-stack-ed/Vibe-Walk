"""
TDD tests for emit_trigger_wiring.emit_trigger_wiring().

M7 — Trigger wiring: first-run flag + auto-fire effect + replay entry point.

Covers:
  - Given a build-plan + host_signals with an existing flag system (hasSeenWelcome),
    the flag snippet EXTENDS it with a sibling flag (not a parallel store).
  - The auto-fire effect snippet gates on onboarding-complete + overlay-dismissed
    + flag-unset, and sets the flag in onDone.
  - The replay snippet calls replaySpotlightTour and is ungated.
  - WIRING.md names the flag file, effect placement (main component), and replay placement.
  - host_signals with NO existing flag system → localStorage fallback + a warning.
  - Return shape: {"files": {...}, "snippets": {...}, "wiring_guide": str, "warnings": [...]}

Source: docs/inputs/research/_seed.md §3 Phase 2 (items 4, 6), M7 spec.
"""
import pytest
import sys
from pathlib import Path

# conftest.py adds SCRIPTS_ROOT to sys.path — build/ is a sub-package of that
from build.emit_trigger_wiring import emit_trigger_wiring


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _build_plan_with_overlays() -> dict:
    """Build-plan with trigger model auto-once-replay and a first-login overlay."""
    return {
        "schema_version": 1,
        "app_path": "/projects/my-app",
        "substrate": "driver.js",
        "anchor_attr": "data-tour",
        "trigger_model": "auto-once-replay",
        "first_login_overlays": ["WelcomeModal"],
        "aha_moment": {
            "surface": "project-dashboard",
            "reason": "First view where value is tangible.",
        },
        "ranked_shortlist": [
            {"name": "project-dashboard", "anchor": "project-dashboard", "rank": 1},
            {"name": "create-project",    "anchor": "create-project",    "rank": 2},
        ],
    }


def _host_signals_with_flag_system() -> dict:
    """host_signals with a detected first-run flag system (hasSeenWelcome)."""
    return {
        "framework": "react",
        "first_run_flag_system": {
            "file": "src/hooks/useUserPreferences.ts",
            "existing_flags": ["hasSeenWelcome", "hasCompletedOnboarding"],
        },
        "main_component": {
            "file": "src/components/Dashboard.tsx",
            "name": "Dashboard",
        },
        "existing_overlays": ["WelcomeModal"],
    }


def _host_signals_no_flag_system() -> dict:
    """host_signals with NO detected first-run flag system."""
    return {
        "framework": "react",
        "first_run_flag_system": None,
        "main_component": {
            "file": "src/app/page.tsx",
            "name": "HomePage",
        },
        "existing_overlays": [],
    }


def _host_signals_no_main_component() -> dict:
    """host_signals with NO detected main component."""
    return {
        "framework": "react",
        "first_run_flag_system": {
            "file": "src/store/userPrefs.ts",
            "existing_flags": ["hasSeenWelcome"],
        },
        "main_component": None,
        "existing_overlays": [],
    }


# ---------------------------------------------------------------------------
# Return-shape tests
# ---------------------------------------------------------------------------

class TestReturnShape:
    def test_returns_dict(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        assert "files" in result
        assert "snippets" in result
        assert "wiring_guide" in result
        assert "warnings" in result

    def test_files_is_dict(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        assert isinstance(result["files"], dict)

    def test_snippets_is_dict(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        assert isinstance(result["snippets"], dict)

    def test_wiring_guide_is_str(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        assert isinstance(result["wiring_guide"], str)

    def test_warnings_is_list(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        assert isinstance(result["warnings"], list)

    def test_emits_wiring_md_file(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        assert "WIRING.md" in result["files"]

    def test_has_flag_snippet(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        assert "flag" in result["snippets"]

    def test_has_auto_fire_effect_snippet(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        assert "auto_fire_effect" in result["snippets"]

    def test_has_replay_snippet(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        assert "replay" in result["snippets"]

    def test_has_permalink_snippet(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        assert "permalink" in result["snippets"]
        assert result["snippets"]["permalink"], "permalink snippet must not be empty"


# ---------------------------------------------------------------------------
# Flag snippet — extends existing system (no parallel store)
# ---------------------------------------------------------------------------

class TestFlagSnippetExtendsExisting:
    """
    When host_signals has a detected first_run_flag_system, the emitted flag
    snippet must add a SIBLING flag alongside the existing ones — not invent
    a new store, context, or localStorage key.
    """

    def _flag_snippet(self) -> str:
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        return result["snippets"]["flag"]

    def test_sibling_flag_name_present(self):
        """The new flag must be named (e.g. hasSeenSpotlight)."""
        snippet = self._flag_snippet()
        # Accept common sibling-flag naming patterns
        sibling_patterns = [
            "hasSeenSpotlight",
            "hasSeenTour",
            "spotlightSeen",
            "tourSeen",
            "hasTakenTour",
        ]
        found = any(p in snippet for p in sibling_patterns)
        assert found, (
            f"No sibling flag name found in flag snippet. Got:\n{snippet}"
        )

    def test_references_existing_flag_file(self):
        """
        The snippet (or wiring guide) must reference the file that owns the
        existing flags — confirming it's extending, not inventing a new store.
        """
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        flag_file = "useUserPreferences.ts"
        # Check either the snippet or WIRING.md names the file
        combined = (
            result["snippets"]["flag"]
            + result["wiring_guide"]
            + result["files"].get("WIRING.md", "")
        )
        assert flag_file in combined, (
            f"Flag file '{flag_file}' not referenced in flag snippet or WIRING.md"
        )

    def test_no_parallel_localstorage_when_system_detected(self):
        """
        When a flag system exists, the flag snippet must NOT fall back to
        localStorage — that's the parallel-store anti-pattern.
        """
        snippet = self._flag_snippet()
        assert "localStorage" not in snippet, (
            "Flag snippet invents a localStorage key even though a flag system was detected"
        )

    def test_extends_existing_flags_not_replaces(self):
        """
        The snippet text must read as an ADDITION (e.g., references existing
        flags by name or shows them alongside the new one), confirming sibling
        placement rather than replacement.
        """
        snippet = self._flag_snippet()
        # Must reference at least one of the existing flags OR clearly show addition syntax
        existing_references = [
            "hasSeenWelcome",
            "hasCompletedOnboarding",
            "// add alongside",
            "sibling",
            "beside",
            "next to",
            "alongside",
        ]
        found = any(ref.lower() in snippet.lower() for ref in existing_references)
        assert found, (
            "Flag snippet does not reference existing flags or show addition syntax — "
            "must be clearly additive (sibling), not a replacement"
        )


# ---------------------------------------------------------------------------
# Auto-fire effect snippet — correct gating
# ---------------------------------------------------------------------------

class TestAutoFireEffectGating:
    """
    The auto-fire effect must gate on THREE conditions:
      1. Onboarding complete (or equivalent)
      2. First-login overlay(s) dismissed
      3. Flag unset (hasSeenSpotlight is false/undefined)
    And set the flag in onDone.
    """

    def _effect_snippet(self, build_plan=None, host_signals=None) -> str:
        bp = build_plan or _build_plan_with_overlays()
        hs = host_signals or _host_signals_with_flag_system()
        result = emit_trigger_wiring(bp, hs)
        return result["snippets"]["auto_fire_effect"]

    def test_uses_react_useEffect(self):
        """React framework → effect must be a useEffect."""
        snippet = self._effect_snippet()
        assert "useEffect" in snippet, (
            "auto_fire_effect must use React useEffect for React apps"
        )

    def test_calls_startSpotlightTour(self):
        """Must call startSpotlightTour (the primary call surface from emit_tour_module)."""
        snippet = self._effect_snippet()
        assert "startSpotlightTour" in snippet, (
            "auto_fire_effect must call startSpotlightTour"
        )

    def test_flag_unset_gate_present(self):
        """
        Must check the flag before firing.
        Accept: !hasSeenSpotlight, hasSeenSpotlight === false, !flag, negated flag check.
        """
        snippet = self._effect_snippet()
        flag_gate_patterns = [
            "!hasSeenSpotlight",
            "!hasSeen",
            "hasSeenSpotlight === false",
            "hasSeenSpotlight == false",
            "!tourSeen",
            "!spotlightSeen",
            "!hasTakenTour",
        ]
        found = any(p in snippet for p in flag_gate_patterns)
        assert found, (
            f"auto_fire_effect does not gate on flag-unset check. Snippet:\n{snippet}"
        )

    def test_overlay_dismissed_gate_present(self):
        """
        Must gate on overlay dismissal — the WelcomeModal must be gone before firing.
        Acceptable: a boolean prop, a state variable name, or a reference to the overlay.
        """
        snippet = self._effect_snippet()
        overlay_gate_patterns = [
            "welcomeModal",
            "WelcomeModal",
            "isOnboardingComplete",
            "onboardingComplete",
            "overlayDismissed",
            "modalDismissed",
            "hasCompletedOnboarding",
            "isWelcomeDone",
        ]
        found = any(p.lower() in snippet.lower() for p in overlay_gate_patterns)
        assert found, (
            f"auto_fire_effect does not gate on overlay-dismissed. "
            f"Expected reference to WelcomeModal or onboarding completion. Snippet:\n{snippet}"
        )

    def test_onDone_sets_flag(self):
        """
        The onDone callback passed to startSpotlightTour must SET the flag
        (so the tour never auto-fires twice).
        """
        snippet = self._effect_snippet()
        set_flag_patterns = [
            "setHasSeenSpotlight",
            "hasSeenSpotlight = true",
            "setHasSeen",
            "setTourSeen",
            "setSpotlightSeen",
            "setHasTakenTour",
            "update(",
            "set(",
            "dispatch(",
            "localStorage.setItem",  # allowed only in no-flag-system fallback
        ]
        # Must have at least one setter-style call in the snippet
        found = any(p in snippet for p in set_flag_patterns)
        assert found, (
            f"onDone in auto_fire_effect does not set the flag. Snippet:\n{snippet}"
        )

    def test_effect_has_dependency_array(self):
        """useEffect must have a dependency array to avoid infinite re-runs."""
        snippet = self._effect_snippet()
        # useEffect(() => { ... }, [...]) — the closing bracket pattern
        has_dep_array = "], [" in snippet or "],\n  [" in snippet or "}, [" in snippet
        assert has_dep_array, (
            "useEffect in auto_fire_effect is missing a dependency array"
        )


# ---------------------------------------------------------------------------
# Replay snippet — ungated
# ---------------------------------------------------------------------------

class TestReplaySnippet:
    """
    The replay snippet must call replaySpotlightTour and must be ungated
    (no flag check, no onboarding check — replay fires any time).
    """

    def _replay_snippet(self) -> str:
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        return result["snippets"]["replay"]

    def test_calls_replaySpotlightTour(self):
        snippet = self._replay_snippet()
        assert "replaySpotlightTour" in snippet, (
            "replay snippet must call replaySpotlightTour"
        )

    def test_is_ungated_no_flag_check(self):
        """Replay must not gate on the has-seen flag."""
        snippet = self._replay_snippet()
        gated_patterns = [
            "hasSeenSpotlight",
            "if (!has",
            "if (has",
            "hasSeenTour",
            "!tourSeen",
        ]
        found = any(p in snippet for p in gated_patterns)
        assert not found, (
            "replay snippet must be ungated — found a flag check in it"
        )

    def test_is_a_button_or_control(self):
        """
        The replay snippet should render a button or control (JSX) for a
        'Take the Tour' entry point — not just a bare function call.
        """
        snippet = self._replay_snippet()
        control_patterns = [
            "<button",
            "onClick",
            "<Button",
            "onClick=",
            "button",
        ]
        found = any(p.lower() in snippet.lower() for p in control_patterns)
        assert found, (
            "replay snippet must be a persistent UI control (button/onClick), "
            f"not just a bare function call. Got:\n{snippet}"
        )


# ---------------------------------------------------------------------------
# Permalink snippet — URL-triggered tour entry
# ---------------------------------------------------------------------------

class TestPermalinkSnippet:
    """
    The permalink snippet must:
      - Read a ?tour URL param via URLSearchParams (or window.location.search)
      - Call startSpotlightTour() when the param is present
      - Bypass the hasSeenSpotlight flag (user explicitly opted in via URL)
      - NOT set the flag after firing (link is reusable)
      - Still honor overlay-sequencing
      - Clean the URL param after firing so refresh doesn't loop
      - Guard SSR (typeof window === 'undefined' check)
    """

    def _permalink_snippet(self, build_plan=None, host_signals=None) -> str:
        bp = build_plan or _build_plan_with_overlays()
        hs = host_signals or _host_signals_with_flag_system()
        result = emit_trigger_wiring(bp, hs)
        return result["snippets"]["permalink"]

    def test_uses_react_useEffect(self):
        snippet = self._permalink_snippet()
        assert "useEffect" in snippet, (
            "permalink must use React useEffect to fire on mount"
        )

    def test_reads_url_search_param(self):
        snippet = self._permalink_snippet()
        # Accept URLSearchParams or window.location.search reading patterns
        patterns = ["URLSearchParams", "window.location.search", "location.search"]
        found = any(p in snippet for p in patterns)
        assert found, (
            f"permalink must read URL params (URLSearchParams). Snippet:\n{snippet}"
        )

    def test_checks_tour_param(self):
        snippet = self._permalink_snippet()
        # Must reference the `tour` param name
        patterns = ["'tour'", '"tour"', "params.has('tour')", 'params.has("tour")']
        found = any(p in snippet for p in patterns)
        assert found, (
            f"permalink must check for the 'tour' URL param. Snippet:\n{snippet}"
        )

    def test_calls_startSpotlightTour(self):
        snippet = self._permalink_snippet()
        assert "startSpotlightTour" in snippet, (
            "permalink must call startSpotlightTour when ?tour is present"
        )

    def test_does_not_set_flag(self):
        """
        Permalink must NOT call setHasSeenSpotlight — the link should be reusable.
        Auto-fire owns the flag; permalink is a separate opt-in path.
        """
        snippet = self._permalink_snippet()
        flag_setter_patterns = ["setHasSeenSpotlight", "setHasSeen", "setSpotlightSeen"]
        found = any(p in snippet for p in flag_setter_patterns)
        assert not found, (
            "permalink must NOT set the hasSeenSpotlight flag — link must remain reusable"
        )

    def test_ssr_guard_present(self):
        """Permalink reads window.location — must guard against SSR."""
        snippet = self._permalink_snippet()
        ssr_patterns = [
            "typeof window === 'undefined'",
            'typeof window === "undefined"',
            "typeof window !== 'undefined'",
            'typeof window !== "undefined"',
            "if (typeof window",
        ]
        found = any(p in snippet for p in ssr_patterns)
        assert found, (
            f"permalink must guard against SSR (typeof window check). Snippet:\n{snippet}"
        )

    def test_cleans_url_after_firing(self):
        """Permalink must clean the ?tour param after firing so refresh doesn't loop."""
        snippet = self._permalink_snippet()
        cleanup_patterns = [
            "history.replaceState",
            "history.pushState",
            "params.delete",
        ]
        # Must show URL mutation after firing
        found = any(p in snippet for p in cleanup_patterns)
        assert found, (
            f"permalink must clean the URL param after firing (history.replaceState or "
            f"params.delete). Snippet:\n{snippet}"
        )

    def test_overlay_gate_still_present(self):
        """Permalink honors overlay-sequencing — must reference the overlay or onboarding gate."""
        snippet = self._permalink_snippet()
        gate_patterns = [
            "welcomeModal",
            "WelcomeModal",
            "isOnboardingComplete",
            "onboardingComplete",
        ]
        found = any(p.lower() in snippet.lower() for p in gate_patterns)
        assert found, (
            f"permalink must gate on overlay-dismissed even when URL-triggered. "
            f"Snippet:\n{snippet}"
        )


# ---------------------------------------------------------------------------
# WIRING.md — precision placement guide
# ---------------------------------------------------------------------------

class TestWiringMd:
    """
    WIRING.md must name:
      - The flag file (where to add the sibling flag)
      - The effect placement (the main authenticated/dashboard component)
      - The replay placement (where to drop the replay control)
    """

    def _wiring_md(self) -> str:
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_with_flag_system()
        )
        return result["files"]["WIRING.md"]

    def test_names_flag_file(self):
        """WIRING.md must name the file where the flag should be added."""
        md = self._wiring_md()
        assert "useUserPreferences.ts" in md, (
            "WIRING.md must name the flag file (useUserPreferences.ts)"
        )

    def test_names_main_component(self):
        """WIRING.md must name the main component where the effect should be placed."""
        md = self._wiring_md()
        assert "Dashboard" in md, (
            "WIRING.md must name the main component (Dashboard) for effect placement"
        )

    def test_names_main_component_file(self):
        """WIRING.md must include the component file path."""
        md = self._wiring_md()
        assert "Dashboard.tsx" in md, (
            "WIRING.md must include the main component file path (Dashboard.tsx)"
        )

    def test_replay_placement_mentioned(self):
        """WIRING.md must mention where to add the replay control."""
        md = self._wiring_md()
        replay_placement_patterns = [
            "replay",
            "Take the Tour",
            "help menu",
            "settings",
            "persistent",
        ]
        found = any(p.lower() in md.lower() for p in replay_placement_patterns)
        assert found, (
            "WIRING.md must mention where to add the replay control"
        )

    def test_permalink_placement_mentioned(self):
        """WIRING.md must mention the permalink trigger step."""
        md = self._wiring_md()
        permalink_patterns = ["permalink", "?tour", "URL param"]
        found = any(p.lower() in md.lower() for p in permalink_patterns)
        assert found, (
            f"WIRING.md must mention the permalink trigger step. Got:\n{md[:500]}..."
        )

    def test_wiring_md_is_not_empty(self):
        md = self._wiring_md()
        assert len(md.strip()) > 100, "WIRING.md content is too sparse"

    def test_wiring_md_has_sections(self):
        """WIRING.md must have at minimum two section headings."""
        md = self._wiring_md()
        headings = [line for line in md.splitlines() if line.startswith("#")]
        assert len(headings) >= 2, (
            f"WIRING.md must have at least 2 section headings; found {len(headings)}"
        )


# ---------------------------------------------------------------------------
# Fallback: no first_run_flag_system → localStorage + warning
# ---------------------------------------------------------------------------

class TestNoFlagSystemFallback:
    """
    When host_signals["first_run_flag_system"] is None, emit_trigger_wiring must:
      - Fall back to a minimal localStorage implementation
      - Add a warning about the fallback
    """

    def _result(self) -> dict:
        return emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_no_flag_system()
        )

    def test_localStorage_fallback_in_flag_snippet(self):
        result = self._result()
        snippet = result["snippets"]["flag"]
        assert "localStorage" in snippet, (
            "When no flag system is detected, flag snippet must use localStorage fallback"
        )

    def test_warning_emitted(self):
        result = self._result()
        assert len(result["warnings"]) > 0, (
            "No warning emitted when first_run_flag_system is None"
        )

    def test_warning_mentions_flag_system(self):
        result = self._result()
        warnings_text = " ".join(result["warnings"]).lower()
        keywords = ["flag", "first-run", "onboarding", "detected", "fallback", "localstorage"]
        found = any(k in warnings_text for k in keywords)
        assert found, (
            f"Warning doesn't mention missing flag system. Got: {result['warnings']}"
        )

    def test_auto_fire_still_emitted(self):
        """Even with no flag system, the auto-fire effect must still be emitted."""
        result = self._result()
        assert "auto_fire_effect" in result["snippets"]
        assert result["snippets"]["auto_fire_effect"]

    def test_replay_still_emitted(self):
        """Replay control must be emitted regardless of flag system."""
        result = self._result()
        assert "replay" in result["snippets"]
        assert result["snippets"]["replay"]


# ---------------------------------------------------------------------------
# No main component detected → warning
# ---------------------------------------------------------------------------

class TestNoMainComponentWarning:
    """When host_signals["main_component"] is None, emit a warning."""

    def test_warning_emitted_when_no_main_component(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_no_main_component()
        )
        assert len(result["warnings"]) > 0, (
            "No warning emitted when main_component is None"
        )

    def test_warning_mentions_component(self):
        result = emit_trigger_wiring(
            _build_plan_with_overlays(), _host_signals_no_main_component()
        )
        warnings_text = " ".join(result["warnings"]).lower()
        keywords = ["component", "main", "dashboard", "placement", "detected"]
        found = any(k in warnings_text for k in keywords)
        assert found, (
            f"Warning doesn't mention missing main component. Got: {result['warnings']}"
        )


# ---------------------------------------------------------------------------
# on-demand trigger model — no auto-fire effect
# ---------------------------------------------------------------------------

class TestOnDemandTriggerModel:
    """
    When trigger_model is 'on-demand', the auto-fire effect must be absent or empty
    — only a replay/launch control is needed.
    """

    def _build_plan_on_demand(self) -> dict:
        bp = _build_plan_with_overlays()
        bp["trigger_model"] = "on-demand"
        return bp

    def test_no_auto_fire_for_on_demand(self):
        result = emit_trigger_wiring(
            self._build_plan_on_demand(), _host_signals_with_flag_system()
        )
        snippet = result["snippets"].get("auto_fire_effect", "")
        # Either absent, empty, or clearly marked as N/A
        is_absent_or_empty = not snippet or snippet.strip() == "" or "N/A" in snippet
        assert is_absent_or_empty, (
            "auto_fire_effect must be absent or empty for on-demand trigger model"
        )

    def test_replay_present_for_on_demand(self):
        """On-demand still needs a launch control (it's the ONLY entry point)."""
        result = emit_trigger_wiring(
            self._build_plan_on_demand(), _host_signals_with_flag_system()
        )
        assert "replay" in result["snippets"]
        assert result["snippets"]["replay"]

    def test_permalink_present_for_on_demand(self):
        """
        Permalink is a third opt-in entry point and works regardless of trigger
        model. On-demand should still emit the permalink snippet.
        """
        result = emit_trigger_wiring(
            self._build_plan_on_demand(), _host_signals_with_flag_system()
        )
        assert "permalink" in result["snippets"]
        assert result["snippets"]["permalink"], (
            "permalink must be emitted for on-demand trigger model too"
        )
        assert "startSpotlightTour" in result["snippets"]["permalink"]
