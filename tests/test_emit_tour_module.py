"""
TDD tests for emit_tour_module.emit_module().

M3 — Phase 2 tour generator: Driver.js drop-in module emitter.

Covers:
  - 4-stop build-plan → exactly 4 steps, each with a data-tour selector
  - Runner imports driver, sets popoverClass, wires onDestroyed to onDone
  - startSpotlightTour export present
  - Replay export present (same function re-exported)
  - showProgress / progress indicator present
  - SSR guard present
  - D1 cap: 7-stop build-plan → exactly 5 steps emitted + split-recommendation warning
  - Copy: no step description exceeds 25 words
  - Output dict shape: {"files": {...}, "warnings": [...]}
  - Each emitted file maps a relative path to its string contents
"""
import pytest
import sys
from pathlib import Path

# conftest.py adds SCRIPTS_ROOT to sys.path — build/ is a sub-package of that
from build.emit_tour_module import emit_module


# ---------------------------------------------------------------------------
# Fixtures — build-plan shapes
# ---------------------------------------------------------------------------

def _build_plan_4_stops(audience: str = "b2c", substrate: str = "driver.js") -> dict:
    """A clean 4-stop build-plan — the nominal happy path."""
    return {
        "schema_version": 1,
        "app_path": "/projects/my-app",
        "mode": "walkthrough",
        "trigger_model": "auto-once-replay",
        "first_login_overlays": [],
        "substrate": substrate,
        "anchor_attr": "data-tour",
        "substrate_reason": "Default substrate resolved.",
        "substrate_overridden": False,
        "driver_js_version": None,
        "aha_moment": {
            "surface": "project-dashboard",
            "reason": "First view where value is tangible.",
        },
        "primary_user_role": "single",
        "two_tour_branching": False,
        "ranked_shortlist": [
            {
                "name": "project-dashboard",
                "file": "src/pages/Dashboard.tsx",
                "purpose": "Main workspace",
                "view": "page",
                "rank": 1,
                "anchor": "project-dashboard",
            },
            {
                "name": "create-project",
                "file": "src/components/CreateProject.tsx",
                "purpose": "Project creation flow",
                "view": "component",
                "rank": 2,
                "anchor": "create-project",
            },
            {
                "name": "activity-feed",
                "file": "src/components/ActivityFeed.tsx",
                "purpose": "Real-time updates",
                "view": "component",
                "rank": 3,
                "anchor": "activity-feed",
            },
            {
                "name": "team-invite",
                "file": "src/components/TeamInvite.tsx",
                "purpose": "Invite teammates",
                "view": "component",
                "rank": 4,
                "anchor": "team-invite",
            },
        ],
        "anchor_readiness": {
            "readiness": "ready",
            "risk_flags": [],
        },
        "product_summary": "A project management tool for small teams.",
        "audience": audience,
    }


def _build_plan_7_stops() -> dict:
    """7-stop build-plan — triggers the D1 5-step cap."""
    plan = _build_plan_4_stops()
    extra_stops = [
        {
            "name": f"extra-surface-{i}",
            "file": f"src/components/Extra{i}.tsx",
            "purpose": f"Extra surface {i}",
            "view": "component",
            "rank": 4 + i,
            "anchor": f"extra-surface-{i}",
        }
        for i in range(1, 4)  # adds 3 more → 7 total
    ]
    plan["ranked_shortlist"].extend(extra_stops)
    return plan


def _build_plan_ssr(substrate: str = "driver.js") -> dict:
    """Build-plan with an SSR-relevant substrate (Next.js context)."""
    plan = _build_plan_4_stops()
    plan["substrate"] = substrate
    plan["anchor_readiness"]["risk_flags"] = ["ssr"]
    return plan


def _build_plan_technical_audience() -> dict:
    return _build_plan_4_stops(audience="technical")


def _build_plan_b2b_audience() -> dict:
    return _build_plan_4_stops(audience="b2b")


# ---------------------------------------------------------------------------
# Return-shape contract
# ---------------------------------------------------------------------------

class TestReturnShape:
    """emit_module must always return {"files": {...}, "warnings": [...]}."""

    def test_returns_dict_with_files_and_warnings(self):
        result = emit_module(_build_plan_4_stops())
        assert isinstance(result, dict)
        assert "files" in result
        assert "warnings" in result

    def test_files_is_dict_of_str_to_str(self):
        result = emit_module(_build_plan_4_stops())
        files = result["files"]
        assert isinstance(files, dict)
        for key, value in files.items():
            assert isinstance(key, str), f"file key must be str, got {type(key)}"
            assert isinstance(value, str), f"file content must be str, got {type(value)}"

    def test_warnings_is_list(self):
        result = emit_module(_build_plan_4_stops())
        assert isinstance(result["warnings"], list)

    def test_emits_at_least_two_files(self):
        """Steps file + runner file = minimum two."""
        result = emit_module(_build_plan_4_stops())
        assert len(result["files"]) >= 2, (
            f"Expected at least 2 files, got {list(result['files'].keys())}"
        )

    def test_file_paths_contain_steps_and_tour(self):
        """File paths should include a steps file and a runner file."""
        result = emit_module(_build_plan_4_stops())
        paths = list(result["files"].keys())
        has_steps = any("steps" in p.lower() or "Steps" in p for p in paths)
        has_tour = any("tour" in p.lower() or "Tour" in p for p in paths)
        assert has_steps, f"No steps file in: {paths}"
        assert has_tour, f"No tour/runner file in: {paths}"


