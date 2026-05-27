"""
Tests for diagnostics.anchor_drift.detect().

Covers:
  - Clean state: every spotlightSteps.ts anchor has a matching data-tour=
    in source → status "clean", drift_count 0.
  - Missing anchor: anchor in steps file but not in source → reported in
    `missing`.
  - Orphan anchor: data-tour= in source but not in steps file → reported
    in `orphan` with file + line.
  - Partial drift: a mix of clean, missing, and orphan in one host →
    each surfaces correctly without poisoning the others.
  - No spotlightSteps.ts: status "no-tour", graceful no-op (no false drift).
  - No source files: status "no-source" — distinguishable from drift.
  - Multi-file source: an anchor present in two source files is still
    treated as a single source-side presence (the anchor is satisfied).
  - Skip directories: anchors inside node_modules / .next / dist are
    ignored entirely.
  - Single + double quote attribute styles are both recognized.
  - Custom tour_dir / source_root overrides take precedence over auto-locate.
  - Return shape contract.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

# conftest.py adds SCRIPTS_ROOT to sys.path — diagnostics/ is a sub-package of that
from diagnostics.anchor_drift import detect


# ---------------------------------------------------------------------------
# Fixture builders — build a minimal "host app" tree under tmp_path
# ---------------------------------------------------------------------------

def _make_host(
    tmp_path: Path,
    steps_anchors: list[str] | None = None,
    source_files: dict[str, str] | None = None,
    *,
    tour_subdir: str = "src/components/tour",
) -> Path:
    """
    Build a host-app directory tree.

    Parameters
    ----------
    tmp_path
        Pytest's tmp_path fixture.
    steps_anchors
        Anchors to embed as element selectors in spotlightSteps.ts.
        Pass None to skip emitting the steps file entirely (simulates
        a host that hasn't run the tour build).
    source_files
        Map of relative-to-host source paths → file contents.
        Defaults to a single empty src/App.tsx if not provided.

    Returns the host app root path.
    """
    host = tmp_path / "host_app"
    host.mkdir()

    # Steps file (optional — omit to test no-tour path)
    if steps_anchors is not None:
        tour_dir = host / tour_subdir
        tour_dir.mkdir(parents=True, exist_ok=True)
        step_entries = "\n".join(
            f"  {{ element: '[data-tour=\"{a}\"]', popover: {{ title: 'x', description: 'y' }} }},"
            for a in steps_anchors
        )
        (tour_dir / "spotlightSteps.ts").write_text(
            "export const SPOTLIGHT_STEPS = [\n" + step_entries + "\n];\n",
            encoding="utf-8",
        )

    # Source files (defaults to an empty App if none provided)
    src = host / "src"
    src.mkdir(parents=True, exist_ok=True)
    if not source_files:
        (src / "App.tsx").write_text("export const App = () => null;\n", encoding="utf-8")
    else:
        for rel_path, content in source_files.items():
            full = host / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")

    return host


def _jsx_with_anchor(anchor: str, quote: str = '"') -> str:
    """Return a tiny JSX file body containing one data-tour attribute."""
    q = quote
    return textwrap.dedent(f"""
        import React from 'react';
        export function Card() {{
          return <div data-tour={q}{anchor}{q}>Hello</div>;
        }}
    """).lstrip()


# ---------------------------------------------------------------------------
# Return-shape contract
# ---------------------------------------------------------------------------

class TestReturnShape:
    """detect() must always return the full dict shape with every key present."""

    REQUIRED_KEYS = {
        "status", "tour_dir", "steps_file", "steps_anchors",
        "source_anchors", "missing", "orphan", "drift_count",
        "last_emit", "scanned_files",
    }

    def test_clean_state_returns_all_keys(self, tmp_path):
        host = _make_host(
            tmp_path,
            steps_anchors=["foo"],
            source_files={"src/Foo.tsx": _jsx_with_anchor("foo")},
        )
        result = detect(host)
        assert isinstance(result, dict)
        assert self.REQUIRED_KEYS.issubset(result.keys()), (
            f"Missing keys: {self.REQUIRED_KEYS - result.keys()}"
        )

    def test_no_tour_returns_all_keys(self, tmp_path):
        host = _make_host(tmp_path, steps_anchors=None)
        result = detect(host)
        assert self.REQUIRED_KEYS.issubset(result.keys())
        assert result["status"] == "no-tour"


# ---------------------------------------------------------------------------
# Clean state
# ---------------------------------------------------------------------------

class TestCleanState:
    """Every steps anchor has a matching source attribute → no drift."""

    def test_one_anchor_clean(self, tmp_path):
        host = _make_host(
            tmp_path,
            steps_anchors=["nav-bar"],
            source_files={"src/Nav.tsx": _jsx_with_anchor("nav-bar")},
        )
        result = detect(host)
        assert result["status"] == "clean"
        assert result["drift_count"] == 0
        assert result["missing"] == []
        assert result["orphan"] == []
        assert result["last_emit"] is not None  # mtime captured

    def test_multiple_anchors_clean(self, tmp_path):
        anchors = ["nav-bar", "dashboard", "create-button"]
        host = _make_host(
            tmp_path,
            steps_anchors=anchors,
            source_files={
                "src/Nav.tsx":       _jsx_with_anchor("nav-bar"),
                "src/Dashboard.tsx": _jsx_with_anchor("dashboard"),
                "src/Create.tsx":    _jsx_with_anchor("create-button"),
            },
        )
        result = detect(host)
        assert result["status"] == "clean"
        assert sorted(result["steps_anchors"]) == sorted(anchors)
        assert result["scanned_files"] >= 3

    def test_anchor_present_in_two_files_is_still_clean(self, tmp_path):
        """An anchor used by multiple components is satisfied — not a drift."""
        host = _make_host(
            tmp_path,
            steps_anchors=["shared"],
            source_files={
                "src/A.tsx": _jsx_with_anchor("shared"),
                "src/B.tsx": _jsx_with_anchor("shared"),
            },
        )
        result = detect(host)
        assert result["status"] == "clean"
        assert result["missing"] == []
        # Both occurrences still appear in source_anchors (no dedup at scan)
        anchors_only = [e["anchor"] for e in result["source_anchors"]]
        assert anchors_only.count("shared") == 2


# ---------------------------------------------------------------------------
# Missing anchors — in steps, not in source
# ---------------------------------------------------------------------------

class TestMissingAnchor:
    def test_single_missing(self, tmp_path):
        host = _make_host(
            tmp_path,
            steps_anchors=["was-removed"],
            source_files={"src/App.tsx": "export const App = () => <div>nothing here</div>;\n"},
        )
        result = detect(host)
        assert result["status"] == "drift"
        assert result["missing"] == ["was-removed"]
        assert result["orphan"] == []
        assert result["drift_count"] == 1

    def test_some_missing_some_clean(self, tmp_path):
        host = _make_host(
            tmp_path,
            steps_anchors=["keeps", "removed-a", "removed-b"],
            source_files={"src/A.tsx": _jsx_with_anchor("keeps")},
        )
        result = detect(host)
        assert result["status"] == "drift"
        assert result["missing"] == ["removed-a", "removed-b"]  # sorted
        assert result["orphan"] == []


# ---------------------------------------------------------------------------
# Orphan anchors — in source, not in steps
# ---------------------------------------------------------------------------

class TestOrphanAnchor:
    def test_single_orphan_reports_file_and_line(self, tmp_path):
        host = _make_host(
            tmp_path,
            steps_anchors=["used"],
            source_files={
                "src/Used.tsx":  _jsx_with_anchor("used"),
                "src/Stale.tsx": _jsx_with_anchor("stale-anchor"),
            },
        )
        result = detect(host)
        assert result["status"] == "drift"
        assert result["missing"] == []
        assert len(result["orphan"]) == 1
        orphan = result["orphan"][0]
        assert orphan["anchor"] == "stale-anchor"
        assert orphan["file"] == "Stale.tsx"
        assert orphan["line"] >= 1
        assert result["drift_count"] == 1


# ---------------------------------------------------------------------------
# Partial drift — mix of clean + missing + orphan
# ---------------------------------------------------------------------------

class TestPartialDrift:
    def test_mixed_drift_isolates_each_class(self, tmp_path):
        host = _make_host(
            tmp_path,
            steps_anchors=["clean-one", "missing-one"],
            source_files={
                "src/Clean.tsx":  _jsx_with_anchor("clean-one"),
                "src/Orphan.tsx": _jsx_with_anchor("orphan-one"),
            },
        )
        result = detect(host)
        assert result["status"] == "drift"
        assert result["missing"] == ["missing-one"]
        assert [o["anchor"] for o in result["orphan"]] == ["orphan-one"]
        assert result["drift_count"] == 2


# ---------------------------------------------------------------------------
# No-tour / no-source — graceful skips, NOT false drift reports
# ---------------------------------------------------------------------------

class TestGracefulNoOp:
    def test_no_steps_file_is_no_tour_status(self, tmp_path):
        """When the host hasn't built a tour yet, drift detection is a no-op."""
        host = _make_host(tmp_path, steps_anchors=None)
        result = detect(host)
        assert result["status"] == "no-tour"
        assert result["drift_count"] == 0
        assert result["missing"] == []
        assert result["orphan"] == []
        assert result["steps_file"] is None

    def test_no_source_files_is_no_source_status(self, tmp_path):
        """Steps file present, but src/ is empty → no-source (not 'all missing')."""
        host = _make_host(tmp_path, steps_anchors=["foo"], source_files={})
        # Wipe the default src/App.tsx that _make_host writes
        (host / "src" / "App.tsx").unlink()
        result = detect(host)
        assert result["status"] == "no-source"
        assert result["scanned_files"] == 0
        # Don't report drift when there's nothing to compare against
        assert result["missing"] == []
        assert result["drift_count"] == 0


# ---------------------------------------------------------------------------
# Skip directories — node_modules, .next, dist, build
# ---------------------------------------------------------------------------

class TestSkipDirectories:
    def test_anchor_in_node_modules_is_ignored(self, tmp_path):
        """Don't surface drift from third-party packages."""
        host = _make_host(
            tmp_path,
            steps_anchors=["wanted"],
            source_files={
                "src/Real.tsx":                       _jsx_with_anchor("wanted"),
                "node_modules/lib/dist/Stale.tsx":    _jsx_with_anchor("vendor-junk"),
            },
        )
        result = detect(host)
        assert result["status"] == "clean", (
            f"Vendor anchor should be ignored; got {result['orphan']}"
        )
        for entry in result["source_anchors"]:
            assert "node_modules" not in entry["file"]

    def test_anchor_in_dist_is_ignored(self, tmp_path):
        host = _make_host(
            tmp_path,
            steps_anchors=["foo"],
            source_files={
                "src/Foo.tsx": _jsx_with_anchor("foo"),
                "dist/Compiled.js": _jsx_with_anchor("compiled-orphan"),
            },
        )
        result = detect(host)
        assert result["status"] == "clean"


# ---------------------------------------------------------------------------
# Quote-style coverage — both single and double quotes
# ---------------------------------------------------------------------------

class TestQuoteStyles:
    def test_single_quote_attribute_is_detected(self, tmp_path):
        host = _make_host(
            tmp_path,
            steps_anchors=["singleq"],
            source_files={"src/SQ.tsx": _jsx_with_anchor("singleq", quote="'")},
        )
        result = detect(host)
        assert result["status"] == "clean"


# ---------------------------------------------------------------------------
# Overrides — tour_dir / source_root take precedence over auto-locate
# ---------------------------------------------------------------------------

class TestOverrides:
    def test_custom_tour_dir_is_honored(self, tmp_path):
        """A non-default tour directory location resolves via the override."""
        host = _make_host(
            tmp_path,
            steps_anchors=["x"],
            source_files={"src/X.tsx": _jsx_with_anchor("x")},
            tour_subdir="some/wild/path",
        )
        result = detect(host, tour_dir=host / "some" / "wild" / "path")
        assert result["status"] == "clean"
        assert result["tour_dir"].endswith("path") or "wild" in result["tour_dir"]
