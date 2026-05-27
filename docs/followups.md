# Follow-ups

Append-only list of work carried out of a session but not yet shipped. Each item names the artifact, the reason, and the next concrete move. Cross off (strikethrough + date) when done.

---

## 1. Soften the walk-SKILL hard gate to confirm-then-proceed

**Where:** `plugins/vibe-walk/skills/walk/SKILL.md` — around line 47, the "Prerequisites" section.

**Current behavior:**

> "If `verdict != 'build'` → surface the verdict and its reasons, and explain that Phase 1.5 runs only on a `build` verdict. Offer to re-run discovery."

That is a **hard gate** — the SKILL refuses to proceed unless discovery returned `build`.

**Wanted behavior:** advisory, not gating. Surface the verdict + its reasons, ask the builder once if they want to proceed anyway, then continue. Default override path = **single confirmation**, not a 3-step dialog.

**Why:** Captured 2026-05-26 by Este during `/vibe-iterate` bootstrap — *"the 'we don't build it' is overstated, we don't want to gate it. if they want a walkthrough for something small then meh."* Hard-gating overweights one signal at the expense of builder autonomy. The earn-the-tour framing is still the differentiator (no other onboarding vendor will say "don't build one") and stays as external positioning — the gate-vs-advisory distinction is **internal posture only**.

**Concrete next move:**

1. Edit `plugins/vibe-walk/skills/walk/SKILL.md` lines ~43–48 to: surface verdict + reasons → ask once `"Discovery returned <verdict>: <reason>. Proceed anyway? (y/N)"` → continue on `y`.
2. Sweep `plugins/vibe-walk/skills/discover/SKILL.md` for prose that implies the verdict is dispositive; soften.
3. Sweep README — likely no change needed (external framing of "earn the tour" still accurate), but verify.
4. Log the change to the 626Labs Dashboard once item #2 below lands.

**Related:** the feedback memory at `~/.claude-personal/projects/<this-repo>/memory/feedback_verdict-not-a-gate.md` carries the rule across sessions.

---

## 2. Create the 626Labs Dashboard project for Vibe-Walk

**Where:** 626Labs Dashboard, via `mcp__626labs__manage_projects` action `create`.

**Current state:** `findByRepo` against `https://github.com/estevanhernandez-stack-ed/Vibe-Walk.git` returns zero matches. The repo has `.mcp.json` bound to the 626Labs MCP server, but the project entry itself does not exist yet.

**Why:** Vibe-Walk is the 10th plugin in the Vibe family (sibling to vibe-cartographer, vibe-doc, vibe-iterate, vibe-keystone, etc., which are tracked). Without a Dashboard project, `mcp__626labs__manage_decisions log` rejects entries — the server requires a non-null `projectId`. Decisions that should land in the audit trail (e.g., the verdict-advisory posture call captured above) currently can only be saved to local memory + this followups file.

**Concrete next move:**

```
mcp__626labs__manage_projects create:
  name: "Vibe-Walk"
  description: "Claude Code plugin that generates instrumented Driver.js spotlight tours for apps
                that earn one — with an advisory tour-readiness discovery pass and a human-gated
                anchor injection codemod. 10th in the Vibe family."
  category: "claude-code-plugin"
  status: "Launched"           (v0.1.0 live in marketplace + canary)
  version: "0.1.0"
  techStack: ["python", "node", "jscodeshift", "jest", "pytest", "driver.js"]
  tags: ["vibe-family", "onboarding", "spotlight-tour", "marketplace"]
  liveUrl: "https://github.com/estevanhernandez-stack-ed/Vibe-Walk"
```

Then `linkRepo` with `repoUrl: https://github.com/estevanhernandez-stack-ed/Vibe-Walk.git` so future `findByRepo` calls bind silently. Then re-log the verdict-advisory decision against the new `projectId`.

---
