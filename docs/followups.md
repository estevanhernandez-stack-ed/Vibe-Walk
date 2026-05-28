# Follow-ups

Append-only list of work carried out of a session but not yet shipped. Each item names the artifact, the reason, and the next concrete move. Cross off (strikethrough + date) when done.

---

## 1. ~~Soften the walk-SKILL hard gate to confirm-then-proceed~~ — shipped 2026-05-27 in [PR #1](https://github.com/estevanhernandez-stack-ed/Vibe-Walk/pull/1)

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

## 2. ~~Create the 626Labs Dashboard project for Vibe-Walk~~ — shipped 2026-05-27, project ID `nGhNenQOaYmTyv6rkr3z`

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

## 3. ~~Tour i18n — emit step copy as a separate `spotlight.i18n.json`~~ — shipped 2026-05-27 in [PR #4](https://github.com/estevanhernandez-stack-ed/Vibe-Walk/pull/4)

**Where:** `plugins/vibe-walk/scripts/build/emit_tour_module.py`

**Source:** atlas queue from `/vibe-iterate:competitive` run 2026-05-27. `:rate` score **17/25** (match, queue bucket). Multi-vendor pattern: Tango Workflow Translations (Feb 4), Chameleon Copilot Translations, Scribe Voice Transcription i18n. 4 of 8 spied competitors ship some translation flow.

**Why:** Vibe-Walk's emitted `spotlightSteps.ts` inlines step copy as English strings today. Hosts shipping to non-English markets currently have to fork the emitted file to localize. Extracting copy to a sibling `spotlight.i18n.json` makes localization a maintained-by-host concern without touching the step structure.

**Concrete next move:**

1. Extend `emit_tour_module.py` to write a sibling `spotlight.i18n.json` keyed by step name:
   ```json
   {
     "spotlight.step.project-dashboard.title": "Your project dashboard",
     "spotlight.step.project-dashboard.description": "Everything you've built lives here.",
     ...
   }
   ```
2. The emitted `spotlightSteps.ts` references keys instead of inlining strings (with a fallback for missing keys).
3. Tests under `tests/test_emit_tour_module.py` — add ~4-5 cases: i18n.json shape, steps.ts references keys (not strings), no inline copy in step bodies, missing-key fallback to step name.
4. Walk SKILL Phase 2 close-out lists `spotlight.i18n.json` in the file list.
5. README + `CLAUDE.md` mention i18n support; note migration for existing v0.1.0 hosts (their inlined copy continues to work via fallback path).

**Posture notes:** contract change on the emitted module shape. Existing v0.1.0 hosts who already adopted the inlined-copy module need a CHANGELOG migration note. The change stays additive at runtime (fallback path means missing-key surfaces the step name, not an error).

**Cart-detection:** light flow expected — single emitter, bounded tests.

**Recommended ship order:** **#1 of the three** — smallest contract change, ship first while the muscle is warm.

---

## 4. Drift-aware tour audit — extend `/vibe-walk:vitals` with anchor-vs-source mismatch detection

**Where:** new module `plugins/vibe-walk/scripts/diagnostics/anchor_drift.py` + wire into `plugins/vibe-walk/skills/vitals/SKILL.md`

**Source:** atlas queue from `/vibe-iterate:competitive` run 2026-05-27. `:rate` score **21/25** (differentiate). The unique-moat story: Chameleon ships **Ranger** (AI agent that fixes detached elements *at runtime*) — proof that anchor drift is a real category problem they've solved post-hoc. Vibe-Walk's source-injected `data-tour` anchors avoid the failure mode by construction, but they can still drift if the host renames a component or removes the anchor after emission.

**Why:** Vendors literally cannot ship this — they have no build-time codemod, so they can't compare "emitted step list" vs "current source anchors." We can, and the prevention story is structurally unavailable to them. This is the **differentiator-extension** ship.

**Concrete next move:**

1. New script `anchor_drift.py`:
   - Read host source for `data-tour="..."` attribute occurrences.
   - Parse `spotlightSteps.ts` (the emitted file) for each step's `element` selector.
   - Diff: missing anchors (in steps.ts, not in source), orphan anchors (in source, not in steps.ts), renamed (heuristic).
   - Output: drift report with file path + line number for each mismatch + last-emit timestamp.
2. Extend `plugins/vibe-walk/skills/vitals/SKILL.md` to call `anchor_drift.detect()` as a vitals check; format the drift report inline with the existing vitals output.
3. New test file `tests/test_anchor_drift.py` — clean state (no drift), missing anchor (drift), orphan anchor (drift), renamed anchor, multi-step partial drift, no `spotlightSteps.ts` (no-op).
4. Optional fixture under `tests/fixtures/drift_scenarios/` showing each drift type.

