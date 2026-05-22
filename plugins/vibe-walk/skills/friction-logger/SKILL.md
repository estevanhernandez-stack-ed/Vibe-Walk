---
name: friction-logger
description: "Internal SKILL — not a slash command. Append-only friction capture for vibe-walk. Invoked by bootstrap, discover, and walk at the trigger points listed in guide/references/friction-triggers.md. Implements Pattern #6 (Friction Log) of the Self-Evolving Plugin Framework."
---

# friction-logger — append-only friction capture

Internal SKILL. Not user-invocable. Commands call `log()` at the trigger points in [`../guide/references/friction-triggers.md`](../guide/references/friction-triggers.md). At startup, `bootstrap` (and any command) may call `detect_orphans()` to convert abandoned sessions into friction signal.

## Where the log lives

`~/.claude/plugins/data/vibe-walk/friction.jsonl`

- Single append-only file. Never rewrite existing lines.
- Cross-project. Directory created on first use (mkdir -p).

## Entry shape

```json
{
  "schema_version": 1,
  "timestamp": "2026-05-22T14:40:00-05:00",
  "plugin": "vibe-walk",
  "plugin_version": "0.0.1",
  "command": "discover",
  "project_dir": "Celestia3",
  "sessionUUID": "550e8400-e29b-41d4-a716-446655440000",
  "friction_type": "verdict_overridden",
  "confidence": "high",
  "symptom": "Agent verdict was don't-build (existing flyby + welcome modal); user chose to build anyway.",
  "complement_involved": null
}
```

### Field definitions

- **schema_version / timestamp / plugin / plugin_version / command / project_dir** — same semantics as the session-logger.
- **sessionUUID** — the value from `session-logger.start()` for this run. Required so friction clusters under its session.
- **friction_type** — one of the types named in `friction-triggers.md`: `repeat_question` · `rephrase_requested` · `misclassification` · `default_overridden` · `verdict_overridden` · `shortlist_rejected` · `guardrail_pushed` · `anchor_unresolvable` · `command_abandoned`.
- **confidence** — `low` | `medium` | `high`. How sure the agent is this is real friction vs noise.
- **symptom** — one short sentence describing what happened. For `repeat_question` / `rephrase_requested`, MUST quote the prior turn (defensive default — without a quote, do not log).
- **complement_involved** — identifier of a composed plugin/skill if the friction involves one; else `null`.

## Procedure: `log(entry)`

1. Build the entry from the caller's partial (`friction_type`, `confidence`, `symptom`, `sessionUUID`, optional `complement_involved`) + the audit fields.
2. Append one JSON line to `~/.claude/plugins/data/vibe-walk/friction.jsonl` (mkdir -p first).
3. On any failure, warn to stderr and continue. Never block the command.

**Defensive default:** for the universal triggers (`repeat_question`, `rephrase_requested`), do NOT log unless `symptom` quotes the specific prior turn. False friction pollutes the evolve signal.

## Procedure: `detect_orphans()`

Called once at command startup, after `session-logger.start()` has written this run's sentinel.

1. Scan recent session files for sentinels (`outcome: "in_progress"`) with no matching terminal entry (same `sessionUUID`) and a timestamp older than 24h.
2. For each, append a `command_abandoned` friction entry (`confidence: "medium"`, `symptom` naming the abandoned command + age).
3. This is the only path that emits `command_abandoned` — do not also log it from the regular trigger table.

## What NOT to log

No PII beyond `project_dir` basename. No secrets. No host-app source. No transcripts — `symptom` is one sentence, structured signal only.

## Privacy posture

Local-first, user-inspectable, user-deletable. **NO telemetry.**

## Why this exists

Friction entries are the highest-signal input to **Level 3** — `/vibe-walk:evolve-walk` weights them to propose improvements. The most load-bearing type is `verdict_overridden`: it tells us when the plugin's earn-the-tour verdict disagrees with the builder, which is exactly the judgment the plugin most needs to calibrate.

## Cross-references

- Sibling: [`../session-logger/SKILL.md`](../session-logger/SKILL.md)
- Trigger map: [`../guide/references/friction-triggers.md`](../guide/references/friction-triggers.md)
- Reader: [`../evolve-walk/SKILL.md`](../evolve-walk/SKILL.md)
