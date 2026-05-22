---
name: vitals
description: "This skill should be used when the user says `/vibe-walk:vitals` or wants a structural integrity check on the vibe-walk install. Runs read-only structural checks and reports findings in a banner-style report. Implements Pattern #8 (Plugin Self-Test) from the Self-Evolving Plugin Framework. Read-only — no auto-fix in v0.0.1."
---

# /vibe-walk:vitals — structural self-test

Slash command `/vibe-walk:vitals`. Runs **read-only** structural checks against the installed plugin files, reports findings in a banner-style report with per-check status (✓ pass, ⚠ warn, ✗ fail), and prints a summary line. No writes, no auto-fix in this release.

This is Pattern #8 (Plugin Self-Test) from the Self-Evolving Plugin Framework. Vitals surfaces drift between files before that drift silently breaks a command mid-flow.

## Before You Start

Read [`../guide/SKILL.md`](../guide/SKILL.md) for the Sherpa persona and posture. Vitals applies the Sherpa voice to the opening line only — the report body is neutral.

## Session Logging

Call `session-logger.start("vitals", project_dir_basename)` at command start. Hold the returned `sessionUUID`. At command end, call `session-logger.end()` with:

- `outcome: "completed"` on a clean run.
- `outcome: "partial"` if a check could not run due to an unreadable file.
- `outcome: "error"` only if the command crashed before the summary line rendered.
- `verdict: null` — vitals produces no tour verdict.
- `tour_built: false`
- `anchor_review_needed: null`
- `key_decisions`: short strings for notable findings (e.g., `"friction-triggers.md missing walk triggers"`, `"vitals SKILL.md absent"`, `"plugin.json version field missing"`).
- `friction_notes: []` — vitals does not emit friction entries; see "Friction Logging" below.

## Friction Logging

Vitals does **not** call `friction-logger.log()`. Running a structural self-test is not friction. This section is intentionally empty — per the friction-triggers contract, the absence here is auditable.

## Persona Adaptation

One-sentence opening before the report renders:

```
Running structural sweep — checking plugin.json, all nine SKILLs, scripts, guide references, and friction-trigger wiring.
```

Then render the report. No narration between checks.

## Runtime Paths

All paths vitals reads (never writes):

| What | Where |
|------|-------|
| Plugin root | `<repo>/plugins/vibe-walk/` — walk up from this SKILL file's location. |
| Plugin manifest | `plugins/vibe-walk/.claude-plugin/plugin.json` |
| SKILL files | `plugins/vibe-walk/skills/*/SKILL.md` |
| Guide references | `plugins/vibe-walk/skills/guide/references/*.md` |
| Discovery scripts | `plugins/vibe-walk/scripts/discovery/inventory_surfaces.py`, `anchor_readiness.py`, `build_verdict.py` |
| Build scripts | `plugins/vibe-walk/scripts/build/emit_tour_module.py`, `emit_analytics.py`, `substrate_tree.py` |
| Anchor codemod | `plugins/vibe-walk/scripts/anchors/inject_anchors.js` |
| Friction triggers doc | `plugins/vibe-walk/skills/guide/references/friction-triggers.md` |

If any path is unreadable for reasons other than "does not exist" (permission denied, I/O error), the affected check reports `✗ fail` with the error surfaced verbatim.

## Flow

1. Write the persona-adapted opening line.
2. Read `plugin.json` version field. Fall back to `"unknown"` on parse failure. Capture local ISO datetime for the banner.
3. Run checks #1 through #7 in order. A failure in one check never aborts the next — the report always includes all seven sections.
4. Render the report (banner + per-check boxes + summary line).
5. Print the closing advisory.
6. Call `session-logger.end()`.

## Check Specifications

### Check #1 — plugin.json valid + version present

**Purpose:** the plugin manifest is parseable JSON with the required fields.

**(a) Read.** Open `plugins/vibe-walk/.claude-plugin/plugin.json`.