# ---------------------------------------------------------------------------
# D1 — 5-step cap
# ---------------------------------------------------------------------------

class TestD1StepCap:
    """Hard cap: never emit more than 5 steps. 7-stop plan → 5 steps + warning."""

    def test_4_stop_plan_emits_exactly_4_steps(self):
        result = emit_module(_build_plan_4_stops())
        steps_content = _get_steps_file(result)
        step_count = _count_steps_in_content(steps_content)
        assert step_count == 4, (
            f"Expected 4 steps for 4-stop plan, got {step_count}.\n{steps_content[:800]}"
        )

    def test_7_stop_plan_emits_exactly_5_steps(self):
        result = emit_module(_build_plan_7_stops())
        steps_content = _get_steps_file(result)
        step_count = _count_steps_in_content(steps_content)
        assert step_count == 5, (
            f"Expected 5 steps for 7-stop plan (D1 cap), got {step_count}.\n{steps_content[:800]}"
        )

    def test_7_stop_plan_emits_split_recommendation_warning(self):
        result = emit_module(_build_plan_7_stops())
        assert len(result["warnings"]) > 0, "Expected at least one warning for 7-stop plan"
        warning_text = " ".join(result["warnings"]).lower()
        has_split = "split" in warning_text or "first-run" in warning_text or "feature-discovery" in warning_text
        assert has_split, (
            f"Warning should recommend splitting the tour. Got: {result['warnings']}"
        )

    def test_4_stop_plan_has_no_cap_warning(self):
        """Under the cap → no split-recommendation warning."""
        result = emit_module(_build_plan_4_stops())
        cap_warnings = [w for w in result["warnings"] if "split" in w.lower() or "cap" in w.lower() or "5 step" in w.lower() or "5-step" in w.lower()]
        assert len(cap_warnings) == 0, (
            f"Unexpected cap warning for 4-stop plan: {cap_warnings}"
        )


# ---------------------------------------------------------------------------
# D4 — data-tour anchor selectors
# ---------------------------------------------------------------------------

class TestD4Anchors:
    """Each step must reference a data-tour selector."""

    def test_all_steps_have_data_tour_selector(self):
        result = emit_module(_build_plan_4_stops())
        steps_content = _get_steps_file(result)
        # Each step should have an element referencing data-tour
        assert '[data-tour=' in steps_content or "data-tour=" in steps_content, (
            f"Steps file should use data-tour selectors.\n{steps_content[:800]}"
        )

    def test_selector_count_matches_step_count(self):
        """Every step entry has exactly one element/selector."""
        result = emit_module(_build_plan_4_stops())
        steps_content = _get_steps_file(result)
        selector_count = steps_content.count("data-tour=")
        step_count = _count_steps_in_content(steps_content)
        assert selector_count == step_count, (
            f"selector_count={selector_count} != step_count={step_count}"
        )

    def test_selector_uses_anchor_from_build_plan(self):
        """Selectors should reference the anchor names from the ranked_shortlist."""
        plan = _build_plan_4_stops()
        result = emit_module(plan)
        steps_content = _get_steps_file(result)
        for stop in plan["ranked_shortlist"]:
            anchor = stop["anchor"]
            assert anchor in steps_content, (
                f"Anchor '{anchor}' not found in steps file.\n{steps_content[:800]}"
            )


# ---------------------------------------------------------------------------
# Runner — driver import, popoverClass, onDestroyed, startSpotlightTour export
# ---------------------------------------------------------------------------

