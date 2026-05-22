"""
emit_tour_module.py — Phase 2 tour generator: Driver.js drop-in module emitter.

Pure function. No I/O. No side effects.

emit_module(build_plan: dict) -> dict
  Returns {"files": {"<relpath>": "<contents>", ...}, "warnings": [...]}

Emits two TypeScript files for the Driver.js / Shape A (drop-in module) path:

  spotlightSteps.ts
    A DriveStep[] array. Each entry uses a data-tour="<anchor>" selector (D4).
    Aha-moment surface always appears first (step 1). Copy is benefit-led,
    ≤25 words per description, register matched to the build-plan audience.

  spotlightTour.ts
    The driver({...}) runner. Wires:
      - popoverClass (derived from app name)
      - showProgress: true (progress indicator, +12% completion, cheap to ship)
      - showButtons: ['next', 'previous', 'close']
      - onDestroyed → onDone callback
      - startSpotlightTour(onDone?) export (primary call surface)
      - replaySpotlightTour export (persistent, ungated replay entry point)
      - SSR guard (typeof window check — driver.js is browser-only)

Decision constraints honored:
  D1 — Hard cap at 5 steps. If build-plan has >5 stops, emit only the top 5
        (by rank) and add a warnings entry recommending a split tour.
  D2 — Drop-in module (Shape A) only. Config-only (Shape B) is not emitted here.
  D3 — Driver.js substrate.
  D4 — data-tour="<kebab-semantic-name>" selectors; no class selectors.

Reference target: Celestia3 spotlightSteps.ts + spotlightTour.ts
(feat/spotlight-tour branch — the calibre to match).

Source: docs/inputs/research/_seed.md §2 (D1–D4), §3 Phase 2, §4 GENERATE list.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STEP_CAP = 5

# Audience registers: copy style hints
_AUDIENCE_REGISTERS = {
    "b2c": "warm",
    "b2b": "authoritative-roi",
    "technical": "sparse",
    "domain_expert": "sparse",
    "power_user": "sparse",
}

# Driver.js popover sides/aligns for layout variety
_SIDE_CYCLE = ["right", "bottom", "bottom", "top", "left"]
_ALIGN_CYCLE = ["start", "start", "center", "center", "end"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def emit_module(build_plan: dict) -> dict:
    """
    Emit a Driver.js drop-in tour module from a resolved build-plan.

    Parameters
    ----------
    build_plan : dict
        The fully resolved .vibe-walk/build-plan.json (as a Python dict).
        Required keys: substrate, ranked_shortlist, aha_moment, audience,
        app_path, anchor_attr.

    Returns
    -------
    dict:
        "files"    — dict of {relative_path: file_contents}
        "warnings" — list of warning strings (empty when clean)
    """
    warnings: list[str] = []

    # Extract the stop list, sorted by rank (ascending = highest priority first)
    stops: list[dict] = _sorted_stops(build_plan)
    aha_surface: str = build_plan.get("aha_moment", {}).get("surface", "")

    # Context-dependent stop ordering (cowpath-earned rule):
    #   <= 3 stops: aha-first (emotional payoff immediate — short tours benefit from it)
    #   4-5 stops:  orientation-first → aha near the END (earned-payoff arc)
    # This matches the Celestia3 cowpath decision: sidebar nav first → natal chart last.
    # The 3-stop boundary is where "aha-first feels disjointed" starts to bite.
    stops = _order_stops_contextually(stops, aha_surface)

    # D1 — hard cap at 5 steps
    if len(stops) > _STEP_CAP:
        over_count = len(stops) - _STEP_CAP
        warnings.append(
            f"D1 step cap: build-plan has {len(stops)} stops — emitting the top "
            f"{_STEP_CAP} only. {over_count} stop(s) trimmed. "
            f"Recommend splitting into a first-run tour (aha moment + core surfaces) "
            f"+ a separate feature-discovery tour for advanced surfaces."
        )
        stops = stops[:_STEP_CAP]

    # Derive app-slug for naming (popoverClass, file name prefix)
    app_slug = _derive_app_slug(build_plan.get("app_path", "my-app"))
    audience = build_plan.get("audience", "b2c")

    # Emit the two files
    steps_content = _emit_steps_file(stops, audience, app_slug)
    runner_content = _emit_runner_file(app_slug, stops)

    return {
        "files": {
            "spotlightSteps.ts": steps_content,
            "spotlightTour.ts": runner_content,
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Steps file emitter
# ---------------------------------------------------------------------------

def _emit_steps_file(stops: list[dict], audience: str, app_slug: str) -> str:
    """
    Emit the spotlightSteps.ts file: a DriveStep[] array.

    Each stop entry has:
      element: '[data-tour="<anchor>"]'
      popover: { title, description, side, align }

    Copy is benefit-led, ≤25 words per description, register matched to audience.
    """
    register = _AUDIENCE_REGISTERS.get(audience, "warm")
    lines: list[str] = [
        "// spotlightSteps.ts",
        "// Generated by vibe-walk emit_tour_module — edit freely.",
        "import type { DriveStep } from 'driver.js';",
        "",
        f"export const SPOTLIGHT_STEPS: DriveStep[] = [",
    ]

    for i, stop in enumerate(stops):
        anchor = stop.get("anchor") or stop.get("name", f"stop-{i}")
        name = stop.get("name", anchor)
        purpose = stop.get("purpose", "")
        side = _SIDE_CYCLE[i % len(_SIDE_CYCLE)]
        align = _ALIGN_CYCLE[i % len(_ALIGN_CYCLE)]

        title = _generate_title(name, purpose, register, i)
        description = _generate_description(name, purpose, register, i)

        # Escape any single quotes in the generated strings
        title = title.replace("'", "\\'")
        description = description.replace("'", "\\'")

        lines.append("  {")
        lines.append(f"    element: '[data-tour=\"{anchor}\"]',")
        lines.append("    popover: {")
        lines.append(f"      title: '{title}',")
        lines.append(f"      description: '{description}',")
        lines.append(f"      side: '{side}',")
        lines.append(f"      align: '{align}',")
        lines.append("    },")
        lines.append("  },")

    lines.append("];")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Runner file emitter
# ---------------------------------------------------------------------------

def _emit_runner_file(app_slug: str, stops: list[dict]) -> str:
    """
    Emit the spotlightTour.ts runner file.

    Matches the Celestia3 calibre:
      - import driver from driver.js
      - driver({showProgress, showButtons, popoverClass, steps, onDestroyed}) .drive()
      - startSpotlightTour(onDone?) export — the primary call surface
      - replaySpotlightTour export — persistent, ungated replay entry point
      - SSR guard (typeof window check) — driver.js is browser-only
    """
    popover_class = f"{app_slug}-spotlight"
    step_count = len(stops)

    content = f"""\
