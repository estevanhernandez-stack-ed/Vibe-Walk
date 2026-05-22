"""
Truth-table tests for substrate_tree.resolve_substrate().

One test per branch of the decision tree from _seed.md §3 Phase 1.5.
Tree order (checked top-down):
  1.  Not React → driver.js (mandatory)
  2.  Any stop in shadow DOM → untourable
  3.  Output shape config-only JSON → driver.js (mandatory)
  4.  Next.js App Router AND tour spans multiple routes → nextstep.js (id anchor)
  5.  Any stop must async-wait for element mount → react-joyride
  6.  Heavily animated / re-rendering stop elements → reactour
  7.  Host wants idiomatic React AND bundle not a concern → react-joyride
  8.  DEFAULT → driver.js
  ALWAYS: Intro.js is never selectable (AGPL-3)
"""
import pytest
import sys
from pathlib import Path

# conftest.py adds SCRIPTS_ROOT to sys.path — build/ is a sub-package of that
from build.substrate_tree import resolve_substrate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_signals(**overrides) -> dict:
    """
    Return a clean 'React SPA with no special conditions' signals dict,
    then apply overrides.  This is the signals shape that routes to DEFAULT.
    """
    base = {
        "framework": "react-spa",
        "tour_spans_multiple_routes": False,
        "has_shadow_dom_stops": False,
        "output_shape": "module",
        "needs_async_mount_wait": False,
        "heavily_animated": False,
        "wants_idiomatic_react": False,
        "bundle_size_sensitive": False,
    }
    base.update(overrides)
    return base


def _non_react_frameworks():
    return ["svelte", "vue", "vanilla", "alpine", "astro"]


# ---------------------------------------------------------------------------
# Branch 1 — Not React → driver.js (mandatory)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fw", _non_react_frameworks())
def test_non_react_framework_resolves_to_driver(fw):
    """Any non-React framework → driver.js, anchor data-tour."""
    signals = _base_signals(framework=fw)
    result = resolve_substrate(signals)
    assert result["substrate"] == "driver.js", f"Expected driver.js for framework={fw}"
    assert result["anchor_attr"] == "data-tour"
    assert result["confirm_only"] is False  # mandatory, not confirm-only


def test_non_react_framework_reason_mentions_mandatory(capsys):
    """Non-React path should note driver.js is mandatory."""
    signals = _base_signals(framework="svelte")
    result = resolve_substrate(signals)
    assert "mandatory" in result["reason"].lower() or "non-react" in result["reason"].lower() or "svelte" in result["reason"].lower()


# ---------------------------------------------------------------------------
# Branch 2 — Shadow DOM → untourable
# ---------------------------------------------------------------------------

def test_shadow_dom_resolves_to_untourable():
    """Any tour stop inside shadow DOM → substrate = 'untourable'."""
    signals = _base_signals(has_shadow_dom_stops=True)
    result = resolve_substrate(signals)
    assert result["substrate"] == "untourable"
    assert "shadow" in result["reason"].lower() or "untourable" in result["reason"].lower()


def test_shadow_dom_beats_other_conditions():
    """Shadow DOM check fires before all React-specific checks."""
    signals = _base_signals(
        has_shadow_dom_stops=True,
        framework="next-app-router",
        tour_spans_multiple_routes=True,
    )
    result = resolve_substrate(signals)
    assert result["substrate"] == "untourable"


# ---------------------------------------------------------------------------
# Branch 3 — Config-only output shape → driver.js (mandatory)
# ---------------------------------------------------------------------------

def test_config_only_resolves_to_driver():
    """Output shape config-only JSON → driver.js (only serializable steps)."""
    signals = _base_signals(output_shape="config-only")
    result = resolve_substrate(signals)
    assert result["substrate"] == "driver.js"
    assert result["anchor_attr"] == "data-tour"
    # config-only is a forced/mandatory path, not a confirm-only
    assert result["confirm_only"] is False


def test_config_only_reason_mentions_serializable():
    """Config-only reason should mention serialization or driver.js mandatory."""
    signals = _base_signals(output_shape="config-only")
    result = resolve_substrate(signals)
    reason_lower = result["reason"].lower()
    assert "config" in reason_lower or "serial" in reason_lower or "mandatory" in reason_lower


# ---------------------------------------------------------------------------
# Branch 4 — Next.js App Router + multi-route → nextstep.js (id anchor)
# ---------------------------------------------------------------------------

def test_nextjs_multi_route_resolves_to_nextstep():
    """Next.js App Router AND tour spans multiple routes → nextstep.js."""
    signals = _base_signals(
        framework="next-app-router",
        tour_spans_multiple_routes=True,
    )
    result = resolve_substrate(signals)
    assert result["substrate"] == "nextstep.js"
    assert result["anchor_attr"] == "id"  # NOT data-tour (D3-nextstep)


def test_nextstep_reason_mentions_framer_motion():
    """NextStep resolution should note the ~30KB Framer Motion peer dep."""
    signals = _base_signals(
        framework="next-app-router",
        tour_spans_multiple_routes=True,
    )
    result = resolve_substrate(signals)
    reason_lower = result["reason"].lower()
    assert "framer" in reason_lower or "motion" in reason_lower or "30kb" in reason_lower or "peer" in reason_lower


def test_nextjs_single_route_does_not_resolve_to_nextstep():
    """Next.js App Router but single-route tour → does NOT go to nextstep.js."""
    signals = _base_signals(
        framework="next-app-router",
        tour_spans_multiple_routes=False,
    )
    result = resolve_substrate(signals)
    assert result["substrate"] != "nextstep.js"


