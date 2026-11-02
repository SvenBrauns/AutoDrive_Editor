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

- At every good break (a commit that finishes a part, a merge, an agreed plan), give a short hand-over: whether to `/clear` now, which model to use next with `/model` (a smaller one for routine work like git cleanup, small fixes, docs; the larger one for planning and complex features), and a ready-to-paste first prompt for the new session. DEVELOPMENT.md, `docs/design/` (designs and the task list `tasks.md`) and `git log` carry the context over.
- Only take screenshots when the look of something is the point of the change. Otherwise rely on tests.
- Don't spawn an agent for git work.
- Keep tool output small: `ruff check . --output-format concise`, `python -m pytest -q` piped through `tail` when only the summary matters.

## 6. Project Conventions

- Write all code (app and tests) in compact, normal Python style: `ruff format .`, not one argument per line. `pyproject.toml` is the source of truth.
- While working, run only the test files for the code you changed. Run the full suite (`python -m pytest -q`) and `ruff check . --output-format concise` once before a commit.
- New behavior gets a test, not every function. Test it once, at the lowest level that shows it (logic under `editing/`, `file_io/` etc.); a UI test only checks the wiring a user sees, through the public interface, not private attributes or exact texts. Test files mirror the package structure under `tests/`.
- When a test fails, first decide: is the code wrong, or did the requirement change? Fix the code by default. Change a test only when the behavior was meant to change, and say so in the reply with the reason.
- Every edit of the data model is an `EditCommand` pushed via `EditHistory.push()`, never a direct change to `AutoDriveData`. See DEVELOPMENT.md for architecture.
- Keep the virtualization (never permanent NodeItems for all nodes).

## 7. Git

- Claude creates branches, commits and merges. Only the user pushes, tags and releases.
- Local `main` is the development line: every commit on it passes tests and ruff. GitHub's `main` gets a push only at a release; releases are tags.
- One branch per roadmap item or larger fix, kebab-case (e.g. `stations-junctions`). Typos, small doc fixes and one-line fixes go straight onto `main`.
- Commit after each working piece (a function with its tests, a dialog, the docs) when tests pass, and always before a `/clear`, even halfway through a feature (on its branch). Short subject in the style of `git log`, plus the co-author line.
- Merge with `--no-ff` only after the user has confirmed the feature works, then delete the branch.
- Commit only what a user of the repository needs: code, tests, README, MANUAL (en/de), CHANGELOG, ROADMAP (a short outlook of general directions, updated before a push; detailed plans stay in `docs/design/`), CLAUDE.md, DEVELOPMENT.md. Never: design docs (`docs/design/`, git-ignored; they become manual sections when a feature is done), analysis scripts, screenshots, local data.
- Before the user pushes, check `git log origin/main..main --name-only` for files that don't belong.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
