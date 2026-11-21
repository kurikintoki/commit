# commit

## Overview
The `/commit` skill: make one Conventional Commit on the current branch with exactly the given
paths (or all new, updated and deleted files), never push, never stage credential-like files.
Source: `.claude/skills/commit/` (`SKILL.md`, `select_paths.py`, `test_select_paths.py`), exposed
globally through the symlink `~/.claude-personal/skills/commit`. `/prompt --commit` (prompt
project, PLAN16) reads this `SKILL.md` and follows it.
Spec: `03_plans/PLAN3.md` + `03_plans/PLAN5.md` (SKILL.md wording) +
`03_plans/PLAN7.md` (only the named files; `others` in the JSON). Human-facing usage and install: `README.md`.

## How to run
- Test: `python3 .claude/skills/commit/test_select_paths.py`
- Work in this repo is driven by `/prompt [@02_prompts/PROMPT<n>.md]` (user-invoked only).

## Conventions
- **`.claude/skills/commit/` is the live global copy.** Through the symlink, every edit takes
  effect in all projects at once, so run the tests before leaving it changed.
- Behavior changes start as a new PLAN in `03_plans/` (don't rewrite Implemented PLANs).
  Then keep `SKILL.md`, `select_paths.py`, the tests and `README.md` in sync.
- Write the arguments placeholder (`$ARGUMENTS`) in `SKILL.md` only on the `Arguments:` line;
  Claude Code substitutes it everywhere. A test checks this (PLAN5).
- Plans: `03_plans/PLAN*.md`, managed with `/plan-index` (rebuild `INDEX.md` after any PLAN change).
  Results: `04_results/RESULT<n>.md`.
- Scripts: Python 3.9+, standard library only. `select_paths.py` exit codes (keep in sync with
  `SKILL.md` and the tests): 1 not a repo / usage, 2 credential-like path, 3 nothing to commit,
  4 path problem (missing, ignored, outside), 5 detached HEAD.
- Tests run git with the user's global config and global ignore file switched off. Fixture files
  in end-to-end tests must avoid names the sandbox can't delete (`.env`, `*.key`, `*.pem`,
  `id_rsa`, `secrets/` …); test those patterns with the name-only unit tests.
- Managed policy in this environment: Bash can't write to `.claude/skills/` or
  `~/.claude-personal/skills/` (edit skill files with Edit/Write; symlinks are the user's job), and
  `rm -r…` is blocked by a hook. Don't work around either; report it.
- Commits: Conventional Commits (`docs:`, `feat:`, `chore:` …).
