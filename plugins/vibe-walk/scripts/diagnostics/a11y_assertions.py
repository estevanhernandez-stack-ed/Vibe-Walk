"""
a11y_assertions.py — keyboard/AT contract assertions over the emitted tour.

Pure function. Read-only (no writes; never auto-fixes).

check(host_app_path: Path, tour_dir: Path | None = None) -> dict
  Returns a structured assertion report.

Why this exists
---------------
The emitted spotlight tour runs in front of brand-new users — the
highest-stakes accessibility surface a host app has. The emitter ships a
keyboard/AT contract by construction (ESC + close button intact, keyboard
control enabled, focus handed back on destroy, per-step popover copy), but
hosts edit emitted files, and an edit that sets `allowClose: false` or strips
the close button quietly strands keyboard and screen-reader users with no
visible breakage for mouse users. These assertions make the contract
mechanically checkable at emit time and at any later `/vibe-walk:vitals` run.

Mechanical by design: prose-only enforcement rots (the family's GAP-02
lesson — a sibling plugin's prose enforcer sat dead for six releases).
This module is the script the SKILL prose defers to.

Assertions
----------
fail-level (the emitted tour is keyboard-inaccessible for someone):
- keyboard-control-disabled  `allowKeyboardControl: false` in the tour module.
- escape-hatch-removed       `allowClose: false` — ESC / close dismissal gone.
- close-button-removed       `showButtons` present but missing 'close'.

warn-level (degraded, not broken):
- nav-buttons-missing        `showButtons` present but missing 'next' or
                             'previous' — no pointer/AT alternative to arrows.
- focus-return-missing       no document.activeElement capture + .focus()
                             restore in the tour module (pre-v0.3 emissions,
                             or a host edit removed it).
- destroy-hook-missing       no `onDestroyed` — host has no hook to restore
                             focus or state when the tour closes.
- step-copy-missing          steps file has more `element:` entries than
                             `title:` / `description:` entries — steps
                             without popover copy give AT users no context.

Return shape
------------
{
    "status":      "pass" | "findings" | "no-tour",
    "tour_dir":    str | None,     # absolute path
    "tour_file":   str | None,     # absolute path to spotlightTour.ts
    "steps_file":  str | None,     # absolute path to spotlightSteps.ts
    "findings":    list[dict],     # [{id, severity, message}, ...]
    "fail_count":  int,
    "warn_count":  int,
    "checked":     list[str],      # assertion ids evaluated this run
}
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

# Tour-dir + steps-file location is shared with the drift check — one source
# of truth so the two diagnostics can never disagree about where a tour lives.
from diagnostics.anchor_drift import _find_steps_file, _find_tour_dir

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TOUR_FILE_CANDIDATES = ("spotlightTour.ts", "spotlightTour.tsx")

_SHOW_BUTTONS_RE = re.compile(r"showButtons\s*:\s*\[([^\]]*)\]")
_BUTTON_NAME_RE = re.compile(r"""['"](\w+)['"]""")

_KEYBOARD_DISABLED_RE = re.compile(r"allowKeyboardControl\s*:\s*false")
_ALLOW_CLOSE_FALSE_RE = re.compile(r"allowClose\s*:\s*false")
_ACTIVE_ELEMENT_RE = re.compile(r"document\.activeElement")
_FOCUS_CALL_RE = re.compile(r"\.focus\s*\(")
_ON_DESTROYED_RE = re.compile(r"onDestroyed\s*:")

_STEPS_ELEMENT_RE = re.compile(r"element\s*:")
_STEPS_TITLE_RE = re.compile(r"title\s*:")
_STEPS_DESCRIPTION_RE = re.compile(r"description\s*:")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check(host_app_path: Path, tour_dir: Optional[Path] = None) -> dict:
    """
    Run the a11y assertions against the host's emitted tour module.

    Parameters
    ----------
    host_app_path : Path
        Absolute path to the host application's root directory.
    tour_dir : Path, optional
        Absolute path to the directory containing the emitted tour files.
        If None, auto-locate via the same candidates the drift check uses.

    Returns
    -------
    dict
        Structured assertion report per the module docstring.
    """
    host_app_path = Path(host_app_path)
    resolved_tour_dir = tour_dir or _find_tour_dir(host_app_path)
    tour_file = _find_tour_file(resolved_tour_dir) if resolved_tour_dir else None

    if tour_file is None or not tour_file.is_file():
        return {
            "status":     "no-tour",
            "tour_dir":   str(resolved_tour_dir) if resolved_tour_dir else None,
            "tour_file":  None,
            "steps_file": None,
            "findings":   [],
            "fail_count": 0,
            "warn_count": 0,
            "checked":    [],
        }

    steps_file = _find_steps_file(resolved_tour_dir)
    tour_text = tour_file.read_text(encoding="utf-8")

    findings: list[dict] = []
    checked: list[str] = []

    findings.extend(_check_tour_module(tour_text, checked))
    if steps_file is not None and steps_file.is_file():
        steps_text = steps_file.read_text(encoding="utf-8")
        findings.extend(_check_steps_file(steps_text, checked))

    fail_count = sum(1 for f in findings if f["severity"] == "fail")
    warn_count = sum(1 for f in findings if f["severity"] == "warn")

    return {
        "status":     "findings" if findings else "pass",
        "tour_dir":   str(resolved_tour_dir),
        "tour_file":  str(tour_file),
        "steps_file": str(steps_file) if steps_file and steps_file.is_file() else None,
        "findings":   findings,
        "fail_count": fail_count,
        "warn_count": warn_count,
        "checked":    checked,
    }


