"""
Tests for diagnostics.a11y_assertions.check().

Covers:
  - Self-coherence: emit_tour_module's own output passes the assertions
    cleanly (the emitter and the checker cannot drift silently).
  - keyboard-control-disabled: allowKeyboardControl: false → fail.
  - escape-hatch-removed: allowClose: false → fail.
  - close-button-removed: showButtons without 'close' → fail.
  - nav-buttons-missing: showButtons without next/previous → warn.
  - focus-return-missing: legacy runner (onDestroyed, no activeElement
    capture) → warn, no fails — the pre-v0.3 emission shape.
  - destroy-hook-missing: runner without onDestroyed → warn.
  - step-copy-missing: steps file with elements but missing descriptions
    → warn.
  - showButtons absent entirely → driver.js defaults apply → no button
    findings.
  - No tour module: status "no-tour", graceful no-op.
  - Custom tour_dir override takes precedence over auto-locate.
  - Return shape contract.
"""
from __future__ import annotations

from pathlib import Path

# conftest.py adds SCRIPTS_ROOT to sys.path — diagnostics/ and build/ are
# sub-packages of that
from build.emit_tour_module import emit_module
from diagnostics.a11y_assertions import check


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

_CLEAN_RUNNER = """\
import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import { SPOTLIGHT_STEPS } from './spotlightSteps';

export function startSpotlightTour(onDone?: () => void): void {
  if (typeof window === 'undefined') return;
  const previouslyFocused =
    document.activeElement instanceof HTMLElement ? document.activeElement : null;
  const tour = driver({
    showProgress: true,
    showButtons: ['next', 'previous', 'close'],
    popoverClass: 'host-spotlight',
    steps: SPOTLIGHT_STEPS,
    onDestroyed: () => {
      previouslyFocused?.focus();
      onDone?.();
    },
  });
  tour.drive();
}
"""

_CLEAN_STEPS = """\
import type { DriveStep } from 'driver.js';

export const SPOTLIGHT_STEPS: DriveStep[] = [
  {
    element: '[data-tour="sidebar-nav"]',
    popover: {
      title: 'Sidebar',
      description: 'Navigate anywhere from here.',
      side: 'right',
      align: 'start',
    },
  },
];
"""


def _make_host(
    tmp_path: Path,
    tour_src: str | None = _CLEAN_RUNNER,
    steps_src: str | None = _CLEAN_STEPS,
    *,
    tour_subdir: str = "src/components/tour",
) -> Path:
    """Build a host-app tree with an (optional) emitted tour pair."""
    host = tmp_path / "host_app"
    tour_dir = host / tour_subdir
    tour_dir.mkdir(parents=True)
    if tour_src is not None:
        (tour_dir / "spotlightTour.ts").write_text(tour_src, encoding="utf-8")
    if steps_src is not None:
        (tour_dir / "spotlightSteps.ts").write_text(steps_src, encoding="utf-8")
    return host


def _finding_ids(result: dict, severity: str | None = None) -> set[str]:
    return {
        f["id"]
        for f in result["findings"]
        if severity is None or f["severity"] == severity
    }


# ---------------------------------------------------------------------------
# Self-coherence — the emitter's own output passes its own a11y gate
# ---------------------------------------------------------------------------

class TestEmitterOutputPasses:
    """emit_module output must satisfy every assertion by construction."""

    def _build_plan(self, app_path: str) -> dict:
        return {
            "substrate": "driver.js",
            "app_path": app_path,
            "anchor_attr": "data-tour",
            "audience": "b2c",
            "aha_moment": {"surface": "natal-chart"},
            "ranked_shortlist": [
                {"name": "sidebar-nav", "anchor": "sidebar-nav",
                 "purpose": "Navigate between app sections", "rank": 1},
                {"name": "natal-chart", "anchor": "natal-chart",
                 "purpose": "Your full natal chart, computed live", "rank": 2},
            ],
        }

    def test_fresh_emission_passes_clean(self, tmp_path):
        host = tmp_path / "host_app"
        tour_dir = host / "src" / "components" / "tour"
        tour_dir.mkdir(parents=True)

        result = emit_module(self._build_plan(str(host)))
        for rel_path, contents in result["files"].items():
            (tour_dir / rel_path).write_text(contents, encoding="utf-8")

        report = check(host)
        assert report["status"] == "pass", (
            f"Fresh emitter output should pass its own a11y gate.\n"
            f"Findings: {report['findings']}"
        )
        assert report["fail_count"] == 0
        assert report["warn_count"] == 0


# ---------------------------------------------------------------------------
# fail-level assertions
# ---------------------------------------------------------------------------

class TestFailLevel:
    def test_keyboard_control_disabled(self, tmp_path):
        runner = _CLEAN_RUNNER.replace(
            "showProgress: true,",
            "showProgress: true,\n    allowKeyboardControl: false,",
        )
        host = _make_host(tmp_path, tour_src=runner)
        report = check(host)
        assert "keyboard-control-disabled" in _finding_ids(report, "fail")
        assert report["status"] == "findings"

    def test_escape_hatch_removed(self, tmp_path):
        runner = _CLEAN_RUNNER.replace(
            "showProgress: true,",
            "showProgress: true,\n    allowClose: false,",
        )
        host = _make_host(tmp_path, tour_src=runner)
        report = check(host)
        assert "escape-hatch-removed" in _finding_ids(report, "fail")

    def test_close_button_removed(self, tmp_path):
        runner = _CLEAN_RUNNER.replace(
            "showButtons: ['next', 'previous', 'close'],",
            "showButtons: ['next', 'previous'],",
        )
        host = _make_host(tmp_path, tour_src=runner)
        report = check(host)
        assert "close-button-removed" in _finding_ids(report, "fail")


