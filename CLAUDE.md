# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Token Usage

**The user has limited usage. Help keep sessions short.**

- After a feature branch is merged, suggest `/clear` before the next feature. ROADMAP.md, DEVELOPMENT.md and `git log` carry the context over.
- When the next steps are routine (merging, small fixes, doc updates), suggest switching to a smaller model with `/model`. Suggest the larger model again for planning and complex features.
- Only take screenshots when the look of something is the point of the change. Otherwise rely on tests.
- Keep the reminders to one short line, not every turn.
- Don't commit, merge or push yourself, and don't spawn an agent for it. Write the git commands (with commit message) for the user to run.
- Keep tool output small: `ruff check . --output-format concise`, `python -m pytest -q` piped through `tail` when only the summary matters.

## 6. Project Conventions

- Write all code (app and tests) in compact, normal Python style: `ruff format .`, not one argument per line. `pyproject.toml` is the source of truth.
- Before finishing: `python -m pytest -q` and `ruff check . --output-format concise`.
- New functions get tests; test files mirror the package structure under `tests/`.
- Every edit of the data model is an `EditCommand` pushed via `EditHistory.push()`, never a direct change to `AutoDriveData`. See DEVELOPMENT.md for architecture.
- Keep the virtualization (never permanent NodeItems for all nodes).

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
