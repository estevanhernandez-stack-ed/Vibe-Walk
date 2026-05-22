"""
inventory_surfaces.py — Phase 1: surface reader.

inventory(repo_path: str) -> dict

Reads orientation docs (README, DOCS, CLAUDE.md) + the route/page surface +
component composition to build a structured inventory of user-facing surfaces.

Mirrors the Explore pass described in the Vibe-Walk cowpath (process-notes.md):
  1. Read README / DOCS / CLAUDE.md for a product summary.
  2. Find page-level files (routes / views).
  3. Find component files imported by or co-located with those pages.
  4. Produce a structured surface list + interactive_surface_count.

Returns
-------
dict:
    product_summary      : str    — 1–4 sentence product description from docs.
    surfaces             : list   — each item has {name, file, purpose?, view?}
    interactive_surface_count : int
    error                : str?   — only present when repo_path is invalid
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Skip dirs (same as anchor_readiness)
# ---------------------------------------------------------------------------
_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "dist", "build", ".next",
    "coverage", ".turbo", "out", ".cache", "vendor", "venv", ".venv",
    "tests", "test", "spec", "__tests__", "stories", "storybook",
}

# Source extensions we consider component / page files
_SOURCE_EXTENSIONS = {".tsx", ".ts", ".jsx", ".js", ".vue", ".svelte"}

# Page/view detection heuristics
# File names that suggest a view/page/route level component
_PAGE_PATTERNS = re.compile(
    r"(?i)(page|view|screen|route|layout|dashboard|home|index|app)\b"
)

# Component detection: PascalCase file names in /components/ or /src/ directories
_COMPONENT_DIR_PATTERNS = re.compile(r"(?i)(components?|widgets?|panels?|features?|modules?)")

# Regex to detect interactive elements in source
_RE_INTERACTIVE = re.compile(
    r"<(button|input|select|textarea|a\b|form|[A-Z][A-Za-z]*(?:Button|Form|Input|Field|"
    r"Panel|Modal|Drawer|Dialog|Tab|Menu|Dropdown|Widget|Card|Table|List|Sidebar|Nav|"
    r"Header|Footer|Chart|Calendar|Picker|Toggle|Switch|Slider))[^>]*>"
)

# Orientation doc names (in priority order)
_ORIENTATION_DOCS = [
    "CLAUDE.md", "README.md", "readme.md", "README", "docs/README.md",
    "DOCS.md", "docs.md", "OVERVIEW.md", "overview.md",
]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def inventory(repo_path: str) -> dict:
    """
    Read repo_path and produce a surface inventory.

    Parameters
    ----------
    repo_path : str
        Absolute path to the root of the target repository.

    Returns
    -------
    dict with required keys: surfaces, interactive_surface_count, product_summary.
    """
    path = Path(repo_path)

    if not path.exists():
        return {
            "surfaces": [],
            "interactive_surface_count": 0,
            "product_summary": "",
            "error": f"Path not found: {repo_path}",
        }

    # 1. Read orientation docs for product summary
    product_summary = _read_product_summary(path)

    # 2. Collect all source files
    source_files = _collect_source_files(path)

    # 3. Classify each file as page-level, component-level, or neither
    surfaces: list[dict] = []
    for fpath in source_files:
        surface = _classify_file(fpath, path)
        if surface:
            surfaces.append(surface)

    # 4. Deduplicate by name (keep first seen)
    seen_names: set[str] = set()
    deduped: list[dict] = []
    for s in surfaces:
        if s["name"] not in seen_names:
            seen_names.add(s["name"])
            deduped.append(s)

    # 5. Count interactive surfaces
    interactive_count = _count_interactive(deduped, path)

    return {
        "product_summary": product_summary,
        "surfaces": deduped,
        "interactive_surface_count": interactive_count,
    }


# ---------------------------------------------------------------------------
# Orientation doc reader
# ---------------------------------------------------------------------------

def _read_product_summary(root: Path) -> str:
    """
    Extract a 1–4 sentence product summary from the first orientation doc found.
    Returns the first non-empty paragraph (up to 400 chars) from the doc.

    CLAUDE.md is tried first (highest priority for product-aware context). If the
    extracted summary is suspiciously short, starts with an HTML comment (e.g. a
    gitnexus:start / AI-INDEX tooling preamble), or contains only markup, the next
    orientation doc in the priority list is tried as a fallback.

    Within a single doc, multiple paragraphs are extracted; the first non-tainted
    paragraph wins. This handles the pattern where CLAUDE.md opens with a tooling
    preamble section followed by real product description.
    """
    first_tainted: str | None = None  # fallback of last resort

    for doc_name in _ORIENTATION_DOCS:
        doc_path = root / doc_name
        if doc_path.exists():
            try:
                content = doc_path.read_text(encoding="utf-8", errors="ignore")
                # Try all paragraphs in this doc — stop at the first clean one.
                for para in _extract_all_paragraphs(content, doc_path.name):
                    if not _is_tooling_preamble(para):
                        return para
                    if first_tainted is None:
                        first_tainted = para
            except OSError:
                continue

    # All candidates were tainted — return whatever we scraped, or empty.
    return first_tainted or ""


_RE_HTML_COMMENT_START = re.compile(r"^\s*<!--")
_TOOLING_PREAMBLE_MARKERS = (
    "gitnexus",
    "ai-index",
    "ai index",
    "auto-generated",
    "do not edit",
    "repo index",
)
_MIN_QUALITY_CHARS = 30


def _is_tooling_preamble(summary: str) -> bool:
    """
    Return True if the summary looks like a tooling preamble rather than a real
    product description. Triggers:
      - Starts with an HTML comment (<!-- ... -->)
      - Contains known tooling preamble markers
      - Is suspiciously short (< 30 chars) after stripping markup
    """
    if not summary:
        return True
    # HTML comment at start
    if _RE_HTML_COMMENT_START.match(summary):
        return True
    # Known tooling preamble markers
    summary_lower = summary.lower()
    if any(marker in summary_lower for marker in _TOOLING_PREAMBLE_MARKERS):
        return True
    # Too short to be a real description
    clean = re.sub(r"<!--.*?-->", "", summary, flags=re.DOTALL).strip()
    if len(clean) < _MIN_QUALITY_CHARS:
        return True
    return False


def _extract_all_paragraphs(content: str, filename: str) -> list[str]:
    """
    Extract all meaningful paragraphs from a markdown/text doc.
    Skips:
      - H1 title lines (# Foo) at the top
      - Horizontal rules, badges, shields
      - HTML comment blocks (<!-- ... -->) such as gitnexus:start / AI-INDEX headers
      - Content bracketed between gitnexus/tooling delimiter comment lines
    Each returned paragraph is capped at 400 chars.
    """
    lines = content.splitlines()
    paragraphs: list[str] = []
    current: list[str] = []
    in_html_comment = False
    # Track whether we are inside a known tooling section (e.g. between <!-- gitnexus:start -->
    # and <!-- gitnexus:end --> where the text between the delimiters is tooling boilerplate).
    in_tooling_section = False

    for line in lines:
        stripped = line.strip()

        # Track HTML comment blocks (<!-- ... --> may span multiple lines)
        if in_html_comment:
            if "-->" in stripped:
                in_html_comment = False
            continue  # skip all lines inside a comment block

        if stripped.startswith("<!--"):
            # Check for known tooling section delimiters before handling as a comment
            stripped_lower = stripped.lower()
            if any(marker in stripped_lower for marker in ("gitnexus:start", "ai-index:start", "tooling:start")):
                in_tooling_section = True
            elif any(marker in stripped_lower for marker in ("gitnexus:end", "ai-index:end", "tooling:end")):
                in_tooling_section = False

            if "-->" in stripped:
                # Single-line comment — skip this line and continue
                continue
            else:
                # Multi-line comment opens here
                in_html_comment = True
                continue

        # Skip content inside a known tooling section
        if in_tooling_section:
            continue

        # Skip H1 title line (# Foo) at the very top (before any paragraph has started)
        if stripped.startswith("# ") and not current and not paragraphs:
            continue
        # Skip horizontal rules, badges, shields
        if stripped.startswith("---") or stripped.startswith("![") or stripped.startswith("[!["):
            continue
        if stripped == "":
            if current:
                paragraphs.append(" ".join(current)[:400])
                current = []
        else:
            # Strip leading markdown formatting (##, >, -, *)
            clean = re.sub(r"^[#>\-\*]+\s*", "", stripped)
            if clean:
                current.append(clean)

    if current:
        paragraphs.append(" ".join(current)[:400])

    return paragraphs


def _extract_first_paragraph(content: str, filename: str) -> str:
    """
    Return the first meaningful paragraph from a markdown/text doc.
    Wrapper around _extract_all_paragraphs — returns the first paragraph or "".
    """
    paragraphs = _extract_all_paragraphs(content, filename)
    return paragraphs[0] if paragraphs else ""


# ---------------------------------------------------------------------------
# File classifier
# ---------------------------------------------------------------------------

def _classify_file(fpath: Path, root: Path) -> dict | None:
    """
    Decide if a source file represents a user-facing surface.
    Returns a surface dict or None if not relevant.
    """
    name = fpath.stem  # filename without extension

    # Skip test/story files
    if re.search(r"(?i)(\.test|\.spec|\.stories?|\.mock)\.", fpath.name):
        return None
    # Skip utility / helper / hook / context / config files by convention
    if re.search(r"(?i)^(use[A-Z]|[a-z]+Context|[a-z]+Config|[a-z]+Types?|[a-z]+Utils?|"
                 r"[a-z]+Helpers?|[a-z]+Constants?|index)$", name):
        return None

    # PascalCase name suggests a React/Vue component
    is_pascal = bool(re.match(r"^[A-Z][A-Za-z0-9]+$", name))
    if not is_pascal:
        # Allow special names like "App", "index" at root level
        if name.lower() not in ("app", "main", "index", "root"):
            return None

    # Determine view context from parent directory path
    rel = fpath.relative_to(root)
    parts_lower = [p.lower() for p in rel.parts]

    is_page = bool(_PAGE_PATTERNS.search(name)) or any(
        p in ("pages", "views", "screens", "routes", "app") for p in parts_lower
    )
    is_component = bool(_COMPONENT_DIR_PATTERNS.search(str(rel))) or any(
        p in ("components", "widgets", "panels", "features", "modules") for p in parts_lower
    )

    if not (is_page or is_component or name.lower() in ("app", "main")):
        # Might still be a top-level component — include if PascalCase
        if not is_pascal:
            return None

    # Try to read a one-line purpose from the file
    purpose = _infer_purpose(fpath, name)

    # View context
    view = "page" if is_page else ("component" if is_component else "root")

    return {
        "name": name,
        "file": str(fpath.relative_to(root)).replace("\\", "/"),
        "purpose": purpose,
        "view": view,
    }


def _infer_purpose(fpath: Path, component_name: str) -> str:
    """
    Infer a short purpose string from the component name or a JSDoc comment.
    """
    try:
        content = fpath.read_text(encoding="utf-8", errors="ignore")
        # Look for a JSDoc or single-line comment near the top
        jsdoc = re.search(r"/\*\*?\s*\n?\s*\*?\s*([^\n*@{]+)", content)
        if jsdoc:
            return jsdoc.group(1).strip()[:120]
        # Fall back to splitting PascalCase into words
        return _pascal_to_words(component_name)
    except OSError:
        return _pascal_to_words(component_name)


def _pascal_to_words(name: str) -> str:
    """Convert PascalCase to space-separated words: 'NatalChartPanel' → 'Natal Chart Panel'."""
    words = re.sub(r"([A-Z][a-z]+)", r" \1", name).strip()
    return words


# ---------------------------------------------------------------------------
# Interactive surface counter
# ---------------------------------------------------------------------------

def _count_interactive(surfaces: list[dict], root: Path) -> int:
    """
    Count surfaces that contain at least one interactive element.
    A surface is "interactive" if its source file has a button, input, select,
    or a named interactive component.
    """
    count = 0
    for surface in surfaces:
        fpath = root / surface["file"].replace("/", os.sep)
        if not fpath.exists():
            # Still count it — surface exists, we just can't read it
            count += 1
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            if _RE_INTERACTIVE.search(content):
                count += 1
            elif _is_likely_interactive_by_name(surface["name"]):
                count += 1
        except OSError:
            count += 1

    return count


def _is_likely_interactive_by_name(name: str) -> bool:
    """
    Fallback: infer interactivity from the component name alone.
    """
    keywords = {
        "panel", "modal", "drawer", "form", "input", "button", "menu",
        "dropdown", "tab", "widget", "card", "table", "list", "sidebar",
        "nav", "header", "footer", "dashboard", "calendar", "chart",
        "action", "toggle", "switch", "slider",
    }
    name_lower = name.lower()
    return any(kw in name_lower for kw in keywords)


# ---------------------------------------------------------------------------
# Source file collector (shared pattern)
# ---------------------------------------------------------------------------

def _collect_source_files(root: Path) -> list[Path]:
    """Recursively collect source files, skipping noise directories."""
    results: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix in _SOURCE_EXTENSIONS:
                results.append(fpath)
    return results
