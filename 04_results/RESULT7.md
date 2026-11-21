# RESULT7 — Implement PLAN7: commit only the named files, and show what was left out

Source: chat instruction "implement @03_plans/PLAN7.md and write results in RESULT7.md" (no prompt
file; PROMPT7 answered PLAN6's 要確認). Date: 2026-11-22

## Task

Implement [[PLAN7]] (Confirmed): state and test that `/commit <paths>` commits only those files,
and add the "Left as is" report line, backed by a new `others` field in `select_paths.py`'s JSON.

## Result

| File | Change |
|---|---|
| `.claude/skills/commit/select_paths.py` | New JSON field `others`. In path mode it holds the status entries that weren't selected, in `git status` order, each once (an unselected rename under its new name); without paths it's `[]`. No new git calls, exit codes unchanged. The docstring is updated |
| `.claude/skills/commit/test_select_paths.py` | 7 new tests (below) |
| `.claude/skills/commit/SKILL.md` | Intro: "With paths, the commit contains **only** those files …". Step 1: only these paths; a directory means the changed files under it; either side of a rename commits the rename. Step 2: `others` in the JSON example, plus "Never add them to PATHS". Step 6: the "Left as is" line (at most 10 paths, then "and M more"; no line when empty). Spec line adds PLAN7 |
| `README.md` | Usage: "only these files", and a paragraph on the guarantee and "Left as is". Step 4 of "Each run" mentions the list. Spec line adds PLAN7 |
| `CLAUDE.md` | Spec reference adds PLAN7 |

The selection and the commit commands are unchanged (PROMPT7 #1), as are directories (#2) and
renames (#3).

### Tests

`python3 .claude/skills/commit/test_select_paths.py` → `Ran 37 tests … OK` (30 before + 7).

New:

- `TestOthers`:
  - empty without paths;
  - empty when the given paths cover every change;
  - lists bystanders (modified, deleted, staged);
  - an unselected rename is listed once, by its new name;
  - a directory argument puts the files outside it in `others`;
  - a credential-like **bystander** doesn't stop the run (PLAN7 O5: the rule applies to what's
    committed).
- `TestBystandersEndToEnd.test_only_the_named_file`: name one modified file. The bystanders are a
  modified tracked file, a new staged file and an untracked file. The commit holds only `M a.md`.
  The bystanders' `git status` lines and the modified file's content are the same before and
  after.

PLAN5's guard (the placeholder only on the `Arguments:` line) still passes.

Smoke run in this repo: `select_paths.py -- 03_plans/PLAN7.md` → `stage: [03_plans/PLAN7.md]`, and
the 9 other uncommitted files in `others`.

### Yours to do

- Manual checks in PLAN7 (`/commit <one file>`, `/commit` without paths, `/commit <dir>`, and
  PLAN3's still-open `/commit a.md b.md`). A convenient first one: `/commit 04_results/RESULT7.md`
  on the current tree. It should commit only that file and list everything else under
  "Left as is".
- After the commit: mark PLAN7 `Implemented · Depends-on: PLAN3 · SHA: <sha>` and rebuild
  `03_plans/INDEX.md`. PLAN5 is also still `Confirmed`, although it was implemented in `f870b2b`.

## Items Requiring Confirmation（要確認）

None.