// spotlightTour.ts
// Generated by vibe-walk emit_tour_module — edit freely.
// SSR guard: driver.js is browser-only; this module is client-side only.
// Do NOT import server-side (Next.js: use dynamic import with ssr: false,
// or call only inside useEffect / onClick handlers).
import {{ driver }} from 'driver.js';
import 'driver.js/dist/driver.css';
import {{ SPOTLIGHT_STEPS }} from './spotlightSteps';

/**
 * Starts the spotlight tour. `onDone` runs once when the tour is destroyed —
 * covers finishing the last step, the close button, and ESC.
 *
 * Replay entry point: call this function at any time (from a help menu,
 * a "Take the Tour" button, etc.) — it is persistent and ungated.
 *
 * SSR: always call this inside a browser context (useEffect, onClick, etc.).
 * typeof window guard is enforced below.
 */
export function startSpotlightTour(onDone?: () => void): void {{
  // SSR guard — driver.js requires a browser DOM; bail out on SSR/SSG renders.
  if (typeof window === 'undefined') return;

  const tour = driver({{
    showProgress: true,
    showButtons: ['next', 'previous', 'close'],
    popoverClass: '{popover_class}',
    steps: SPOTLIGHT_STEPS,
    onDestroyed: () => {{
      onDone?.();
    }},
  }});
  tour.drive();
}}

/**
 * Replay export — persistent, ungated. Wire to any "Take the Tour" / help
 * surface. No first-run gate; fires any time the user wants a replay.
 * Alias of startSpotlightTour with no onDone callback.
 */
