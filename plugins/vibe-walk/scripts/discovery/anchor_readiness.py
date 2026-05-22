"""
anchor_readiness.py — Phase 1: selector scan → anchor-readiness verdict + risk flags.

assess(repo_path: str) -> dict

Scans the repo for stable selectors (id= and data-* attributes in JSX/TSX/HTML/JS/TS
source files) and detects risk patterns that affect the anchor-injection pass.

Returns
-------
dict with keys:
    readiness : str  — "ready" | "needs-pass" | "none"
    risk_flags : list[str]  — detected risk signals

Readiness levels
-----------------
  ready       — stable selectors (id= or data-tour/data-*) present on the majority
                of interactive components; anchor injection should be straightforward.
  needs-pass  — some stable selectors present but coverage is sparse; an anchor pass
                is needed before the tour can be built.
  none        — no stable selectors found anywhere; the host must accept a full anchor
                pass or the tour cannot be built.

Risk flags
----------
  no_stable_selectors   — no id= or data-* attrs found in any source file
  tailwind_only         — only Tailwind utility class names detected (className=) with
                          no stable ids; high rotation risk
  css_modules           — *.module.css / *.module.scss files found → hashed class names
                          at build time; class-name anchoring forbidden
  shadow_dom            — attachShadow() call detected → any stop inside the shadow
                          boundary is untourable
  cross_origin_iframe   — <iframe src="https://..."> pointing outside the repo →
                          stops inside cannot be targeted
  dynamic_mount         — dynamic import() or React.lazy() detected → element may not
                          be mounted when the tour step fires
  ssr_risk              — Next.js or Remix detected → SSR guard required in emitted module
  path_not_found        — repo_path does not exist
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Source file globs to scan
# ---------------------------------------------------------------------------
_SOURCE_EXTENSIONS = {".tsx", ".ts", ".jsx", ".js", ".html", ".vue", ".svelte"}

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Stable selector: id= or data-anything= in JSX/HTML
# Matches: id="foo"  id={'foo'}  data-tour="foo"  data-testid="bar"
_RE_STABLE_ID = re.compile(r'\bid\s*=\s*["{\'`]')
_RE_DATA_ATTR = re.compile(r'\bdata-[a-z][a-z0-9\-]*\s*=\s*["{\'`]')

# Tailwind: className= present (not definitive alone — need absence of stable selectors)
_RE_CLASSNAME = re.compile(r'\bclassName\s*=\s*["{\'`]')

# CSS Modules import
_RE_CSS_MODULE_FILE = re.compile(r'\.(module)\.(css|scss|sass|less)$')

# Shadow DOM
_RE_SHADOW_DOM = re.compile(r'\.attachShadow\s*\(')

# Cross-origin iframe
_RE_CROSS_ORIGIN_IFRAME = re.compile(r'<iframe\b[^>]*\bsrc\s*=\s*["\']https?://')

# Dynamic import / React.lazy
_RE_DYNAMIC_IMPORT = re.compile(r'\bimport\s*\(|React\.lazy\s*\(')

# SSR frameworks
_RE_NEXT_JS = re.compile(r'["\']next["\']|next\.config\.(js|mjs|ts)')
_RE_REMIX = re.compile(r'["\']@remix-run|remix\.config\.')


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def assess(repo_path: str) -> dict:
    """
    Scan repo_path for anchor-readiness signals and return verdict + risk flags.

    Parameters
    ----------
    repo_path : str
        Absolute path to the root of the target repository.

    Returns
    -------
    dict with "readiness" and "risk_flags" keys.
    """
    path = Path(repo_path)

    if not path.exists():
        return {"readiness": "none", "risk_flags": ["path_not_found"]}

    # Collect source files (skip node_modules, .git, __pycache__, dist, build)
    source_files = _collect_source_files(path)
    all_files = list(path.rglob("*"))

    risk_flags: list[str] = []

    # ------------------------------------------------------------------
    # Stable selector counts
    # ------------------------------------------------------------------
    files_with_stable: int = 0
    files_without_stable: int = 0
    classname_only_files: int = 0  # has className= but no id= / data-*
    total_stable_attrs: int = 0

    for f in source_files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        has_id = bool(_RE_STABLE_ID.search(content))
        has_data = bool(_RE_DATA_ATTR.search(content))
        has_classname = bool(_RE_CLASSNAME.search(content))
        stable = has_id or has_data

        if stable:
            files_with_stable += 1
            total_stable_attrs += len(_RE_STABLE_ID.findall(content)) + len(
                _RE_DATA_ATTR.findall(content)
            )
        else:
            files_without_stable += 1
            if has_classname:
                classname_only_files += 1

        # Shadow DOM
        if _RE_SHADOW_DOM.search(content):
            if "shadow_dom" not in risk_flags:
                risk_flags.append("shadow_dom")

        # Cross-origin iframe
        if _RE_CROSS_ORIGIN_IFRAME.search(content):
            if "cross_origin_iframe" not in risk_flags:
                risk_flags.append("cross_origin_iframe")

        # Dynamic imports
        if _RE_DYNAMIC_IMPORT.search(content):
            if "dynamic_mount" not in risk_flags:
                risk_flags.append("dynamic_mount")

    # ------------------------------------------------------------------
    # CSS Modules detection
    # ------------------------------------------------------------------
    css_module_files = [
        f for f in all_files if _RE_CSS_MODULE_FILE.search(f.name)
    ]
    if css_module_files:
        risk_flags.append("css_modules")

    # ------------------------------------------------------------------
    # SSR framework detection (package.json / config files)
    # ------------------------------------------------------------------
    pkg_json = path / "package.json"
    next_config = list(path.glob("next.config.*"))
    remix_config = list(path.glob("remix.config.*"))

    ssr_signal = False
    if pkg_json.exists():
        try:
            pkg_content = pkg_json.read_text(encoding="utf-8", errors="ignore")
            if _RE_NEXT_JS.search(pkg_content) or _RE_REMIX.search(pkg_content):
                ssr_signal = True
        except OSError:
            pass
    if next_config or remix_config:
        ssr_signal = True
    if ssr_signal:
        risk_flags.append("ssr_risk")

    # ------------------------------------------------------------------
    # Tailwind-only detection
    # tailwind_only = classname_only_files dominate AND no stable selectors overall
    # ------------------------------------------------------------------
    total_component_files = files_with_stable + files_without_stable
    if total_component_files > 0:
        tailwind_fraction = classname_only_files / total_component_files
        if tailwind_fraction > 0.5 and files_with_stable == 0:
            risk_flags.append("tailwind_only")

    # ------------------------------------------------------------------
    # Readiness verdict
    # ------------------------------------------------------------------
    if files_with_stable == 0:
        risk_flags.append("no_stable_selectors")
        readiness = "none"
    else:
        # Coverage ratio: what fraction of component files have stable selectors?
        if total_component_files > 0:
            coverage = files_with_stable / total_component_files
        else:
            coverage = 1.0

        if coverage >= 0.6:
            readiness = "ready"
        else:
            readiness = "needs-pass"

    return {
        "readiness": readiness,
        "risk_flags": risk_flags,
        # Extra context for callers (not part of the public contract but useful)
        "_meta": {
            "files_with_stable": files_with_stable,
            "files_without_stable": files_without_stable,
            "total_stable_attrs": total_stable_attrs,
            "source_files_scanned": total_component_files,
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "dist", "build", ".next",
    "coverage", ".turbo", "out", ".cache", "vendor", "venv", ".venv",
}


def _collect_source_files(root: Path) -> list[Path]:
    """Recursively collect source files, skipping noise directories."""
    results: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place so os.walk doesn't descend into them
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix in _SOURCE_EXTENSIONS:
                results.append(fpath)
    return results