class TestRunner:
    """The runner file must match the Celestia3 calibre."""

    def test_runner_imports_driver(self):
        result = emit_module(_build_plan_4_stops())
        runner = _get_runner_file(result)
        assert "driver" in runner, (
            f"Runner should import driver from driver.js.\n{runner[:600]}"
        )

    def test_runner_imports_from_driver_js(self):
        result = emit_module(_build_plan_4_stops())
        runner = _get_runner_file(result)
        assert "driver.js" in runner, (
            f"Runner should reference 'driver.js' (the package).\n{runner[:600]}"
        )

    def test_runner_sets_popover_class(self):
        result = emit_module(_build_plan_4_stops())
        runner = _get_runner_file(result)
        assert "popoverClass" in runner, (
            f"Runner should set popoverClass.\n{runner[:600]}"
        )

    def test_runner_wires_on_destroyed_to_on_done(self):
        result = emit_module(_build_plan_4_stops())
        runner = _get_runner_file(result)
        assert "onDestroyed" in runner, (
            f"Runner should wire onDestroyed callback.\n{runner[:600]}"
        )
        assert "onDone" in runner, (
            f"Runner should expose onDone parameter or invoke it.\n{runner[:600]}"
        )

    def test_runner_exports_start_spotlight_tour(self):
        result = emit_module(_build_plan_4_stops())
        runner = _get_runner_file(result)
        assert "startSpotlightTour" in runner, (
            f"Runner must export startSpotlightTour.\n{runner[:600]}"
        )
        assert "export" in runner, (
            f"Runner must use 'export' keyword.\n{runner[:600]}"
        )

    def test_runner_calls_drive(self):
        """Runner must call .drive() to start the tour."""
        result = emit_module(_build_plan_4_stops())
        runner = _get_runner_file(result)
        assert ".drive()" in runner, (
            f"Runner must call tour.drive().\n{runner[:600]}"
        )


# ---------------------------------------------------------------------------
# Progress indicator (showProgress)
# ---------------------------------------------------------------------------

class TestProgressIndicator:
    """showProgress: true must be present in the runner."""

    def test_show_progress_present_in_runner(self):
        result = emit_module(_build_plan_4_stops())
        runner = _get_runner_file(result)
        assert "showProgress" in runner, (
            f"Runner must include showProgress (progress indicator).\n{runner[:600]}"
        )
        # The value must be truthy (true or True)
        assert "showProgress: true" in runner or "showProgress:true" in runner, (
            f"showProgress must be set to true.\n{runner[:600]}"
        )


# ---------------------------------------------------------------------------
# Replay export
# ---------------------------------------------------------------------------

class TestReplayExport:
    """A replay entry point must be present and exported."""

    def test_replay_export_present(self):
        """startSpotlightTour is itself the replay entry point (persistent, ungated)."""
        result = emit_module(_build_plan_4_stops())
        runner = _get_runner_file(result)
        # The replay contract: startSpotlightTour is exported and callable any time.
        # A dedicated replaySpotlightTour export OR a comment flagging it as the replay entry.
        has_replay_export = (
            "replaySpotlightTour" in runner
            or "replay" in runner.lower()
        )
        assert has_replay_export, (
            f"Runner must include a replay export or replay entry point.\n{runner[:800]}"
        )


# ---------------------------------------------------------------------------
# SSR guard
# ---------------------------------------------------------------------------

class TestSSRGuard:
    """An SSR guard must appear in the runner (dynamic import / typeof window / useEffect)."""

    def test_ssr_guard_present_in_runner(self):
        result = emit_module(_build_plan_4_stops())
        runner = _get_runner_file(result)
        has_guard = (
            "typeof window" in runner
            or "useEffect" in runner
            or "dynamic import" in runner.lower()
            or "ssr" in runner.lower()
            or "SSR" in runner
            or "client" in runner.lower()
        )
        assert has_guard, (
            f"Runner must include an SSR guard.\n{runner[:800]}"
        )

    def test_ssr_guard_comment_or_pattern_present(self):
        """The SSR guard should be explicit — either a comment or a typeof window check."""
        result = emit_module(_build_plan_4_stops())
        runner = _get_runner_file(result)
        has_explicit_guard = (
            "typeof window" in runner
            or "window !== " in runner
            or "window ==" in runner
            or "SSR" in runner
            or "ssr" in runner.lower()
            or "// client" in runner.lower()
            or "/* client" in runner.lower()
        )
        assert has_explicit_guard, (
            f"SSR guard should be explicit (typeof window, SSR comment, etc.).\n{runner[:800]}"
        )


# ---------------------------------------------------------------------------
# Copy — benefit-led, ≤25 words/step
# ---------------------------------------------------------------------------

class TestCopy:
    """Every step description must be ≤25 words."""

    def test_no_step_description_exceeds_25_words(self):
        result = emit_module(_build_plan_4_stops())
        steps_content = _get_steps_file(result)
        descriptions = _extract_descriptions(steps_content)
        assert len(descriptions) > 0, "No descriptions found in steps file."
        for desc in descriptions:
            word_count = len(desc.split())
            assert word_count <= 25, (
                f"Description exceeds 25 words ({word_count} words): '{desc}'"
            )

    def test_no_step_description_exceeds_25_words_technical_audience(self):
        result = emit_module(_build_plan_technical_audience())
        steps_content = _get_steps_file(result)
        descriptions = _extract_descriptions(steps_content)
        for desc in descriptions:
            word_count = len(desc.split())
            assert word_count <= 25, (
                f"Description exceeds 25 words ({word_count} words): '{desc}'"
            )

    def test_no_step_description_exceeds_25_words_b2b_audience(self):
        result = emit_module(_build_plan_b2b_audience())
        steps_content = _get_steps_file(result)
        descriptions = _extract_descriptions(steps_content)
        for desc in descriptions:
            word_count = len(desc.split())
            assert word_count <= 25, (
                f"Description exceeds 25 words ({word_count} words): '{desc}'"
            )


