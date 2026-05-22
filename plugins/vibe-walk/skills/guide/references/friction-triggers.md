# Friction triggers — vibe-walk

Where each command invokes `friction-logger.log()`, with the friction type and confidence. Every `log()` call carries the `sessionUUID` from `session-logger.start()`. Implements Pattern #6 (Friction Log) of the Self-Evolving Plugin Framework.

## Universal triggers (all commands)

- **`repeat_question`** — the user asks the same thing twice in a run. Defensive default: do NOT log without a quoted prior turn in `symptom`.
- **`rephrase_requested`** — the user asks the agent to restate/redo output. Same defensive default.

## /vibe-walk:bootstrap

- **User corrects the inferred app category** → `friction_type: "misclassification"`, `confidence: "medium"`. Capture inferred vs corrected in `symptom`.
- **User overrides the inferred substrate** (e.g., picks React Joyride when the tree said Driver.js) → `friction_type: "default_overridden"`, `confidence: "low"`.

## /vibe-walk:discover

- **User overrides the build/don't-build verdict** (agent said don't-build, user builds anyway — or vice versa) → `friction_type: "verdict_overridden"`, `confidence: "high"`. Capture the verdict and the override in `symptom`. This is the highest-signal friction in the plugin — the verdict is the differentiator.
- **User rejects the ranked stop shortlist wholesale** → `friction_type: "shortlist_rejected"`, `confidence: "medium"`.

## /vibe-walk:walk

- **User changes the substrate at the gate after the tree resolved one** → `friction_type: "default_overridden"`, `confidence: "low"`.
- **User asks for more than 5 steps** → `friction_type: "guardrail_pushed"`, `confidence: "medium"`. Capture the requested step count.
- **A REVIEW_NEEDED anchor item is resolved by the user as "can't anchor this"** → `friction_type: "anchor_unresolvable"`, `confidence: "high"`. Feeds the anchor-readiness model.
