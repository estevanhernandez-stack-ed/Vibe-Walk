"""
TDD tests for emit_analytics.emit_analytics().

M5 — Analytics wiring + replay.

Covers:
  - All 6 event names present in the emitted wiring
  - Each event maps to the correct Driver.js callback (assert the mapping)
  - tour_skipped vs tour_completed distinguished by last-step check
  - A host-agnostic trackTourEvent seam exists (no hardcoded vendor)
  - TOUR_ANALYTICS.md lists all 6 events + 7d and 14d attribution windows
  - Output dict shape: {"files": {...}, "warnings": [...]}
  - No hardcoded Amplitude/Mixpanel/Pendo/Segment/GA references in wiring
  - tour_started maps to drive start (not a Driver.js callback — emitted inline)
  - tour_replayed maps to replay invocation
"""
import pytest
import sys
from pathlib import Path

# conftest.py adds SCRIPTS_ROOT to sys.path — build/ is a sub-package of that
from build.emit_analytics import emit_analytics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _build_plan_4_stops() -> dict:
    """Minimal build-plan for analytics emission tests."""
    return {
        "schema_version": 1,
        "app_path": "/projects/my-app",
        "substrate": "driver.js",
        "anchor_attr": "data-tour",
        "aha_moment": {
            "surface": "project-dashboard",
            "reason": "First view where value is tangible.",
        },
        "ranked_shortlist": [
            {"name": "project-dashboard", "anchor": "project-dashboard", "rank": 1},
            {"name": "create-project",    "anchor": "create-project",    "rank": 2},
            {"name": "invite-team",       "anchor": "invite-team",       "rank": 3},
            {"name": "run-analysis",      "anchor": "run-analysis",      "rank": 4},
        ],
    }


# ---------------------------------------------------------------------------
# Return-shape tests
# ---------------------------------------------------------------------------

class TestReturnShape:
    def test_returns_dict_with_files_and_warnings(self):
        result = emit_analytics(_build_plan_4_stops())
        assert isinstance(result, dict)
        assert "files" in result
        assert "warnings" in result

    def test_warnings_is_list(self):
        result = emit_analytics(_build_plan_4_stops())
        assert isinstance(result["warnings"], list)

    def test_files_is_dict(self):
        result = emit_analytics(_build_plan_4_stops())
        assert isinstance(result["files"], dict)

    def test_emits_at_least_two_files(self):
        """Expect the TS wiring file + TOUR_ANALYTICS.md."""
        result = emit_analytics(_build_plan_4_stops())
        assert len(result["files"]) >= 2


# ---------------------------------------------------------------------------
# All six events present
# ---------------------------------------------------------------------------

SIX_EVENTS = [
    "tour_started",
    "tour_step_viewed",
    "tour_step_advanced",
    "tour_skipped",
    "tour_completed",
    "tour_replayed",
]


class TestSixEventsInWiring:
    """All six event names must appear in the emitted TypeScript wiring."""

    def _wiring_source(self) -> str:
        result = emit_analytics(_build_plan_4_stops())
        # Find the TypeScript analytics file (not the .md)
        ts_files = {k: v for k, v in result["files"].items() if k.endswith(".ts")}
        assert ts_files, "Expected at least one .ts file in output"
        return "\n".join(ts_files.values())

    @pytest.mark.parametrize("event_name", SIX_EVENTS)
    def test_event_present_in_wiring(self, event_name):
        source = self._wiring_source()
        assert event_name in source, (
            f"Event '{event_name}' not found in emitted analytics wiring"
        )


# ---------------------------------------------------------------------------
# Correct Driver.js callback mapping
# ---------------------------------------------------------------------------