# ---------------------------------------------------------------------------
# warn-level assertions
# ---------------------------------------------------------------------------

class TestWarnLevel:
    def test_nav_buttons_missing(self, tmp_path):
        runner = _CLEAN_RUNNER.replace(
            "showButtons: ['next', 'previous', 'close'],",
            "showButtons: ['close'],",
        )
        host = _make_host(tmp_path, tour_src=runner)
        report = check(host)
        assert "nav-buttons-missing" in _finding_ids(report, "warn")
        # close is still present — no fail
        assert report["fail_count"] == 0

    def test_legacy_runner_focus_return_missing(self, tmp_path):
        """The pre-v0.3 emission shape: onDestroyed wired, no focus capture."""
        legacy = """\
import { driver } from 'driver.js';
import { SPOTLIGHT_STEPS } from './spotlightSteps';

export function startSpotlightTour(onDone?: () => void): void {
  if (typeof window === 'undefined') return;
  const tour = driver({
    showProgress: true,
    showButtons: ['next', 'previous', 'close'],
    popoverClass: 'host-spotlight',
    steps: SPOTLIGHT_STEPS,
    onDestroyed: () => {
      onDone?.();
    },
  });
  tour.drive();
}
"""
        host = _make_host(tmp_path, tour_src=legacy)
        report = check(host)
        assert "focus-return-missing" in _finding_ids(report, "warn")
        assert report["fail_count"] == 0, (
            "A legacy emission is degraded, not broken — warn only."
        )

    def test_destroy_hook_missing(self, tmp_path):
        runner = """\
import { driver } from 'driver.js';
import { SPOTLIGHT_STEPS } from './spotlightSteps';

export function startSpotlightTour(): void {
  if (typeof window === 'undefined') return;
  driver({ steps: SPOTLIGHT_STEPS }).drive();
}
"""
        host = _make_host(tmp_path, tour_src=runner)
        report = check(host)
        ids = _finding_ids(report, "warn")
        assert "destroy-hook-missing" in ids
        assert "focus-return-missing" in ids

    def test_step_copy_missing(self, tmp_path):
        steps = """\
export const SPOTLIGHT_STEPS = [
  {
    element: '[data-tour="sidebar-nav"]',
    popover: {
      title: 'Sidebar',
    },
  },
];
"""
        host = _make_host(tmp_path, steps_src=steps)
        report = check(host)
        assert "step-copy-missing" in _finding_ids(report, "warn")


# ---------------------------------------------------------------------------
# Defaults + graceful no-ops
# ---------------------------------------------------------------------------

class TestDefaultsAndNoOps:
    def test_show_buttons_absent_is_fine(self, tmp_path):
        """No showButtons option → driver.js shows all buttons by default."""
        runner = _CLEAN_RUNNER.replace(
            "    showButtons: ['next', 'previous', 'close'],\n", ""
        )
        host = _make_host(tmp_path, tour_src=runner)
        report = check(host)
        ids = _finding_ids(report)
        assert "close-button-removed" not in ids
        assert "nav-buttons-missing" not in ids

    def test_no_tour_module(self, tmp_path):
        host = _make_host(tmp_path, tour_src=None, steps_src=None)
        report = check(host)
        assert report["status"] == "no-tour"
        assert report["findings"] == []
        assert report["checked"] == []

    def test_steps_file_absent_skips_steps_checks(self, tmp_path):
        host = _make_host(tmp_path, steps_src=None)
        report = check(host)
        assert "step-copy-missing" not in report["checked"]
        assert report["steps_file"] is None
        # tour-module checks still ran
        assert "escape-hatch-removed" in report["checked"]

    def test_custom_tour_dir_override(self, tmp_path):
        host = _make_host(tmp_path, tour_subdir="lib/onboarding")
        report = check(host, tour_dir=host / "lib" / "onboarding")
        assert report["status"] == "pass"


# ---------------------------------------------------------------------------
# Return shape contract
# ---------------------------------------------------------------------------

class TestReturnShape:
    def test_contract_keys(self, tmp_path):
        host = _make_host(tmp_path)
        report = check(host)
        expected = {
            "status", "tour_dir", "tour_file", "steps_file",
            "findings", "fail_count", "warn_count", "checked",
        }
        assert set(report.keys()) == expected

    def test_counts_match_findings(self, tmp_path):
        runner = _CLEAN_RUNNER.replace(
            "showButtons: ['next', 'previous', 'close'],",
            "showButtons: ['next'],",
        ).replace(
            "showProgress: true,",
            "showProgress: true,\n    allowClose: false,",
        )
        host = _make_host(tmp_path, tour_src=runner)
        report = check(host)
        fails = [f for f in report["findings"] if f["severity"] == "fail"]
        warns = [f for f in report["findings"] if f["severity"] == "warn"]
        assert report["fail_count"] == len(fails)
        assert report["warn_count"] == len(warns)
        assert report["fail_count"] >= 2  # allowClose + close button
