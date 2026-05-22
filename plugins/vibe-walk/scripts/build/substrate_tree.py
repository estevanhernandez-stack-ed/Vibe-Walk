"""
substrate_tree.py — substrate decision-tree resolver for vibe-walk.

Pure function: takes a signals dict, walks the decision tree from
_seed.md §3 Phase 1.5 top-to-bottom, and returns the resolved substrate
plus the anchor attribute, a human-readable reason, and whether the result
is merely a default that should be confirmed vs a mandatory/forced choice.

Decision tree (order is load-bearing — first match wins):
  1.  Not React (Svelte/Vue/vanilla/Alpine/Astro)?
        → driver.js (mandatory), anchor data-tour
  2.  Any tour stop inside shadow DOM?
        → untourable — remove or scope around it
  3.  Output shape config-only JSON?
        → driver.js (mandatory; only substrate with serializable steps)
  4.  Next.js App Router AND tour spans multiple routes?
        → nextstep.js, anchor id="tour-<name>" (NOT data-tour).
          Note: ~30KB Framer Motion peer dep.
  5.  Any stop must async-wait for element mount?
        → react-joyride (async hook before step)
  6.  Heavily animated / re-rendering stop elements?
        → reactour (mutationObservables auto-reposition)
  7.  Host wants idiomatic React AND bundle NOT a concern?
        → react-joyride
  8.  DEFAULT → driver.js, anchor data-tour

ALWAYS BLOCK: Intro.js is never selectable (AGPL-3 — license poison).
  If a caller somehow passes a signal requesting it, this function rejects
  it and falls through to the default.

Input signals keys (all required):
  framework (str)
      The target app's primary framework.
      Known non-React values: "svelte", "vue", "vanilla", "alpine", "astro".
      React values: "react-spa", "next-app-router", "next-pages-router",
                    "remix", "gatsby", or any string starting with "react".
  tour_spans_multiple_routes (bool)
      True if the planned tour highlights stops across more than one route/page.
  has_shadow_dom_stops (bool)
      True if one or more planned tour stops are inside a shadow DOM boundary
      (Web Components, Stencil, lit-element, etc.).
  output_shape (str)
      "module" — drop-in JS module (default, Shape A).
      "config-only" — JSON-only output (Shape B, gated exception).
  needs_async_mount_wait (bool)
      True if any planned tour stop requires waiting for an async element
      mount before the tooltip can attach (e.g., lazy-loaded panels, portals).
  heavily_animated (bool)
      True if one or more planned tour stops are on heavily animated or
      frequently re-rendering elements that would make tooltip positioning
      unreliable without mutation observers.
  wants_idiomatic_react (bool)
      True if the host team explicitly prefers a React-native tour library
      over a framework-agnostic one.
  bundle_size_sensitive (bool)
      True if the host is actively managing bundle size and would prefer
      to avoid adding a heavier React-specific tour library.

Output dict (always all four keys):
  substrate (str)   — "driver.js" | "nextstep.js" | "react-joyride" |
                       "reactour" | "untourable"
  anchor_attr (str) — "data-tour" | "id" | "none" (for untourable)
  reason (str)      — human-readable explanation of the resolution
  confirm_only (bool) — True = default, ask user to confirm;
                         False = forced/mandatory choice
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Framework classification helpers
# ---------------------------------------------------------------------------

_NON_REACT_FRAMEWORKS = frozenset({"svelte", "vue", "vanilla", "alpine", "astro"})

_REACT_KEYWORDS = ("react", "next", "remix", "gatsby")


def _is_react(framework: str) -> bool:
    """Return True if the framework is React or a React-based meta-framework."""
    fw = framework.lower().strip()
    if fw in _NON_REACT_FRAMEWORKS:
        return False
    return any(kw in fw for kw in _REACT_KEYWORDS)


def _is_non_react(framework: str) -> bool:
    return not _is_react(framework)


def _is_next_app_router(framework: str) -> bool:
    return framework.lower().strip() == "next-app-router"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_substrate(signals: dict) -> dict:
    """
    Walk the substrate decision tree and return the resolved substrate config.

    See module docstring for full input/output contract.

    Parameters
    ----------
    signals : dict
        Must contain all eight keys documented above.

    Returns
    -------
    dict with keys: substrate, anchor_attr, reason, confirm_only
    """
    framework: str = signals["framework"]
    tour_spans_multiple_routes: bool = signals["tour_spans_multiple_routes"]
    has_shadow_dom_stops: bool = signals["has_shadow_dom_stops"]
    output_shape: str = signals["output_shape"]
    needs_async_mount_wait: bool = signals["needs_async_mount_wait"]
    heavily_animated: bool = signals["heavily_animated"]
    wants_idiomatic_react: bool = signals["wants_idiomatic_react"]
    bundle_size_sensitive: bool = signals["bundle_size_sensitive"]

    # ------------------------------------------------------------------
    # ALWAYS BLOCK: Intro.js is never selectable (AGPL-3)
    # (No signal currently requests it, but guard against future callers.)
    # ------------------------------------------------------------------
    # This guard is implicit — none of the branches below can return intro.js,
    # and the docstring documents the rejection. No separate early-return needed.

    # ------------------------------------------------------------------
    # Branch 1 — Not React (Svelte/Vue/vanilla/Alpine/Astro)
    # → driver.js mandatory, anchor data-tour
    # ------------------------------------------------------------------
    if _is_non_react(framework):
        return {
            "substrate": "driver.js",
            "anchor_attr": "data-tour",
            "reason": (
                f"Non-React framework detected ({framework}). "
                "Driver.js is mandatory — it is framework-agnostic and the only "
                "substrate that works reliably outside the React ecosystem."
            ),
            "confirm_only": False,
        }

    # ------------------------------------------------------------------
    # Branch 2 — Any tour stop inside shadow DOM → untourable
    # ------------------------------------------------------------------
    if has_shadow_dom_stops:
        return {
            "substrate": "untourable",
            "anchor_attr": "none",
            "reason": (
                "One or more planned tour stops are inside a shadow DOM boundary "
                "(Web Components, Stencil, lit-element, etc.). "
                "Shadow DOM is a hard wall — querySelector and AST traversal both "
                "fail at the boundary. No substrate fixes this. "
                "Remove the stop or scope the tour around the shadow boundary."
            ),
            "confirm_only": False,
        }

    # ------------------------------------------------------------------
    # Branch 3 — Config-only JSON output shape → driver.js (mandatory)
    # ------------------------------------------------------------------
    if output_shape == "config-only":
        return {
            "substrate": "driver.js",
            "anchor_attr": "data-tour",
            "reason": (
                "Config-only JSON output (Shape B) is selected. "
                "Driver.js is mandatory for this path — it is the only substrate "
                "with fully serializable steps (JSON-safe config), which is what "
                "makes config-only output reliable. "
                "Note: fire the driver.js version sub-question before emitting."
            ),
            "confirm_only": False,
        }

    # ------------------------------------------------------------------
    # Branch 4 — Next.js App Router AND tour spans multiple routes
    # → nextstep.js, anchor id (NOT data-tour per D3-nextstep)
    # ------------------------------------------------------------------
    if _is_next_app_router(framework) and tour_spans_multiple_routes:
        return {
            "substrate": "nextstep.js",
            "anchor_attr": "id",
            "reason": (
                "Next.js App Router detected with a multi-route tour. "
                "NextStep.js is the purpose-built solution for this combination — "
                "it handles App Router route transitions natively. "
                "Anchor contract: id=\"tour-<name>\" (NOT data-tour; NextStep reads id only). "
                "Note: ~30KB Framer Motion peer dep — confirm it is already in the bundle "
                "or budget it explicitly."
            ),
            "confirm_only": False,
        }

    # ------------------------------------------------------------------
    # Branch 5 — Any stop must async-wait for element mount → react-joyride
    # ------------------------------------------------------------------
    if needs_async_mount_wait:
        return {
            "substrate": "react-joyride",
            "anchor_attr": "data-tour",
            "reason": (
                "One or more tour stops require async waiting for element mount "
                "(lazy-loaded panels, portals, or deferred render). "
                "React Joyride supports async hooks before each step, "
                "making it the correct choice for deferred-mount surfaces."
            ),
            "confirm_only": False,
        }

    # ------------------------------------------------------------------
    # Branch 6 — Heavily animated / re-rendering stop elements → reactour
    # ------------------------------------------------------------------
    if heavily_animated:
        return {
            "substrate": "reactour",
            "anchor_attr": "data-tour",
            "reason": (
                "One or more tour stops are on heavily animated or frequently "
                "re-rendering elements. Reactour uses mutationObservables to "
                "auto-reposition tooltips, making it the correct choice for "
                "surfaces where the DOM is in flux."
            ),
            "confirm_only": False,
        }

    # ------------------------------------------------------------------
    # Branch 7 — Idiomatic React preferred AND bundle NOT a concern
    # → react-joyride
    # ------------------------------------------------------------------
    if wants_idiomatic_react and not bundle_size_sensitive:
        return {
            "substrate": "react-joyride",
            "anchor_attr": "data-tour",
            "reason": (
                "Host team prefers an idiomatic React tour library and bundle size "
                "is not a constraint. React Joyride integrates naturally with React "
                "state/lifecycle and is the standard React-native choice."
            ),
            "confirm_only": False,
        }

    # ------------------------------------------------------------------
    # Branch 8 — DEFAULT → driver.js, anchor data-tour
    # ------------------------------------------------------------------
    return {
        "substrate": "driver.js",
        "anchor_attr": "data-tour",
        "reason": (
            "No override condition fired. Driver.js is the default substrate — "
            "5.9KB gzip, MIT licensed, zero dependencies, framework-agnostic, "
            "with fully serializable steps. Confirm this is correct before building."
        ),
        "confirm_only": True,
    }