**(b) Evaluate.**
1. File missing → ✗ fail.
2. Not parseable JSON → ✗ fail with parse error.
3. Parseable → verify `"name"`, `"version"`, `"description"`, `"author"` all present and non-empty. Collect missing fields.

**(c) Report.**
- ✓ pass: all required fields present. Include: `name: <name>, version: <version>`.
- ✗ fail: file missing or unparseable, or one or more required fields missing. List each issue.

**(d) Fail-soft.** Any I/O error → ✗ fail with the error text.

---

### Check #2 — All expected SKILL directories + SKILL.md files present with valid frontmatter

**Purpose:** every skill the plugin declares exists on disk with parseable YAML frontmatter (`name` + `description` fields).

**(a) Read.** Check for these nine expected skill directories under `plugins/vibe-walk/skills/`:

```
vibe-walk    bootstrap    guide    discover    walk
session-logger    friction-logger    evolve-walk    vitals
```

For each, confirm `SKILL.md` is present. For each present `SKILL.md`, parse the YAML frontmatter block (the `---`-delimited header). Verify `name` and `description` fields exist and are non-empty strings.

**(b) Evaluate.** Collect:
- Missing skill directories.
- Present directories with missing `SKILL.md`.
- Present `SKILL.md` files with unparseable or incomplete frontmatter.

**(c) Report.**
- ✓ pass: all nine directories + SKILL.md files present, all frontmatter valid. Include: `9 SKILL.md files, all frontmatter valid`.
- ⚠ warn: a SKILL directory is present but its SKILL.md has incomplete frontmatter (non-fatal — skill loads but may not appear in the available-skills list).
- ✗ fail: one or more expected directories or SKILL.md files are absent. List each as `skills/<dir>/SKILL.md — missing`.

**(d) Fail-soft.** If a SKILL.md exists but frontmatter cannot be parsed, warn per-file with the parse error rather than failing the whole check (unless files are missing entirely, which is a fail).

---

### Check #3 — Discovery scripts present

**Purpose:** the three Phase 1 discovery scripts exist.

**(a) Read.** Check for:
- `scripts/discovery/inventory_surfaces.py`
- `scripts/discovery/anchor_readiness.py`
- `scripts/discovery/build_verdict.py`

**(b) Evaluate.** Record which are missing.

**(c) Report.**
- ✓ pass: all three present. Include: `3/3 discovery scripts present`.
- ✗ fail: one or more missing. List each as `scripts/discovery/<name> — missing`.

---

### Check #4 — Build scripts present

**Purpose:** the three Phase 2 build scripts exist.

**(a) Read.** Check for:
- `scripts/build/emit_tour_module.py`
- `scripts/build/emit_analytics.py`
- `scripts/build/substrate_tree.py`

**(b) Evaluate.** Record which are missing.

**(c) Report.**
- ✓ pass: all three present. Include: `3/3 build scripts present`.
- ✗ fail: one or more missing. List each as `scripts/build/<name> — missing`.

---

### Check #5 — Anchor codemod present

**Purpose:** the Phase 2 anchor-injection codemod exists.

**(a) Read.** Check for `scripts/anchors/inject_anchors.js`.

**(b) Evaluate.** Present or absent.

**(c) Report.**
- ✓ pass: `inject_anchors.js` present.
- ✗ fail: `scripts/anchors/inject_anchors.js — missing`.

---

### Check #6 — Guide references present

**Purpose:** all four guide reference files the plugin's skills depend on exist.

**(a) Read.** Check for:
- `skills/guide/references/sherpa-persona.md`
- `skills/guide/references/posture.md`
- `skills/guide/references/conventions.md`
- `skills/guide/references/friction-triggers.md`

**(b) Evaluate.** Record which are missing.

**(c) Report.**
- ✓ pass: all four present. Include: `4/4 guide references present`.
- ✗ fail: one or more missing. List each as `skills/guide/references/<name> — missing`.