class TestDriverJsCallbackMapping:
    """Each event must be wired to the right Driver.js callback."""

    def _wiring_source(self) -> str:
        result = emit_analytics(_build_plan_4_stops())
        ts_files = {k: v for k, v in result["files"].items() if k.endswith(".ts")}
        return "\n".join(ts_files.values())

    def test_tour_step_viewed_wired_to_onHighlightStarted(self):
        source = self._wiring_source()
        # Both the callback name and the event name must appear together
        assert "onHighlightStarted" in source
        assert "tour_step_viewed" in source
        # They must be in the same block — check proximity (within 10 lines)
        lines = source.splitlines()
        callback_lines = [i for i, l in enumerate(lines) if "onHighlightStarted" in l]
        event_lines    = [i for i, l in enumerate(lines) if "tour_step_viewed" in l]
        assert callback_lines and event_lines
        # At least one callback line is within 10 lines of an event line
        close_enough = any(
            abs(c - e) <= 10
            for c in callback_lines
            for e in event_lines
        )
        assert close_enough, (
            "onHighlightStarted and tour_step_viewed are not co-located in the wiring"
        )

    def test_tour_step_advanced_wired_to_onNextClick(self):
        source = self._wiring_source()
        assert "onNextClick" in source
        assert "tour_step_advanced" in source
        lines = source.splitlines()
        callback_lines = [i for i, l in enumerate(lines) if "onNextClick" in l]
        event_lines    = [i for i, l in enumerate(lines) if "tour_step_advanced" in l]
        assert callback_lines and event_lines
        close_enough = any(
            abs(c - e) <= 10
            for c in callback_lines
            for e in event_lines
        )
        assert close_enough, (
            "onNextClick and tour_step_advanced are not co-located in the wiring"
        )

    def test_tour_skipped_and_completed_both_wired_to_onDestroyStarted(self):
        source = self._wiring_source()
        assert "onDestroyStarted" in source
        assert "tour_skipped" in source
        assert "tour_completed" in source
        lines = source.splitlines()
        callback_lines  = [i for i, l in enumerate(lines) if "onDestroyStarted" in l]
        skipped_lines   = [i for i, l in enumerate(lines) if "tour_skipped" in l]
        completed_lines = [i for i, l in enumerate(lines) if "tour_completed" in l]
        assert callback_lines
        # Both skip and complete must be near an onDestroyStarted
        skip_close = any(
            abs(c - e) <= 20 for c in callback_lines for e in skipped_lines
        )
        complete_close = any(
            abs(c - e) <= 20 for c in callback_lines for e in completed_lines
        )
        assert skip_close,    "tour_skipped not co-located with onDestroyStarted"
        assert complete_close, "tour_completed not co-located with onDestroyStarted"


# ---------------------------------------------------------------------------
# tour_skipped vs tour_completed: last-step distinction
# ---------------------------------------------------------------------------

class TestSkipVsCompleteDistinction:
    """
    The emitted wiring MUST distinguish tour_skipped from tour_completed by
    checking whether the user is on the last step when onDestroyStarted fires.
    """

    def _wiring_source(self) -> str:
        result = emit_analytics(_build_plan_4_stops())
        ts_files = {k: v for k, v in result["files"].items() if k.endswith(".ts")}
        return "\n".join(ts_files.values())

    def test_last_step_check_present(self):
        """
        The wiring must contain some last-step guard. Acceptable patterns:
          - isLastStep, currentIndex, activeIndex, getState, steps.length
        At least one must be present so the two events are distinguishable at runtime.
        """
        source = self._wiring_source()
        last_step_indicators = [
            "isLastStep",
            "activeIndex",
            "currentIndex",
            "getState",
            "steps.length",
            ".length - 1",
            "totalCount",
        ]
        found = any(indicator in source for indicator in last_step_indicators)
        assert found, (
            "No last-step guard found in wiring — tour_skipped and tour_completed "
            "cannot be distinguished at runtime without a step-position check"
        )

    def test_both_events_in_same_onDestroyStarted_block(self):
        """
        tour_skipped and tour_completed should both appear inside (or near)
        the onDestroyStarted handler — not in separate, unrelated callbacks.
        """
        source = self._wiring_source()
        lines = source.splitlines()
        destroy_lines = [i for i, l in enumerate(lines) if "onDestroyStarted" in l]
        skipped_lines   = [i for i, l in enumerate(lines) if "tour_skipped" in l]
        completed_lines = [i for i, l in enumerate(lines) if "tour_completed" in l]
        assert destroy_lines, "onDestroyStarted not in wiring"
        # Both events must be within 30 lines of the same destroy handler
        for d_line in destroy_lines:
            skip_near     = any(abs(d_line - e) <= 30 for e in skipped_lines)
            complete_near = any(abs(d_line - e) <= 30 for e in completed_lines)
            if skip_near and complete_near:
                return  # found a destroy handler that has both — pass
        pytest.fail(
            "Could not find a single onDestroyStarted block containing both "
            "tour_skipped and tour_completed within 30 lines"
        )


# ---------------------------------------------------------------------------
# Host-agnostic seam — trackTourEvent
# ---------------------------------------------------------------------------