# ---------------------------------------------------------------------------
# Branch 5 — Async-wait for element mount → react-joyride
# ---------------------------------------------------------------------------

def test_async_mount_wait_resolves_to_joyride():
    """Any stop must async-wait for element mount → react-joyride."""
    signals = _base_signals(needs_async_mount_wait=True)
    result = resolve_substrate(signals)
    assert result["substrate"] == "react-joyride"


# ---------------------------------------------------------------------------
# Branch 6 — Heavily animated / re-rendering stops → reactour
# ---------------------------------------------------------------------------

def test_heavily_animated_resolves_to_reactour():
    """Heavily animated / re-rendering stop elements → reactour."""
    signals = _base_signals(heavily_animated=True)
    result = resolve_substrate(signals)
    assert result["substrate"] == "reactour"


def test_reactour_reason_mentions_mutation_or_reposition():
    """Reactour resolution should note mutation/reposition capability."""
    signals = _base_signals(heavily_animated=True)
    result = resolve_substrate(signals)
    reason_lower = result["reason"].lower()
    assert "mutat" in reason_lower or "reposition" in reason_lower or "animat" in reason_lower


# ---------------------------------------------------------------------------
# Branch 7 — Idiomatic React + bundle not a concern → react-joyride
# ---------------------------------------------------------------------------

def test_idiomatic_react_not_bundle_sensitive_resolves_to_joyride():
    """Host wants idiomatic React AND bundle not a concern → react-joyride."""
    signals = _base_signals(
        wants_idiomatic_react=True,
        bundle_size_sensitive=False,
    )
    result = resolve_substrate(signals)
    assert result["substrate"] == "react-joyride"


def test_idiomatic_react_but_bundle_sensitive_falls_through_to_default():
    """
    If wants_idiomatic_react is True but bundle_size_sensitive is also True,
    the idiomatic-React branch does NOT fire — fall through to default (driver.js).
    (The tree says "bundle not a concern" is required to activate this branch.)
    """
    signals = _base_signals(
        wants_idiomatic_react=True,
        bundle_size_sensitive=True,
    )
    result = resolve_substrate(signals)
    # Should NOT be react-joyride; should be driver.js (default)
    assert result["substrate"] == "driver.js"


# ---------------------------------------------------------------------------
# Branch 8 — DEFAULT → driver.js
# ---------------------------------------------------------------------------

def test_default_resolves_to_driver():
    """No special conditions → driver.js, anchor data-tour."""
    signals = _base_signals()
    result = resolve_substrate(signals)
    assert result["substrate"] == "driver.js"
    assert result["anchor_attr"] == "data-tour"


def test_default_confirm_only_is_true():
    """Default path is confirm-only (ask user to confirm, not mandatory)."""
    signals = _base_signals()
    result = resolve_substrate(signals)
    assert result["confirm_only"] is True


# ---------------------------------------------------------------------------
# ALWAYS BLOCK: Intro.js is never selectable (AGPL-3)
# ---------------------------------------------------------------------------

def test_introjs_never_returned():
    """
    Intro.js must never appear as the substrate under any signal combination.
    Test every branch permutation for this.
    """
    test_cases = [
        _base_signals(),
        _base_signals(framework="svelte"),
        _base_signals(has_shadow_dom_stops=True),
        _base_signals(output_shape="config-only"),
        _base_signals(framework="next-app-router", tour_spans_multiple_routes=True),
        _base_signals(needs_async_mount_wait=True),
        _base_signals(heavily_animated=True),
        _base_signals(wants_idiomatic_react=True, bundle_size_sensitive=False),
    ]
    for signals in test_cases:
        result = resolve_substrate(signals)
        assert result["substrate"] != "intro.js", \
            f"Intro.js returned for signals={signals}"
        assert result["substrate"] != "introjs", \
            f"Intro.js (variant) returned for signals={signals}"


# ---------------------------------------------------------------------------
# Result shape contract
# ---------------------------------------------------------------------------

def test_result_always_has_required_keys():
    """resolve_substrate must always return the four required keys."""
    required_keys = {"substrate", "anchor_attr", "reason", "confirm_only"}
    test_cases = [
        _base_signals(),
        _base_signals(framework="vue"),
        _base_signals(has_shadow_dom_stops=True),
        _base_signals(output_shape="config-only"),
        _base_signals(framework="next-app-router", tour_spans_multiple_routes=True),
        _base_signals(needs_async_mount_wait=True),
        _base_signals(heavily_animated=True),
        _base_signals(wants_idiomatic_react=True),
    ]
    for signals in test_cases:
        result = resolve_substrate(signals)
        assert required_keys == set(result.keys()), \
            f"Missing or extra keys for signals={signals}: got {set(result.keys())}"


def test_result_substrate_is_valid_value():
    """substrate must be one of the known values."""
    valid_substrates = {"driver.js", "nextstep.js", "react-joyride", "reactour", "untourable"}
    for signals in [
        _base_signals(),
        _base_signals(framework="vue"),
        _base_signals(has_shadow_dom_stops=True),
        _base_signals(output_shape="config-only"),
        _base_signals(framework="next-app-router", tour_spans_multiple_routes=True),
        _base_signals(needs_async_mount_wait=True),
        _base_signals(heavily_animated=True),
        _base_signals(wants_idiomatic_react=True, bundle_size_sensitive=False),
    ]:
        result = resolve_substrate(signals)
        assert result["substrate"] in valid_substrates, \
            f"Unknown substrate '{result['substrate']}' for signals={signals}"
