---
name: bootstrap
description: "Internal SKILL — invoked by the bare router on first run, or directly when the user says 'set up vibe-walk', 'init vibe-walk', or '/vibe-walk:bootstrap'. Classifies the host app, infers the framework + likely substrate, detects existing onboarding, and writes .vibe-walk/config.json. Idempotent — re-runnable to refresh stale config."
---

# /vibe-walk:bootstrap — set up the lay of the land

Read [`../guide/SKILL.md`](../guide/SKILL.md) for shared agent behavior (Sherpa persona, posture, conventions), then follow this command.

## What this command does

The repo has no `.vibe-walk/` directory yet (or its config is stale). Bootstrap establishes what app this is and which substrate the tour will likely target, then writes config. The agent's job:

1. **Auto-classify the app type and framework** by reading the codebase (`package.json`, `README.md`, top-level dirs, route surface). Don't ask what you can infer.
2. **Resolve the likely substrate** by running the substrate decision tree (see [`../guide/references/conventions.md`](../guide/references/conventions.md) D3). This is provisional — `walk` confirms it at the gate.
3. **Detect existing onboarding** (welcome modals, flybys, tours, tooltips) so the eventual tour sequences after it, not on top of it.
4. **Confirm classification** in ONE short question. Surface the inference; let the builder correct.
5. **Write `.vibe-walk/config.json`.**
6. **Hand back to the router.** No lecture.

## Hard rules

- **Do work first, ask second.** One confirmation question max.
- **Never auto-fire discover after bootstrap.** Bootstrap writes config; the builder kicks off the next step.
- **No telemetry.** One local file, then stop.
- **Idempotent.** If `.vibe-walk/config.json` exists, treat as a refresh (default yes if `last_inferred_at` >30 days, else no). Don't silently overwrite.

## Session + friction logging

At command start, call `session-logger.start("bootstrap", <project_dir>)` (see [`../session-logger/SKILL.md`](../session-logger/SKILL.md)) for the sessionUUID; hold it for the run; pass it to every `friction-logger.log()`. At command end, call `session-logger.end({...})` with `verdict: null` (bootstrap doesn't produce a verdict). Honor [`../guide/references/friction-triggers.md`](../guide/references/friction-triggers.md) — section `/vibe-walk:bootstrap`.

## Procedure

### Step 1 — classify app type + framework

Read in order, stop when unambiguous:
- `package.json` deps/scripts → web (`next`/`react`/`vue`/`svelte`/`astro`/`remix`), mobile (`react-native`/`expo`), desktop (`electron`), CLI (`commander`/`yargs`/`oclif` + no UI framework).
- `pyproject.toml` / `Cargo.toml` / `go.mod` for non-JS stacks.
- `README.md` first 50 lines if still ambiguous.

Canonical categories: `web-app` · `mobile-app` · `desktop-app` · `cli-tool` · `library-sdk` · `other`. Note the framework anchor (e.g., `Next.js 16`, `Vite + React 19`).

> **Tour-relevance note:** CLI tools and libraries have no visual surface to anchor a spotlight tour. If the app classifies as `cli-tool` or `library-sdk`, flag it — discovery will likely return a don't-build verdict.

### Step 2 — resolve likely substrate (provisional)

Run the D3 decision tree against the detected framework. Record the resolved substrate + the condition that picked it. This is provisional; `walk` confirms.

### Step 3 — detect existing onboarding

Grep the codebase for existing onboarding/tour/tooltip code (welcome modal, flyby, driver.js/shepherd/intro/joyride/reactour, coachmark, tooltip). Record what exists. This feeds the don't-build verdict (don't stack) and the trigger-sequencing gate.

### Step 4 — confirm (ONE question)

```
Looks like a [framework anchor] — I'd classify this as a [category],
likely [substrate] for the tour. [Existing onboarding: found X / none detected.]

Right? (yes / pick another / let me describe it)
```

### Step 5 — write `.vibe-walk/config.json`

```json
{
  "category": "<framework anchor> — <one-line purpose>",
  "framework": "<detected framework>",
  "likely_substrate": "<resolved substrate>",
  "existing_onboarding": ["<what was found>"],
  "last_inferred_at": "<ISO-8601 UTC, now>"
}
```

Create `.vibe-walk/` if needed. Atomic write. Do NOT create discovery.json here — that's `discover`'s job.

### Step 6 — hand back

```
Set up:
- Category: [category]
- Likely substrate: [substrate]
- Existing onboarding: [summary]
- Written: .vibe-walk/config.json

Want the surface read + tour verdict? Run /vibe-walk:discover.
```

Do NOT auto-fire discover.

## Refresh case

If config exists: if `last_inferred_at` >30 days, offer refresh (default yes); else offer refresh (default no). On yes, re-run steps 1–5 and surface what changed.

## Cross-references

- Guide: [`../guide/SKILL.md`](../guide/SKILL.md)
- Router: [`../vibe-walk/SKILL.md`](../vibe-walk/SKILL.md)
- Conventions (substrate tree D3): [`../guide/references/conventions.md`](../guide/references/conventions.md)
