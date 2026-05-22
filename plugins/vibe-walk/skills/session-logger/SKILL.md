---
name: session-logger
description: "Internal SKILL — not a slash command. Two-phase append-only session log for vibe-walk: a sentinel entry at command start (outcome=in_progress) and a terminal entry at command end, paired by sessionUUID. Invoked by bootstrap, discover, and walk at start and end. Part of Level 2 (session memory) of the Self-Evolving Plugin Framework."
---

# session-logger — sentinel + terminal session log

Internal SKILL. Not user-invocable. Every vibe-walk command (`bootstrap`, `discover`, `walk`) calls `start()` at invocation and `end()` at completion. The two entries share a `sessionUUID` so `friction-logger.detect_orphans()` can pair them.

## Where the log lives

`~/.claude/plugins/data/vibe-walk/sessions/<YYYY-MM-DD>.jsonl`

- One file per day. Append-only. Never rewrite existing lines.
- Cross-project: a single user's logs from all their runs land here.
- Two entries per run (sentinel at start, terminal at end), paired by `sessionUUID`.
- Directory created on first use (mkdir -p as part of the first append).

## Entry shapes

### Sentinel (written by `start()`)

```json
{
  "schema_version": 1,
  "timestamp": "2026-05-22T14:25:00-05:00",
  "plugin": "vibe-walk",
  "plugin_version": "0.0.1",
  "command": "discover",
  "project_dir": "Celestia3",
  "sessionUUID": "550e8400-e29b-41d4-a716-446655440000",
  "outcome": "in_progress"
}
```

### Terminal (written by `end()`)

```json
{
  "schema_version": 1,
  "timestamp": "2026-05-22T14:55:00-05:00",
  "plugin": "vibe-walk",
  "plugin_version": "0.0.1",
  "command": "discover",
  "project_dir": "Celestia3",
  "sessionUUID": "550e8400-e29b-41d4-a716-446655440000",
  "outcome": "completed",
  "user_pushback": false,
  "friction_notes": ["verdict_overridden: agent said build, user paused"],
  "key_decisions": ["verdict: build", "6 candidate stops ranked", "aha = natal chart"],
  "verdict": "build",
  "tour_built": false,
  "anchor_review_needed": null
}
```

### Field definitions

Shared unless noted.

- **schema_version** — `1` for now.
- **timestamp** — ISO 8601 with timezone offset.
- **plugin** — always `"vibe-walk"`.
- **plugin_version** — read from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` `"version"`. Fall back to `"unknown"`.
- **command** — `bootstrap` | `discover` | `walk`.
- **project_dir** — basename of cwd. Never the full path.
- **sessionUUID** — UUID v4 from `start()`. Terminal + any friction entries reuse it.
- **outcome** — sentinel: `"in_progress"`. Terminal: `completed` | `abandoned` | `error` | `partial`.

**Terminal-only:**
- **user_pushback** — boolean; `true` if the user overrode a suggestion (be conservative).
- **friction_notes** — array of short strings (human recap; structured signal goes to `friction.jsonl`).
- **key_decisions** — array of short, high-signal decisions.
- **verdict** — `build` | `don't-build` | `cheaper-first` | `null` (for `bootstrap`).
- **tour_built** — boolean; `true` if `walk` emitted a tour module this run.
- **anchor_review_needed** — integer count of `REVIEW_NEEDED.md` items, or `null` if not applicable.

## Procedure: `start(command, project_dir)`

1. Generate a UUID v4 (`[guid]::NewGuid()` in PowerShell; `uuidgen`; `crypto.randomUUID()`).
2. Build the sentinel with the audit fields + `outcome: "in_progress"`.
3. Append to `~/.claude/plugins/data/vibe-walk/sessions/<today>.jsonl` (mkdir -p first).
4. On any failure, warn to stderr and continue — logging is instrumentation, not critical path.
5. Return the `sessionUUID`.

## Procedure: `end(entry)`

1. Build the terminal entry from the caller's partial (`sessionUUID`, `outcome`, `user_pushback`, `friction_notes`, `key_decisions`, `verdict`, `tour_built`, `anchor_review_needed`) + the audit fields.
2. The `sessionUUID` MUST equal the one from `start()`. Never mint a new one here.
3. Append to the same daily file. Create the dir if missing.
4. On failure, warn and continue.

## What NOT to log

- No PII beyond the `project_dir` basename. No full paths. No user identifiers.
- No secrets, ever. No host-app source or PR diffs. No full command arguments.

## Privacy posture

Local-first under `~/.claude/plugins/data/vibe-walk/`. User-inspectable, user-deletable (`rm -rf` and the plugin still works — just loses memory). **NO telemetry — nothing leaves the machine.**

## Why this exists

Raw material for **Level 3** — `/vibe-walk:evolve-walk` reads these entries (with `friction.jsonl`) to propose improvements. The sentinel pattern lets `detect_orphans()` tell "user abandoned" from "never ran."

## Cross-references

- Sibling: [`../friction-logger/SKILL.md`](../friction-logger/SKILL.md)
- Reader: [`../evolve-walk/SKILL.md`](../evolve-walk/SKILL.md)
