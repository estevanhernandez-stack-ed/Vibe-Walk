"""
Tests for anchor_readiness.assess().

Fixture repos used:
  tour_worthy_app  — has both id= and data-tour= attrs across multiple components → "ready"
  no_selectors_app — Tailwind-only, zero id/data-* → "none" + risk flags
  blank_canvas_app — has id= and data-tour= but triggers tailwind_only detection? No — has stable attrs.

Additional inline fixtures tested via tmp directories.
"""
import os
import pytest
from pathlib import Path

from discovery.anchor_readiness import assess

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# tour_worthy_app — has id= and data-tour= throughout → ready
# ---------------------------------------------------------------------------

def test_tour_worthy_app_is_ready():
    result = assess(str(FIXTURES / "tour_worthy_app"))
    assert result["readiness"] == "ready"
    assert isinstance(result["risk_flags"], list)
    # No high-risk flags expected for a clean fixture
    assert "no_stable_selectors" not in result["risk_flags"]


def test_tour_worthy_app_has_no_critical_flags():
    result = assess(str(FIXTURES / "tour_worthy_app"))
    critical = {"shadow_dom", "cross_origin_iframe", "no_stable_selectors"}
    flagged = set(result["risk_flags"])
    overlap = critical & flagged
    assert not overlap, f"Unexpected critical flags: {overlap}"


# ---------------------------------------------------------------------------
# no_selectors_app — Tailwind-only, zero id/data-* → "none"
# ---------------------------------------------------------------------------

def test_no_selectors_app_is_none():
    result = assess(str(FIXTURES / "no_selectors_app"))
    assert result["readiness"] == "none"


def test_no_selectors_app_flags_no_stable_selectors():
    result = assess(str(FIXTURES / "no_selectors_app"))
    assert "no_stable_selectors" in result["risk_flags"]


def test_no_selectors_app_flags_tailwind_only():
    result = assess(str(FIXTURES / "no_selectors_app"))
    assert "tailwind_only" in result["risk_flags"]


# ---------------------------------------------------------------------------
# Single-purpose tool — minimal surface, has no stable selectors in App.tsx
# (only className usages, no id or data-*)
# ---------------------------------------------------------------------------

def test_single_purpose_no_stable_selectors():
    result = assess(str(FIXTURES / "single_purpose_tool"))
    # App.tsx has no id= or data-* attrs
    assert result["readiness"] in ("none", "needs-pass")
    assert "no_stable_selectors" in result["risk_flags"]


# ---------------------------------------------------------------------------
# Shadow DOM fixture — inline tmp fixture
# ---------------------------------------------------------------------------

def test_shadow_dom_flag(tmp_path):
    comp = tmp_path / "src" / "Widget.tsx"
    comp.parent.mkdir(parents=True)
    comp.write_text(
        "import React from 'react';\n"
        "export default function Widget() {\n"
        "  const ref = React.useRef(null);\n"
        "  React.useEffect(() => {\n"
        "    const shadow = ref.current.attachShadow({ mode: 'open' });\n"
        "    shadow.innerHTML = '<p>Shadow content</p>';\n"
        "  }, []);\n"
        "  return <div ref={ref} id='shadow-host' />;\n"
        "}\n",
        encoding="utf-8",
    )
    result = assess(str(tmp_path))
    assert "shadow_dom" in result["risk_flags"]


# ---------------------------------------------------------------------------
# Cross-origin iframe fixture — inline tmp fixture
# ---------------------------------------------------------------------------

def test_cross_origin_iframe_flag(tmp_path):
    page = tmp_path / "src" / "EmbedPage.tsx"
    page.parent.mkdir(parents=True)
    page.write_text(
        "export default function EmbedPage() {\n"
        "  return <iframe src='https://external.example.com/widget' />;\n"
        "}\n",
        encoding="utf-8",
    )
    result = assess(str(tmp_path))
    assert "cross_origin_iframe" in result["risk_flags"]


# ---------------------------------------------------------------------------
# CSS Modules — detects *.module.css / *.module.scss
# ---------------------------------------------------------------------------

def test_css_modules_flag(tmp_path):
    styles = tmp_path / "src" / "Button.module.css"
    styles.parent.mkdir(parents=True)
    styles.write_text(".btn { color: red; }\n", encoding="utf-8")
    comp = tmp_path / "src" / "Button.tsx"
    comp.write_text(
        "import styles from './Button.module.css';\n"
        "export default function Button() {\n"
        "  return <button className={styles.btn}>Click</button>;\n"
        "}\n",
        encoding="utf-8",
    )
    result = assess(str(tmp_path))
    assert "css_modules" in result["risk_flags"]


# ---------------------------------------------------------------------------
# needs-pass: has some stable selectors but many components lack them
# ---------------------------------------------------------------------------

def test_needs_pass_when_partial_coverage(tmp_path):
    """Repo with some id= attrs but many components without → needs-pass."""
    src = tmp_path / "src"
    src.mkdir()
    # One component with stable selectors
    (src / "WithId.tsx").write_text(
        "export default function WithId() {\n"
        "  return <div id='main-panel' data-tour='main-panel'><p>content</p></div>;\n"
        "}\n",
        encoding="utf-8",
    )
    # Several without
    for name in ["NoId1.tsx", "NoId2.tsx", "NoId3.tsx"]:
        (src / name).write_text(
            f"export default function {name[:-4]}() {{\n"
            "  return <div className='box'><span className='label'>text</span></div>;\n"
            "}\n",
            encoding="utf-8",
        )
    result = assess(str(tmp_path))
    # Partial coverage → needs-pass or none (both acceptable; not "ready")
    assert result["readiness"] in ("needs-pass", "none")


# ---------------------------------------------------------------------------
# Result shape contract
# ---------------------------------------------------------------------------

def test_result_shape():
    result = assess(str(FIXTURES / "tour_worthy_app"))
    assert "readiness" in result
    assert "risk_flags" in result
    assert result["readiness"] in ("ready", "needs-pass", "none")
    assert isinstance(result["risk_flags"], list)


def test_nonexistent_path_returns_none_with_flag():
    """Graceful handling of a path that doesn't exist."""
    result = assess("/nonexistent/path/to/repo")
    assert result["readiness"] == "none"
    assert "path_not_found" in result["risk_flags"]
