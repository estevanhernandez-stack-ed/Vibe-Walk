"""
anchor_drift.py — detect drift between emitted spotlightSteps.ts and host source data-tour anchors.

Pure function. Read-only (no writes; never auto-fixes).

detect(host_app_path: Path, tour_dir: Path | None = None,
       source_root: Path | None = None) -> dict
  Returns a structured drift report.

Why this exists
---------------
Vibe-Walk's source-injected `data-tour` anchors avoid the runtime-DOM
fragility class that competing runtime tools fight with patch tools
(e.g., Chameleon's Ranger). But anchors CAN still drift between emit and
deploy if a host renames a component, removes the attribute, or refactors
a section after the tour was generated. This check surfaces those drifts
at build time. Vendors structurally cannot ship this check because they
have no build-time codemod and no emitted tour module to diff against.

Drift types
-----------
- **missing**: anchor X is referenced in `spotlightSteps.ts` (`[data-tour="X"]`)
  but no `data-tour="X"` occurrence exists in the host source. The tour
  step will fail to highlight any element at runtime.
- **orphan**: `data-tour="Y"` exists in host source, but no step in
  `spotlightSteps.ts` references it. Either the step was removed without
  cleaning the source attribute, or the attribute was added without
  wiring a step.

"renamed" is intentionally NOT detected in v1 — heuristic matching is
easy to get wrong, and the missing/orphan pair already surfaces the
information the builder needs to make the call.

Return shape
------------
{
    "status":         "clean" | "drift" | "no-tour" | "no-source",
    "tour_dir":       str | None,        # absolute path
    "steps_file":     str | None,        # absolute path to spotlightSteps.ts
    "steps_anchors":  list[str],         # anchors found in spotlightSteps.ts
    "source_anchors": list[dict],        # [{anchor, file, line}, ...]
    "missing":        list[str],         # in steps_anchors but not in source
    "orphan":         list[dict],        # in source but not in steps; same shape
    "drift_count":    int,               # len(missing) + len(orphan)
    "last_emit":      str | None,        # ISO timestamp of spotlightSteps.ts mtime
    "scanned_files":  int,               # number of source files scanned
}
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Source extensions worth scanning for data-tour attributes
_SOURCE_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}

# Directories to skip during the source walk
_SKIP_DIRS = {
    "node_modules", ".git", ".next", ".vibe-walk", ".vibe-iterate",
    "dist", "build", "out", "__pycache__", ".cache", ".turbo",
}

# spotlightSteps.ts is emitted by emit_tour_module — match the file by name
_STEPS_FILE_CANDIDATES = ("spotlightSteps.ts", "spotlightSteps.tsx")

# Common locations the emitter may have written the tour dir
_TOUR_DIR_CANDIDATES = (
    Path("src") / "components" / "tour",
    Path("src") / "tour",
    Path("tour"),
    Path("components") / "tour",
)

# Regex to extract anchors from spotlightSteps.ts element selectors.
# Matches: element: '[data-tour="<anchor>"]' OR element: "[data-tour='<anchor>']"
# Accepts both quote styles for both the JS literal and the selector.
_STEPS_ANCHOR_RE = re.compile(
    r"""\[data-tour=(['"])([^'"]+)\1\]""",
)

# Regex for data-tour attributes in host source (JSX/HTML).
# Matches: data-tour="<anchor>" OR data-tour='<anchor>'.
# Does NOT match data-tour={expr} — dynamic anchors are out of scope for v1.
# Negative lookbehind on `[` excludes selector syntax like `[data-tour="x"]`
# (which appears in spotlightSteps.ts) so we never count the emitted tour
# module's own selectors as source occurrences.
_SOURCE_ANCHOR_RE = re.compile(
    r"""(?<!\[)data-tour=(['"])([^'"]+)\1""",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect(
    host_app_path: Path,
    tour_dir: Optional[Path] = None,
    source_root: Optional[Path] = None,
) -> dict:
    """
    Detect anchor drift between the emitted spotlightSteps.ts and the host source.

    Parameters
    ----------
    host_app_path : Path
        Absolute path to the host application's root directory.
    tour_dir : Path, optional
        Absolute path to the directory containing spotlightSteps.ts.
        If None, auto-locate via _TOUR_DIR_CANDIDATES under host_app_path.
    source_root : Path, optional
        Absolute path to the host source directory to scan for data-tour
        attributes. If None, defaults to host_app_path/src (or host_app_path
        if src/ doesn't exist).

    Returns
    -------
    dict
        Structured drift report per the module docstring.
    """
    host_app_path = Path(host_app_path)

    # ---- locate tour_dir + steps file -----------------------------------
    resolved_tour_dir = tour_dir or _find_tour_dir(host_app_path)
    steps_file: Optional[Path] = (
        _find_steps_file(resolved_tour_dir) if resolved_tour_dir else None
    )

    if steps_file is None or not steps_file.is_file():
        return {
            "status":         "no-tour",
            "tour_dir":       str(resolved_tour_dir) if resolved_tour_dir else None,
            "steps_file":     None,
            "steps_anchors":  [],
            "source_anchors": [],
            "missing":        [],
            "orphan":         [],
            "drift_count":    0,
            "last_emit":      None,
            "scanned_files":  0,
        }

    steps_anchors = _extract_steps_anchors(steps_file.read_text(encoding="utf-8"))
    last_emit = _iso_mtime(steps_file)

    # ---- scan host source -----------------------------------------------
    # Exclude the tour directory itself from the source scan — those files
    # are vibe-walk artifacts, not host source. (The regex negative-lookbehind
    # already blocks selector-style matches, but skipping the directory entirely
    # also keeps scanned_files honest and prevents future-file scans from
    # snagging on emitted artifacts.)
    resolved_source_root = source_root or _default_source_root(host_app_path)
    source_anchors, scanned_files = _scan_source_anchors(
        resolved_source_root, skip_dir=resolved_tour_dir
    )

    if scanned_files == 0:
        # No source to compare against — treat as no-source so callers can
        # render an informative skip instead of a misleading "everything is
        # missing" drift report.
        return {
            "status":         "no-source",
            "tour_dir":       str(resolved_tour_dir),
            "steps_file":     str(steps_file),
            "steps_anchors":  steps_anchors,
            "source_anchors": [],
            "missing":        [],
            "orphan":         [],
            "drift_count":    0,
            "last_emit":      last_emit,
            "scanned_files":  0,
        }

    # ---- diff ------------------------------------------------------------
    source_anchor_set = {entry["anchor"] for entry in source_anchors}
    steps_anchor_set = set(steps_anchors)

    missing = sorted(a for a in steps_anchor_set if a not in source_anchor_set)
    orphan = sorted(
        (entry for entry in source_anchors if entry["anchor"] not in steps_anchor_set),
        key=lambda e: (e["anchor"], e["file"], e["line"]),
    )
    drift_count = len(missing) + len(orphan)

    return {
        "status":         "drift" if drift_count > 0 else "clean",
        "tour_dir":       str(resolved_tour_dir),
        "steps_file":     str(steps_file),
        "steps_anchors":  sorted(steps_anchors),
        "source_anchors": source_anchors,
        "missing":        missing,
        "orphan":         orphan,
        "drift_count":    drift_count,
        "last_emit":      last_emit,
        "scanned_files":  scanned_files,
    }


# ---------------------------------------------------------------------------
# Helpers — anchor extraction
# ---------------------------------------------------------------------------

def _extract_steps_anchors(content: str) -> list[str]:
    """
    Pull anchors out of a spotlightSteps.ts file by matching
    `[data-tour="<anchor>"]` selectors. Returns anchors in the order they
    appear; duplicates are kept (a step file should not duplicate anchors,
    and the caller's diff turns the list into a set anyway).
    """
    return [match.group(2) for match in _STEPS_ANCHOR_RE.finditer(content)]


def _scan_source_anchors(
    source_root: Path, skip_dir: Optional[Path] = None
) -> tuple[list[dict], int]:
    """
    Walk source_root for files with a source extension and collect every
    occurrence of `data-tour="<anchor>"`. Returns (entries, files_scanned).

    Each entry: {"anchor": str, "file": str, "line": int}.
    File paths are relative to source_root for readable reports.

    Skips _SKIP_DIRS at any depth (so a nested node_modules doesn't sneak in)
    and any path under `skip_dir` (used to exclude the emitted tour dir).
    """
    entries: list[dict] = []
    files_scanned = 0

    if not source_root.is_dir():
        return entries, files_scanned

    skip_dir_resolved = skip_dir.resolve() if skip_dir else None

    for path in _walk_source_files(source_root):
        # Skip files under the explicit skip_dir (typically the tour dir)
        if skip_dir_resolved is not None:
            try:
                path.resolve().relative_to(skip_dir_resolved)
                continue  # path IS under skip_dir
            except ValueError:
                pass  # not under skip_dir → keep scanning
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in _SOURCE_ANCHOR_RE.finditer(text):
            anchor = match.group(2)
            line = text.count("\n", 0, match.start()) + 1
            rel = path.relative_to(source_root).as_posix()
            entries.append({"anchor": anchor, "file": rel, "line": line})

    return entries, files_scanned


def _walk_source_files(root: Path):
    """Yield every source file under root, skipping _SKIP_DIRS at any depth."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in _SOURCE_EXTENSIONS:
            continue
        # Skip if any path part matches _SKIP_DIRS
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        yield path


# ---------------------------------------------------------------------------
# Helpers — path resolution
# ---------------------------------------------------------------------------

def _find_tour_dir(host_app_path: Path) -> Optional[Path]:
    """
    Locate the tour directory inside the host app.
    Tries _TOUR_DIR_CANDIDATES in order; returns the first that exists.
    """
    for candidate in _TOUR_DIR_CANDIDATES:
        full = host_app_path / candidate
        if full.is_dir():
            return full
    return None


def _find_steps_file(tour_dir: Path) -> Optional[Path]:
    """
    Locate spotlightSteps.ts (or .tsx) inside tour_dir.
    Returns the first candidate that exists as a file.
    """
    if not tour_dir or not tour_dir.is_dir():
        return None
    for name in _STEPS_FILE_CANDIDATES:
        candidate = tour_dir / name
        if candidate.is_file():
            return candidate
    return None


def _default_source_root(host_app_path: Path) -> Path:
    """
    Pick a sensible source root to scan. Most apps live under src/; fall
    back to host_app_path itself if no src/ directory exists.
    """
    src = host_app_path / "src"
    return src if src.is_dir() else host_app_path


def _iso_mtime(path: Path) -> Optional[str]:
    """Return the file's mtime as an ISO-8601 UTC string, or None on failure."""
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
    except OSError:
        return None
