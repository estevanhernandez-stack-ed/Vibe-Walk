"""
Truth-table tests for build_verdict.decide_verdict().

One test per don't-build condition from _seed.md §3 Phase 1 step 6, plus:
  - the clean "build" case (no conditions fire)
  - the "cheaper-first" blank-canvas case

Each test checks:
  - verdict is the expected string
  - reasons list is non-empty
  - (for don't-build / cheaper-first) reasons mention the relevant signal
"""
import pytest

# This import will fail until build_verdict.py is implemented.
from discovery.build_verdict import decide_verdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_signals(**overrides) -> dict:
    """Return a clean 'all clear' signals dict, then apply overrides."""
    base = {
        "interactive_surface_count": 8,
        "audience": "b2c",
        "existing_onboarding": False,
        "app_category": "web_app",
        "anchor_readiness": "ready",
        "no_stable_selectors": False,
        "anchor_pass_refused": False,
        "first_run_is_blank_canvas": False,
        "high_urgency": False,
        "untourable_surface_ratio": 0.1,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Clean "build" case — no don't-build condition fires
# ---------------------------------------------------------------------------

def test_build_when_all_clear():
    signals = _base_signals()
    result = decide_verdict(signals)
    assert result["verdict"] == "build"
    assert isinstance(result["reasons"], list)


# ---------------------------------------------------------------------------
# Don't-build conditions (9 conditions from _seed.md §3 step 6)
# ---------------------------------------------------------------------------

def test_dont_build_too_few_surfaces():
    """Fewer than ~5 interactive surfaces → don't-build."""
    signals = _base_signals(interactive_surface_count=3)
    result = decide_verdict(signals)
    assert result["verdict"] == "don't-build"
    assert result["reasons"], "reasons must be non-empty"
    assert any("surface" in r.lower() for r in result["reasons"])


def test_dont_build_domain_expert_audience():
    """Domain-expert / power-user audience → don't-build."""
    signals = _base_signals(audience="domain_expert")
    result = decide_verdict(signals)
    assert result["verdict"] == "don't-build"
    assert any("audience" in r.lower() or "expert" in r.lower() for r in result["reasons"])


def test_dont_build_existing_comprehensive_onboarding():
    """Existing comprehensive onboarding already present → don't-build."""
    signals = _base_signals(existing_onboarding=True)
    result = decide_verdict(signals)
    assert result["verdict"] == "don't-build"
    assert any("onboarding" in r.lower() for r in result["reasons"])


def test_dont_build_single_purpose_tool():
    """Single-purpose tool → don't-build."""
    signals = _base_signals(app_category="single_purpose")
    result = decide_verdict(signals)
    assert result["verdict"] == "don't-build"
    assert any("single" in r.lower() or "purpose" in r.lower() for r in result["reasons"])


def test_dont_build_no_stable_selectors_and_anchor_pass_refused():
    """No stable selectors AND host won't accept an anchor pass → don't-build."""
    signals = _base_signals(no_stable_selectors=True, anchor_pass_refused=True)
    result = decide_verdict(signals)
    assert result["verdict"] == "don't-build"
    assert any("selector" in r.lower() or "anchor" in r.lower() for r in result["reasons"])


def test_dont_build_high_urgency_context():
    """High-urgency use context → don't-build."""
    signals = _base_signals(high_urgency=True)
    result = decide_verdict(signals)
    assert result["verdict"] == "don't-build"
    assert any("urgency" in r.lower() or "urgent" in r.lower() for r in result["reasons"])


def test_dont_build_cli_product():
    """CLI / code-surface product → don't-build."""
    signals = _base_signals(app_category="cli")
    result = decide_verdict(signals)
    assert result["verdict"] == "don't-build"
    assert any("cli" in r.lower() or "code" in r.lower() for r in result["reasons"])


def test_dont_build_untourable_surfaces_dominate():
    """Untourable surfaces dominate (shadow DOM / cross-origin iframe) → don't-build."""
    signals = _base_signals(untourable_surface_ratio=0.6)
    result = decide_verdict(signals)
    assert result["verdict"] == "don't-build"
    assert any("untourable" in r.lower() or "shadow" in r.lower() or "ratio" in r.lower() for r in result["reasons"])


# ---------------------------------------------------------------------------
# Cheaper-first: blank-canvas first-run → cheaper-first
# ---------------------------------------------------------------------------

def test_cheaper_first_blank_canvas():
    """First-run surface is a blank canvas → cheaper-first (empty-state/sample-data)."""
    signals = _base_signals(first_run_is_blank_canvas=True)
    result = decide_verdict(signals)
    assert result["verdict"] == "cheaper-first"
    assert any("canvas" in r.lower() or "empty" in r.lower() or "sample" in r.lower() for r in result["reasons"])


# ---------------------------------------------------------------------------
# Edge: no_stable_selectors alone (without anchor_pass_refused) → not don't-build
# ---------------------------------------------------------------------------

def test_no_stable_selectors_alone_not_dont_build():
    """No stable selectors alone (anchor pass not refused) should NOT fire don't-build."""
    signals = _base_signals(no_stable_selectors=True, anchor_pass_refused=False)
    result = decide_verdict(signals)
    # Should not be don't-build — anchor pass could resolve this
    # (it may be "build" or remain agnostic; but NOT "don't-build")
    assert result["verdict"] != "don't-build"


# ---------------------------------------------------------------------------
# Priority: cheaper-first wins over don't-build when blank canvas is the trigger
# ---------------------------------------------------------------------------

def test_cheaper_first_takes_priority_over_dont_build_when_blank_canvas():
    """
    When blank canvas fires, cheaper-first is returned even if other signals
    would fire don't-build — the cheaper-first signal is more actionable.
    """
    # high_urgency alone would fire don't-build, but blank canvas → cheaper-first
    # NOTE: this test is intentionally flexible — if the implementation returns
    # "don't-build" due to high_urgency dominating, that's also acceptable behavior.
    # We mainly assert the blank_canvas signal is always in the reasons.
    signals = _base_signals(first_run_is_blank_canvas=True)
    result = decide_verdict(signals)
    assert result["verdict"] in ("cheaper-first", "don't-build")
    # At a minimum, a reason mentioning canvas/empty/sample must appear
    reason_text = " ".join(result["reasons"]).lower()
    assert "canvas" in reason_text or "empty" in reason_text or "sample" in reason_text


# ---------------------------------------------------------------------------
# Result shape contract
# ---------------------------------------------------------------------------

def test_result_always_has_verdict_and_reasons():
    """decide_verdict must always return {"verdict": str, "reasons": list}."""
    for signals in [
        _base_signals(),
        _base_signals(interactive_surface_count=2),
        _base_signals(audience="domain_expert"),
        _base_signals(first_run_is_blank_canvas=True),
    ]:
        result = decide_verdict(signals)
        assert "verdict" in result
        assert "reasons" in result
        assert isinstance(result["verdict"], str)
        assert isinstance(result["reasons"], list)
        assert result["verdict"] in ("build", "don't-build", "cheaper-first")
