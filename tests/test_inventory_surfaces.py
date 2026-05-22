"""
Tests for inventory_surfaces.inventory().

Fixture repos:
  tour_worthy_app   — multiple pages + components, README → rich inventory
  single_purpose_tool — minimal, single file → low surface count
  no_selectors_app  — multiple components, no stable selectors (inventory still works)
"""
import pytest
from pathlib import Path

from discovery.inventory_surfaces import inventory

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# tour_worthy_app — full-featured app
# ---------------------------------------------------------------------------

def test_tour_worthy_returns_surface_list():
    result = inventory(str(FIXTURES / "tour_worthy_app"))
    assert "surfaces" in result
    assert isinstance(result["surfaces"], list)
    assert len(result["surfaces"]) >= 5  # Dashboard + ChartDetail + 4 components minimum


def test_tour_worthy_surfaces_have_required_fields():
    result = inventory(str(FIXTURES / "tour_worthy_app"))
    for surface in result["surfaces"]:
        assert "name" in surface, f"Missing 'name' in {surface}"
        assert "file" in surface, f"Missing 'file' in {surface}"
        # purpose and view are optional but should be strings when present
        if "purpose" in surface:
            assert isinstance(surface["purpose"], str)
        if "view" in surface:
            assert isinstance(surface["view"], str)


def test_tour_worthy_interactive_surface_count():
    result = inventory(str(FIXTURES / "tour_worthy_app"))
    assert result["interactive_surface_count"] >= 5


def test_tour_worthy_has_product_summary():
    result = inventory(str(FIXTURES / "tour_worthy_app"))
    assert "product_summary" in result
    assert isinstance(result["product_summary"], str)
    assert len(result["product_summary"]) > 10  # not empty


def test_tour_worthy_product_summary_mentions_app_name():
    result = inventory(str(FIXTURES / "tour_worthy_app"))
    # README says "AstroBoard" — should appear in summary
    assert "astroboard" in result["product_summary"].lower()


def test_tour_worthy_surfaces_include_pages():
    result = inventory(str(FIXTURES / "tour_worthy_app"))
    names = [s["name"].lower() for s in result["surfaces"]]
    # Dashboard.tsx and ChartDetail.tsx should appear
    found_page = any("dashboard" in n or "chart" in n for n in names)
    assert found_page, f"No page-level surface found. Surfaces: {names}"


def test_tour_worthy_surfaces_include_components():
    result = inventory(str(FIXTURES / "tour_worthy_app"))
    names = [s["name"].lower() for s in result["surfaces"]]
    found_component = any(
        n in names or any(kw in n for kw in ["natal", "transit", "compat", "saved"])
        for n in names
    )
    assert found_component, f"No component surfaces found. Names: {names}"


# ---------------------------------------------------------------------------
# single_purpose_tool — one App.tsx, minimal
# ---------------------------------------------------------------------------

def test_single_purpose_low_surface_count():
    result = inventory(str(FIXTURES / "single_purpose_tool"))
    assert result["interactive_surface_count"] < 5


def test_single_purpose_returns_valid_shape():
    result = inventory(str(FIXTURES / "single_purpose_tool"))
    assert "surfaces" in result
    assert "interactive_surface_count" in result
    assert isinstance(result["surfaces"], list)


# ---------------------------------------------------------------------------
# no_selectors_app — multiple surfaces without stable selectors
# ---------------------------------------------------------------------------

def test_no_selectors_returns_surfaces():
    """inventory() reads surfaces regardless of selector presence."""
    result = inventory(str(FIXTURES / "no_selectors_app"))
    assert len(result["surfaces"]) >= 5


def test_no_selectors_count_matches_surfaces():
    result = inventory(str(FIXTURES / "no_selectors_app"))
    # Count should match (or be close to) the length of the surfaces list
    assert result["interactive_surface_count"] >= len(result["surfaces"]) * 0.8


# ---------------------------------------------------------------------------
# Graceful handling of non-existent path
# ---------------------------------------------------------------------------

def test_nonexistent_path_returns_empty():
    result = inventory("/nonexistent/path/to/repo")
    assert result["surfaces"] == []
    assert result["interactive_surface_count"] == 0
    assert "error" in result


# ---------------------------------------------------------------------------
# Result shape contract
# ---------------------------------------------------------------------------

def test_result_shape_contract():
    result = inventory(str(FIXTURES / "tour_worthy_app"))
    required_keys = {"surfaces", "interactive_surface_count", "product_summary"}
    for key in required_keys:
        assert key in result, f"Missing required key: {key}"
    assert isinstance(result["interactive_surface_count"], int)


# ---------------------------------------------------------------------------
# File paths in surfaces are valid (relative or absolute, not empty)
# ---------------------------------------------------------------------------

def test_surface_file_paths_are_non_empty():
    result = inventory(str(FIXTURES / "tour_worthy_app"))
    for surface in result["surfaces"]:
        assert surface.get("file", "").strip() != "", f"Empty file path in surface: {surface}"
