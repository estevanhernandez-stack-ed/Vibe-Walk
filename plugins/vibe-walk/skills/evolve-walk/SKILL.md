---
name: evolve-walk
description: "This skill should be used when the user says `/vibe-walk:evolve-walk` and wants vibe-walk to reflect on past sessions and propose improvements to itself. Reads ~/.claude/plugins/data/vibe-walk/ session logs + friction.jsonl, weights findings, and writes proposed SKILL/verdict/convention edits to docs/proposed-changes.md in the vibe-walk repo. Never auto-applies. L3 self-evolution."
---

# /vibe-walk:evolve-walk — propose improvements from observed use

Read [`../guide/SKILL.md`](../guide/SKILL.md) for shared agent behavior (Sherpa persona, posture), then follow this command.

Named `evolve-walk` (not bare `evolve`) so it never collides with the other vibe-* plugins' evolve skills. Implements Level 3 of the Self-Evolving Plugin Framework.

## What this command does

Reads the local session + friction logs vibe-walk has accumulated, finds patterns, and **proposes** edits to the plugin — never applies them. The builder reviews and decides.

1. **Read the data.**
   - Sessions: `~/.claude/plugins/data/vibe-walk/sessions/*.jsonl` (sentinel + terminal entries).
   - Friction: `~/.claude/plugins/data/vibe-walk/friction.jsonl`.
2. **Weight the findings.** Higher weight for: high-confidence friction, repeated patterns across sessions, and `verdict_overridden` entries (the verdict is the plugin's core judgment — disagreement is the strongest evolve signal).
3. **Propose edits.** Map findings to concrete changes — a verdict-condition tweak, a substrate-tree adjustment, a copy-guardrail change, a convention update, a SKILL clarification.
4. **Write `docs/proposed-changes.md`** in the vibe-walk repo. Never edit SKILLs/conventions directly.

## Hard rules

- **Never auto-apply.** Output is a proposal document the builder reviews. No edits to SKILLs, conventions, or scripts.
- **No telemetry.** Reads local logs only; writes one local proposal file.
- **Evidence-cited.** Every proposed change names the sessions/friction entries that motivated it (by date + sessionUUID + count). No proposal without evidence.
- **Honest about thin data.** If there aren't enough sessions to support a pattern, say so and propose nothing rather than over-fitting one run.

## Weighting

| Signal | Weight |
|---|---|
| `verdict_overridden` (high confidence), repeated | Highest — the earn-the-tour verdict is mis-calibrated; propose a condition change |
| `anchor_unresolvable`, repeated | High — the anchor-readiness model or the 4-gate boundary needs tuning |
| `guardrail_pushed` (step count), repeated | Medium — revisit the 5-step framing or the split-tour suggestion |
| `default_overridden` (substrate), repeated | Medium — the substrate decision tree may need a new branch |
| `misclassification`, repeated | Medium — bootstrap classification heuristics need work |
| Single-occurrence, low confidence | Lowest — note, don't propose |

## Output: `docs/proposed-changes.md`

For each proposal:
- **Finding** — the pattern, with evidence (dates, sessionUUIDs, counts).
- **Proposed change** — the specific file + the edit.
- **Rationale** — why this follows from the evidence.
- **Risk** — what the change might break or over-correct.

Sort by weight, highest first. If no proposals clear the evidence bar, write a short "insufficient signal — N sessions, M friction entries; nothing to propose yet" note.

## Cross-references

- Session log: [`../session-logger/SKILL.md`](../session-logger/SKILL.md)
- Friction log: [`../friction-logger/SKILL.md`](../friction-logger/SKILL.md)
- Guide: [`../guide/SKILL.md`](../guide/SKILL.md)