# ---------------------------------------------------------------------------
# Assertions — tour module (spotlightTour.ts)
# ---------------------------------------------------------------------------

def _check_tour_module(tour_text: str, checked: list[str]) -> list[dict]:
    findings: list[dict] = []

    checked.append("keyboard-control-disabled")
    if _KEYBOARD_DISABLED_RE.search(tour_text):
        findings.append({
            "id":       "keyboard-control-disabled",
            "severity": "fail",
            "message":  "allowKeyboardControl: false — arrow/ESC keyboard "
                        "operation of the tour is disabled. Remove the option "
                        "(driver.js defaults keyboard control on).",
        })

    checked.append("escape-hatch-removed")
    if _ALLOW_CLOSE_FALSE_RE.search(tour_text):
        findings.append({
            "id":       "escape-hatch-removed",
            "severity": "fail",
            "message":  "allowClose: false — users cannot dismiss the tour "
                        "via ESC or overlay click. A tour with no escape "
                        "hatch traps keyboard users; remove the option.",
        })

    checked.append("close-button-removed")
    checked.append("nav-buttons-missing")
    show_buttons = _SHOW_BUTTONS_RE.search(tour_text)
    if show_buttons:
        buttons = set(_BUTTON_NAME_RE.findall(show_buttons.group(1)))
        if "close" not in buttons:
            findings.append({
                "id":       "close-button-removed",
                "severity": "fail",
                "message":  "showButtons omits 'close' — no visible, "
                            "focusable way to leave the tour. Add 'close' "
                            "back to the array.",
            })
        missing_nav = sorted({"next", "previous"} - buttons)
        if missing_nav:
            findings.append({
                "id":       "nav-buttons-missing",
                "severity": "warn",
                "message":  f"showButtons omits {', '.join(missing_nav)} — "
                            "keyboard arrows become the only navigation; "
                            "pointer and switch-access users lose theirs.",
            })

    checked.append("focus-return-missing")
    has_focus_return = (
        _ACTIVE_ELEMENT_RE.search(tour_text) and _FOCUS_CALL_RE.search(tour_text)
    )
    if not has_focus_return:
        findings.append({
            "id":       "focus-return-missing",
            "severity": "warn",
            "message":  "No document.activeElement capture + .focus() restore "
                        "— closing the tour strands focus on document.body. "
                        "Re-emit with the current emitter, or hand-add the "
                        "capture/restore pair around driver().",
        })

    checked.append("destroy-hook-missing")
    if not _ON_DESTROYED_RE.search(tour_text):
        findings.append({
            "id":       "destroy-hook-missing",
            "severity": "warn",
            "message":  "No onDestroyed hook — the host has no point to "
                        "restore focus or state when the tour closes.",
        })

    return findings


# ---------------------------------------------------------------------------
# Assertions — steps file (spotlightSteps.ts)
# ---------------------------------------------------------------------------

def _check_steps_file(steps_text: str, checked: list[str]) -> list[dict]:
    findings: list[dict] = []

    checked.append("step-copy-missing")
    element_count = len(_STEPS_ELEMENT_RE.findall(steps_text))
    title_count = len(_STEPS_TITLE_RE.findall(steps_text))
    description_count = len(_STEPS_DESCRIPTION_RE.findall(steps_text))
    if element_count > 0 and (
        title_count < element_count or description_count < element_count
    ):
        findings.append({
            "id":       "step-copy-missing",
            "severity": "warn",
            "message":  f"{element_count} step element(s) but only "
                        f"{title_count} title(s) / {description_count} "
                        "description(s) — steps without popover copy give "
                        "screen-reader users no context for the highlight.",
        })

    return findings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_tour_file(tour_dir: Optional[Path]) -> Optional[Path]:
    """Locate spotlightTour.ts (or .tsx) inside tour_dir."""
    if not tour_dir or not tour_dir.is_dir():
        return None
    for name in _TOUR_FILE_CANDIDATES:
        candidate = tour_dir / name
        if candidate.is_file():
            return candidate
    return None