---

### Check #7 — Friction-trigger table covers all three commands

**Purpose:** the `friction-triggers.md` table has a section for each of the three command SKILLs that fire it (`bootstrap`, `discover`, `walk`). Orphan or missing sections are a warn — the friction-detection surface is incomplete.

**(a) Read.** Open `skills/guide/references/friction-triggers.md`. Parse section headings (lines starting with `##`).

**(b) Evaluate.** Confirm these three headings are present (case-insensitive match on the command name):
- `## /vibe-walk:bootstrap`
- `## /vibe-walk:discover`
- `## /vibe-walk:walk`

For each present section, confirm it contains at least one friction trigger row (a bullet line starting with `-` or `*`). A section with an empty body is ⚠ warn — documented intentional emptiness is fine; undocumented emptiness is not.

**(c) Report.**
- ✓ pass: all three sections present and each has at least one trigger row. Include: `3 sections, all populated`.
- ⚠ warn: a section is present but has no trigger rows, and the file does not document the emptiness as intentional (compare: the `/vitals` section in vibe-cartographer's friction-triggers is documented-empty; an undocumented empty section here is a signal that triggers went missing).
- ✗ fail: one or more of the three expected sections is entirely absent from the file. List each as `/vibe-walk:<command> section — missing`.

**(d) Fail-soft.** File unreadable → ✗ fail with the I/O error. File present but empty → ✗ fail: `friction-triggers.md is empty`.

---

## Output Format

### Banner header

```
  Vibe-Walk — Vitals
  <version> · <ISO-local-timestamp>
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Then one blank line before the first check.

### Per-check boxed section

Each check renders as its own box:

```
  ┌──────────────────────────────────────────────────────────────────┐
  │ ✓  Check 1 — plugin.json valid + version present                  │
  └──────────────────────────────────────────────────────────────────┘
     name: vibe-walk, version: 0.0.1
```

```
  ┌──────────────────────────────────────────────────────────────────┐
  │ ✗  Check 2 — SKILL directories + SKILL.md files present           │
  └──────────────────────────────────────────────────────────────────┘
     skills/vitals/SKILL.md — missing
```

**Status glyph rules:** `✓` pass · `⚠` warn · `✗` fail. Two spaces after the glyph before the check title.

**Box width:** 68 columns.

**Empty findings for ✓ pass:** one summary line of the form `<headline metric>`.

### Summary line

After the last check box, one blank line, then:

```
  <N> ✓  ·  <N> ⚠  ·  <N> ✗
```

Indented two spaces. The three counts sum to 7.

### Closing advisory

```
Re-run /vibe-walk:vitals any time to re-check. For structural proposals, see /vibe-walk:evolve-walk.
```

## Expected output on a clean install

A fully-shipped v0.0.1 install should produce `7 ✓  ·  0 ⚠  ·  0 ✗`.

The first run before a dogfood session is the natural time to run this. If anything's missing or drifted, the check output names exactly what to fix before the session starts.

## Why this exists

vibe-walk has nine SKILLs, six scripts, and four guide-reference files that cross-reference each other. Without an on-demand diagnostic, a missing script or a deleted reference file surfaces as a cryptic error mid-build at the worst possible moment. `/vitals` makes the structural state visible in one pass — cheap to run, hard to misread.

## Cross-references

- Guide (Sherpa persona + posture): [`../guide/SKILL.md`](../guide/SKILL.md)
- Session logger: [`../session-logger/SKILL.md`](../session-logger/SKILL.md)
- Friction logger: [`../friction-logger/SKILL.md`](../friction-logger/SKILL.md)
- Self-evolution: [`../evolve-walk/SKILL.md`](../evolve-walk/SKILL.md)
- Friction triggers: [`../guide/references/friction-triggers.md`](../guide/references/friction-triggers.md)
