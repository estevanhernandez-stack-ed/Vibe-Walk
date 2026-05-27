---
name: vibe-walk
description: "This skill should be used when the user says `/vibe-walk` (bare, no subcommand). Reads project state (.vibe-walk/ config + discovery output), recommends the next step in the linear flow — discover the app's surfaces, or build/skip the tour — and asks before launching. On first run (no .vibe-walk/ directory), hands off to bootstrap. Never auto-fires a build."
---

# /vibe-walk — bare router

Read [`../guide/SKILL.md`](../guide/SKILL.md) for shared agent behavior (Sherpa persona, posture, conventions), then follow this command.

## What this command does

Bare router. The user invoked `/vibe-walk` with no subcommand — they want to know the next step. Vibe-Walk is a linear two-phase flow, not a multi-mode picker:

```
bootstrap (first run) → discover (Phase 1) → walk (Phase 1.5 + Phase 2)
```

The agent's job:

1. **Detect project state.** Is `.vibe-walk/config.json` present? Has discovery run (`.vibe-walk/discovery.json`)?
2. **Recommend ONE next step** with a one-line rationale.
3. **Ask before launching.** Never auto-fire discover or walk.

## Hard rules

- **Never auto-fire a build.** Always confirm before invoking discover or walk.
- **Read-only by default.** The router writes nothing. (Bootstrap, invoked from here on first run, writes config after the user confirms.)
- **Respect the verdict, surface the override.** If discovery returned a `don't-build` or `cheaper-first` verdict, surface it and its reasons — don't nudge toward building. But name that `/vibe-walk:walk` will accept an override (surface + confirm-once) when the builder has context the plugin lacks. The verdict is advisory, not a refusal.

## Routing logic

| State | Recommend |
|---|---|
| `.vibe-walk/config.json` absent | First-run path → invoke **bootstrap** |
| Config present, no `.vibe-walk/discovery.json` | **/vibe-walk:discover** — read the app's surfaces and get the verdict |
| Discovery present, verdict = `don't-build` or `cheaper-first` | Surface the verdict + its rationale. Do NOT recommend building. Offer `/vibe-walk:discover --refresh` if the app has changed. Mention that `/vibe-walk:walk` will accept an override (surface + ask once) if the builder has context the plugin lacks. |
| Discovery present, verdict = `build` | **/vibe-walk:walk** — run the interview gates and build the tour |

## First-run path (graceful)

If `.vibe-walk/config.json` is absent, say one short line and hand off to bootstrap — don't enumerate every missing file:

```
Fresh repo — no config yet. Let me get the lay of the land first.
```

Then invoke the **bootstrap** SKILL ([`../bootstrap/SKILL.md`](../bootstrap/SKILL.md)). After bootstrap returns, do not auto-recommend — bootstrap's output prompts the user to re-run `/vibe-walk`.

## Output shape (when config exists)

```
Next: /vibe-walk:<step>

Why: [one-line rationale from state]

Project state:
- Config: <inferred YYYY-MM-DD>
- Discovery: <present (verdict: build|don't-build|cheaper-first) | not run yet>

Run /vibe-walk:<step>? (yes / not now)
```

Wait for the user. Do not invoke any subcommand on your own.

## Cross-references

- Bootstrap: [`../bootstrap/SKILL.md`](../bootstrap/SKILL.md)
- Guide: [`../guide/SKILL.md`](../guide/SKILL.md)
- (Phase skills `discover` and `walk` are added in later milestones.)