export const replaySpotlightTour = (): void => startSpotlightTour();
"""
    return content


# ---------------------------------------------------------------------------
# Copy generation helpers
# ---------------------------------------------------------------------------

def _generate_title(name: str, purpose: str, register: str, index: int) -> str:
    """
    Generate a short, benefit-led title for a tour step.
    Derived from the surface name + purpose.
    Titles are proper nouns, ≤8 words.
    """
    # Clean up the name (kebab-case → words)
    words = name.replace("-", " ").replace("_", " ")
    words = re.sub(r"\s+", " ", words).strip()

    # Capitalise first word
    if words:
        words = words[0].upper() + words[1:]

    # Register-specific framing
    if register == "authoritative-roi":
        if purpose:
            # B2B: lead with the capability
            title = _truncate_words(purpose, 6) or words
        else:
            title = words
    elif register == "sparse":
        # Technical: name only, no editorialising
        title = words
    else:
        # B2C warm: add a touch of personality
        title = words

    return _truncate_words(title, 8)


def _generate_description(name: str, purpose: str, register: str, index: int) -> str:
    """
    Generate a benefit-led description ≤25 words.
    Derived from the surface purpose; padded with register-appropriate framing.
    Hard-enforced: truncated to 25 words before return.
    """
    if purpose and len(purpose.strip()) > 0:
        base = purpose.strip()
    else:
        # Fallback: derive from name
        words = name.replace("-", " ").replace("_", " ").strip()
        base = words[0].upper() + words[1:] if words else name

    # Register-specific suffix framing
    if register == "authoritative-roi":
        # B2B: ROI-oriented, authoritative
        desc = _make_benefit_led(base, "Saves setup time and keeps your team aligned.")
    elif register == "sparse":
        # Technical: just the fact, no editorialising
        desc = base
    else:
        # B2C warm: friendly, action-oriented
        desc = _make_benefit_led(base, "Your starting point.")

    # HARD CAP: ≤25 words (D1-honest / GENERATE constraint)
    return _truncate_words(desc, 25)


def _make_benefit_led(base: str, fallback_suffix: str) -> str:
    """
    Ensure description is benefit-led. If it already starts with a verb or
    benefit framing, leave it. Otherwise, use it as-is (it came from purpose
    which should already be descriptive).
    """
    # Strip trailing period
    text = base.rstrip(".")
    # If it's very short (≤4 words), append the register-appropriate hint
    if len(text.split()) <= 4:
        return f"{text} — {fallback_suffix}"
    return text


def _truncate_words(text: str, max_words: int) -> str:
    """Truncate text to at most max_words words, stripping trailing punctuation."""
    words = text.split()
    if len(words) <= max_words:
        return text
    truncated = " ".join(words[:max_words])
    # Clean trailing partial punctuation
    truncated = truncated.rstrip(",;:")
    return truncated


# ---------------------------------------------------------------------------
# Build-plan helpers
# ---------------------------------------------------------------------------

def _sorted_stops(build_plan: dict) -> list[dict]:
    """
    Return the ranked_shortlist sorted by 'rank' (ascending = highest priority).
    Stops without a rank key sort to the end.
    """
    shortlist = build_plan.get("ranked_shortlist", [])
    return sorted(shortlist, key=lambda s: s.get("rank", 9999))


def _order_stops_contextually(stops: list[dict], aha_surface: str) -> list[dict]:
    """
    Context-dependent stop ordering (cowpath-earned rule):

    <= 3 stops: aha-first
        The aha-moment stop is moved to position 0. Short tours benefit from
        immediate emotional payoff — there isn't enough context to build to it.

    4+ stops: orientation-first → aha near the END (earned-payoff arc)
        The aha-moment stop is moved to the second-to-last position. The tour
        starts with orientation stops (sidebar, shell, feed) and builds toward
        the emotional payoff. This matches the Celestia3 cowpath design:
        sidebar nav first → natal chart last.

    If aha_surface is not found in stops, return stops unchanged.
    """
    if not aha_surface:
        return stops

    aha_idx = None
    for i, stop in enumerate(stops):
        if stop.get("name") == aha_surface or stop.get("anchor") == aha_surface:
            aha_idx = i
            break

    if aha_idx is None:
        return stops  # aha stop not in list — no reorder

    n = len(stops)

    if n <= 3:
        # Aha-first: move aha to position 0
        if aha_idx == 0:
            return stops  # already first
        reordered = [stops[aha_idx]] + stops[:aha_idx] + stops[aha_idx + 1:]
        return reordered
    else:
        # Orientation-first: move aha to second-to-last position (n-2)
        # "Near the end" but not the very last stop — last stop is typically
        # an escape hatch (AI chat, replay button, etc.).
        # If there's only 1 non-aha stop after the proposed position, place aha last.
        target_pos = max(n - 2, 1)  # at least position 1, at most n-2
        if aha_idx == target_pos:
            return stops  # already in position
        # Remove aha from current position and insert at target
        remaining = stops[:aha_idx] + stops[aha_idx + 1:]
        reordered = remaining[:target_pos] + [stops[aha_idx]] + remaining[target_pos:]
        return reordered


def _reorder_aha_first(stops: list[dict], aha_surface: str) -> list[dict]:
    """
    Legacy wrapper — preserved for any external callers that imported this directly.
    Delegates to _order_stops_contextually.
    """
    return _order_stops_contextually(stops, aha_surface)


def _derive_app_slug(app_path: str) -> str:
    """
    Derive a kebab-case app slug from the app_path for use in class names.
    '/projects/my-cool-app' → 'my-cool-app'
    '/Users/estev/Projects/Celestia3' → 'celestia3'
    """
    name = Path(app_path).name if app_path else "app"
    # Lower-case + kebab
    slug = name.lower()
    # Replace non-alphanumeric (except hyphens) with hyphens
    slug = re.sub(r"[^a-z0-9\-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "app"