**Posture notes:** vitals is read-only by spec; this addition stays read-only. Outputs a report; never auto-edits.

**Cart-detection:** light flow expected — single new diagnostic module + integration into existing read-only SKILL.

**Recommended ship order:** **#2 of the three** — bigger story than #1, but no D-constraint conflicts, no public-API breakage, additive only.

---

## 5. Jest 30 bump — surgical dependency upgrade

**Where:** `package.json` (jest + jest-environment-node), possibly `tests/` if the codemod modifies syntax.

**Source:** `/vibe-iterate:radar` run 2026-05-27 surfaced Context7's `/websites/jestjs_io_30_0` doc index, suggesting Jest 30 docs exist. Not confirmed: whether 30.x is stable + whether a codemod ships with it.

**Why:** Routine maintenance. Currently pinned at `^29.7.0`; running Jest 30 keeps the test toolchain current and unlocks v30 features the suite may want later. Pure plumbing, not user-facing.

**Concrete next move:**

1. Run `/vibe-iterate:scan-releases jest` first — confirms release status, breaking changes, codemod availability.
2. If 30.x stable and codemod available:
   - Bump `package.json` to `^30.x.y` for both `jest` and `jest-environment-node`.
   - Run the codemod against the JS test files (`plugins/vibe-walk/scripts/anchors/__tests__/`).
   - Run the full test suite — expect green.
3. If 30.x exists but codemod doesn't / breaking changes are wide:
   - **Defer** this ship; substitute with one of the held-back candidates:
     - *Intra-tour branching* (with cap-respecting design — needs a brainstorming session first).
     - *AI step-copy refinement* (probably stays declined for honesty-layer reasons; revisit only if `:scan-releases` reveals nothing).
4. CLAUDE.md (project) Tech Stack section may need a version note if v30 introduces visible-to-builder changes.

**Posture notes:** test framework — affects all tests but well-bounded. Tests must remain green; no new feature, no contract change.

**Cart-detection:** light flow expected unless the codemod fails and we end up rewriting test syntax by hand.

**Recommended ship order:** **#3 of the three** — conditional on `:scan-releases` confirming a clean upgrade path.

---

## 6. `npm audit fix` — resolve `tmp` Path Traversal (transitive dev dep)

**Where:** `package-lock.json` (transitive resolution; primary surface is `npm audit fix`)

**Source:** surfaced by `npm install` during the Jest 30 bump (PR #8) — `npm audit` flags 1 high-severity vulnerability in `tmp` ([GHSA-ph9p-34f9-6g65](https://github.com/advisories/GHSA-ph9p-34f9-6g65) — Path Traversal via unsanitized prefix/postfix). **Pre-existing**, not introduced by the Jest 30 bump (verified via dev-only audit scope). Likely pulled in transitively by `jscodeshift` or one of jest's own deps.

**Why:** high-severity flag should not linger, even in a dev-only chain. The fix is available via the standard `npm audit fix` recipe — no major bumps required. Letting it sit invites a `Dependabot`-style nag and clutters future `npm install` output.

**Concrete next move:**

1. Branch `chore/npm-audit-fix-tmp`.
2. Run `npm audit fix` — confirms no major version bumps. If it would do anything destructive, stop and re-evaluate.
3. Verify lockfile diff is scoped (only `tmp` + any tiny intermediate bumps).
4. `npm test` → expect 228/228 green.
5. If `npm audit` still reports issues after the fix, document the residual in the PR body; don't escalate to `--force`.
6. Ship as a single `chore(deps)` PR. Light flow.

**Posture notes:** transitive dev-dep — does not ship to host apps. Path Traversal in `tmp` is a real CVE class but the exposure here is constrained to local test runs (anyone running our test suite with a malicious `tmp` prefix arg, which doesn't happen in normal use). Worth fixing on hygiene grounds, not panic grounds.

**Cart-detection:** light flow — single command, single file changed (lockfile), tests as the verification gate.

**Recommended ship order:** independent — not part of the three-feature plan. Ship when convenient; doesn't block anything.

---

## Planning notes (not items themselves)

- All three were selected by `/vibe-iterate:rate` against the atlas runners-up from PR #2's `/vibe-iterate:competitive` run. The full match/differentiate/decline diff lives in `.vibe-iterate/atlas.jsonl` for the PR #2 entry (`rejected_runners_up` array).
- **Ship order = small → strategic → maintenance.** Each ships as its own PR per the vibe-iterate one-PR-per-invocation hard rule.
- **Held back from this plan:** *intra-tour branching* (D1 conflict — needs design pass) and *AI step-copy refinement* (honesty-layer risk — needs principle check). Both stay in the atlas runners-up for future iteration windows.