# ---------------------------------------------------------------------------
# Audience register — copy register matches audience
# ---------------------------------------------------------------------------

class TestAudienceRegister:
    """Different audiences get different copy registers (spot-check, not full NLP)."""

    def test_b2c_steps_file_emitted(self):
        """B2C audience → steps file is emitted without error."""
        result = emit_module(_build_plan_4_stops(audience="b2c"))
        steps = _get_steps_file(result)
        assert len(steps) > 0

    def test_b2b_steps_file_emitted(self):
        result = emit_module(_build_plan_b2b_audience())
        steps = _get_steps_file(result)
        assert len(steps) > 0

    def test_technical_steps_file_emitted(self):
        result = emit_module(_build_plan_technical_audience())
        steps = _get_steps_file(result)
        assert len(steps) > 0


# ---------------------------------------------------------------------------
# Aha moment — step 1 routes to the aha surface
# ---------------------------------------------------------------------------

class TestAhaMoment:
    """The first step must reference the aha-moment surface."""

    def test_first_step_references_aha_moment(self):
        plan = _build_plan_4_stops()
        aha_anchor = plan["aha_moment"]["surface"]
        result = emit_module(plan)
        steps_content = _get_steps_file(result)

        # The aha anchor should appear first (or at least appear)
        assert aha_anchor in steps_content, (
            f"Aha moment anchor '{aha_anchor}' not found in steps.\n{steps_content[:800]}"
        )

        # It should be the first step — the first selector occurrence should be the aha anchor
        first_selector_pos = steps_content.find("data-tour=")
        aha_pos = steps_content.find(aha_anchor)
        assert aha_pos <= first_selector_pos + 100, (
            f"Aha moment should appear near the first step.\n"
            f"first_selector at {first_selector_pos}, aha at {aha_pos}.\n{steps_content[:800]}"
        )


# ---------------------------------------------------------------------------
# popoverClass naming
# ---------------------------------------------------------------------------

class TestPopoverClass:
    """popoverClass should be derived from the app path or a reasonable default."""

    def test_popover_class_is_non_empty_string(self):
        result = emit_module(_build_plan_4_stops())
        runner = _get_runner_file(result)
        # Extract the value after popoverClass:
        idx = runner.find("popoverClass")
        assert idx != -1, "popoverClass not found"
        snippet = runner[idx:idx + 80]
        # Should have a non-empty string value
        assert "'" in snippet or '"' in snippet or "`" in snippet, (
            f"popoverClass value not found as string near: {snippet}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_steps_file(result: dict) -> str:
    """Return the content of the steps file from the result."""
    files = result["files"]
    for path, content in files.items():
        if "steps" in path.lower() or "Steps" in path:
            return content
    # Fallback: return the largest file (heuristic)
    if files:
        return max(files.values(), key=len)
    return ""


def _get_runner_file(result: dict) -> str:
    """Return the content of the runner/tour file from the result."""
    files = result["files"]
    # Prefer file with 'tour' but not 'steps' in the path
    for path, content in files.items():
        if ("tour" in path.lower() or "Tour" in path) and "steps" not in path.lower() and "Steps" not in path:
            return content
    # Fallback: return anything that has 'export function'
    for path, content in files.items():
        if "export function" in content or "export const" in content:
            return content
    if files:
        return min(files.values(), key=len)  # runner tends to be shorter
    return ""


def _count_steps_in_content(content: str) -> int:
    """
    Count DriveStep entries in the steps file.
    Uses two heuristics: 'element:' line count or popover block count.
    """
    # Primary: count 'element:' occurrences (one per step)
    count = content.count("element:")
    if count > 0:
        return count
    # Fallback: count 'popover:' occurrences
    count = content.count("popover:")
    if count > 0:
        return count
    # Last resort: count opening braces that look like step objects
    # (a DriveStep array entry starts with "  {")
    import re
    matches = re.findall(r"^\s*\{", content, re.MULTILINE)
    return max(0, len(matches) - 1)  # -1 for the outer array open


def _extract_descriptions(content: str) -> list:
    """
    Extract description values from a steps file.
    Handles TypeScript string literals: 'text', "text", `text`.
    """
    import re
    descriptions = []
    for match in re.finditer(r"description:\s*['\"`]([^'\"`]{1,300})['\"`]", content):
        descriptions.append(match.group(1).strip())
    return descriptions