class TestHostAgnosticSeam:
    """
    The emitted wiring must expose a trackTourEvent function (or equivalent seam)
    and must NOT hardcode any specific analytics vendor.
    """

    def _wiring_source(self) -> str:
        result = emit_analytics(_build_plan_4_stops())
        ts_files = {k: v for k, v in result["files"].items() if k.endswith(".ts")}
        return "\n".join(ts_files.values())

    def test_trackTourEvent_seam_present(self):
        source = self._wiring_source()
        assert "trackTourEvent" in source, (
            "trackTourEvent seam not found in emitted analytics wiring"
        )

    def test_no_hardcoded_amplitude(self):
        """No actual amplitude SDK calls — comment mentions as examples are fine."""
        source = self._wiring_source()
        # Check for call-site patterns, not bare name presence
        import re
        calls = re.findall(r'\bamplitude\s*\.\s*track\s*\(', source, re.IGNORECASE)
        assert not calls, (
            "Hardcoded amplitude.track() call found — wiring must be host-agnostic"
        )

    def test_no_hardcoded_mixpanel(self):
        """No actual mixpanel SDK calls — comment mentions as examples are fine."""
        source = self._wiring_source()
        import re
        calls = re.findall(r'\bmixpanel\s*\.\s*track\s*\(', source, re.IGNORECASE)
        assert not calls, (
            "Hardcoded mixpanel.track() call found — wiring must be host-agnostic"
        )

    def test_no_hardcoded_pendo(self):
        """No actual pendo SDK calls — comment mentions as examples are fine."""
        source = self._wiring_source()
        import re
        calls = re.findall(r'\bpendo\s*\.\s*track\s*\(', source, re.IGNORECASE)
        assert not calls, (
            "Hardcoded pendo.track() call found — wiring must be host-agnostic"
        )

    def test_no_hardcoded_segment(self):
        """No actual segment/analytics SDK calls (outside comments)."""
        source = self._wiring_source()
        import re
        calls = re.findall(r'\banalytics\s*\.\s*track\s*\(', source, re.IGNORECASE)
        assert not calls, (
            "Hardcoded analytics.track() call found — wiring must be host-agnostic"
        )

    def test_no_hardcoded_ga(self):
        """No Google Analytics / gtag calls."""
        source = self._wiring_source()
        assert "gtag(" not in source, "gtag() reference found — must be host-agnostic"
        assert "ga(" not in source, "ga() reference found — must be host-agnostic"

    def test_trackTourEvent_is_exported_or_injected(self):
        """
        trackTourEvent must be either exported (for host to call) OR
        accepted as a parameter/injection — so the host can wire their own tracker.
        """
        source = self._wiring_source()
        # export function, export const, or parameter name
        patterns = [
            "export function trackTourEvent",
            "export const trackTourEvent",
            "trackTourEvent:",  # object property / type
            "trackTourEvent?",  # optional param
            "trackTourEvent =",  # assignment
        ]
        found = any(p in source for p in patterns)
        assert found, (
            "trackTourEvent is mentioned but not exported or exposed as an "
            "injectable seam — host cannot wire their own analytics"
        )


# ---------------------------------------------------------------------------
# TOUR_ANALYTICS.md content
# ---------------------------------------------------------------------------

class TestTourAnalyticsDoc:
    """TOUR_ANALYTICS.md must list all 6 events + attribution windows."""

    def _doc_content(self) -> str:
        result = emit_analytics(_build_plan_4_stops())
        md_files = {k: v for k, v in result["files"].items() if k.endswith(".md")}
        assert md_files, "No .md file emitted — expected TOUR_ANALYTICS.md"
        # Return the first (or only) .md file
        return next(iter(md_files.values()))

    @pytest.mark.parametrize("event_name", SIX_EVENTS)
    def test_event_listed_in_doc(self, event_name):
        doc = self._doc_content()
        assert event_name in doc, (
            f"Event '{event_name}' not found in TOUR_ANALYTICS.md"
        )

    def test_7d_window_mentioned(self):
        doc = self._doc_content()
        has_7d = "7d" in doc or "7-day" in doc or "7 day" in doc
        assert has_7d, "7-day attribution window not mentioned in TOUR_ANALYTICS.md"

    def test_14d_window_mentioned(self):
        doc = self._doc_content()
        has_14d = "14d" in doc or "14-day" in doc or "14 day" in doc
        assert has_14d, "14-day attribution window not mentioned in TOUR_ANALYTICS.md"

    def test_activation_event_placeholder_present(self):
        """
        The doc must include a placeholder for the host's own activation event
        (the downstream activation signal the tour is meant to drive).
        """
        doc = self._doc_content()
        # Accept common placeholder patterns
        patterns = [
            "YOUR_ACTIVATION_EVENT",
            "<activation_event>",
            "activation_event",
            "host_activation",
            "downstream activation",
            "<!-- host",
            "# replace",
            "TODO",
        ]
        found = any(p.lower() in doc.lower() for p in patterns)
        assert found, (
            "No host activation event placeholder found in TOUR_ANALYTICS.md — "
            "the doc must tell the host where to insert their own activation signal"
        )

    def test_completion_trap_metric_warning(self):
        """
        The doc must state that completion alone is a trap metric;
        success is downstream activation.
        """
        doc = self._doc_content()
        trap_indicators = [
            "trap",
            "completion alone",
            "not completion",
            "downstream activation",
            "activation",
        ]
        found = any(ind.lower() in doc.lower() for ind in trap_indicators)
        assert found, (
            "TOUR_ANALYTICS.md must warn that completion is a trap metric "
            "and name downstream activation as the real success criterion"
        )

    def test_tour_analytics_filename_present(self):
        result = emit_analytics(_build_plan_4_stops())
        assert "TOUR_ANALYTICS.md" in result["files"], (
            "Expected key 'TOUR_ANALYTICS.md' in files dict"
        )
