# PLAN7 — `/commit <file>`: commit only the named files, and show what was left out

> Status: Confirmed · Depends-on: PLAN3

Source: `02_prompts/PROMPT7.md` (answers to the 要確認 in [[PLAN6]]). Date: 2026-11-22

Replaces [[PLAN6]] (PLAN6 is marked `Superseded by: PLAN7`). Requirement from PROMPT6:
引数としてファイル名が渡された場合には、そのファイルのみを commit する (when file names are passed as
arguments, commit only those files). Extends [[PLAN3]] (Implemented, `8ad898f`) and [[PLAN5]]
(wording, `f870b2b`); replaces neither. This file is self-contained: you don't need to read PLAN6
to implement it.

## Decisions

From PROMPT7 ("I take all suggestions"), on PLAN6's 要確認:

| # | Topic | Decision |
|---|---|---|
| 1 | What PROMPT6 should change | (a) No change to selection or commit. Make "only those files" explicit in `SKILL.md` / `README.md`, and add a bystander test |
| 2 | Directories as arguments | (a) Keep: a directory stands for the changed files under it, as with `git add -- <dir>` |
| 3 | Renames | (a) Keep both sides: naming either side commits the rename (`old → new`) |
| 4 | Show what was left out | (a) In path mode, report "Left as is: N other changes (…)", listing up to 10 paths, then "and N more". `select_paths.py` adds `others` to its JSON |

## Background: the behavior already exists

PLAN3's path mode selects only the given paths (`select_paths.py`), and `SKILL.md` commits with
`git commit --only -- <paths>`. So the commit holds exactly those paths, whatever else is in the
index or the worktree. Checked on 2026-11-22 in a throwaway repo:

| | Before | `/commit a.md` | After |
|---|---|---|---|
| `a.md` | modified | **committed** (the only entry) | clean |
| `b.md` | modified, not staged | — | still modified |
| `c.md` | new, staged | — | still staged |
| `d.md` | untracked | — | still untracked |

This PLAN states that guarantee, tests it, and makes it visible in every report (decision 4).

## Requirements

| # | Requirement |
|---|---|
| O1 | With paths, the commit contains only the named files (plus, for a directory, the changed files under it; for a rename, both sides). Unchanged from PLAN3 |
| O2 | Every other change (modified, staged, untracked, deleted) is left exactly as it was: same content, same index state |
| O3 | In path mode, the report lists the changes left out (up to 10 paths, then "and N more"). No line when there are none |
| O4 | Without paths, nothing is left out (`others` is empty) and the report has no such line |
| O5 | Listing a left-out path shows its **name only**; this doesn't change the credential rule, which only applies to paths being committed |

## Design

### `select_paths.py`: the `others` field

- New JSON field `others`: the status entries **not** selected, in `git status` order, as paths
  relative to `root`. For a rename that isn't selected, the new path. Each path appears once.
- No-path mode: `others` is always `[]`.
- Path mode: computed after selection, from the same `git status --porcelain=v1 -z
  --untracked-files=all` output (ignored files never appear).
- No new git calls, exit codes unchanged. `others` is only in the JSON of exit 0.

JSON example:

```json
{"root": "/abs/repo", "branch": "main", "upstream": "origin/main", "remotes": ["origin"],
 "stage": ["a.md"], "renamed_from": [], "deleted": [], "skipped_unchanged": [],
 "others": ["b.md", "c.md", "d.md"]}
```

### `SKILL.md`

1. **Intro**, after the first paragraph: "With paths, the commit contains **only** those files.
   Every other change (modified, staged or untracked) is left exactly as it was."
2. **Step 1, "Typed" bullet**, add: "Only these paths are committed. A directory means the changed
   files under it; naming either side of a rename commits the rename."
3. **Step 2, JSON example**: add `"others": ["…"]`.
4. **Step 6, report**, after "Skipped (unchanged)":
   - **Left as is:** when `others` isn't empty: "N other changes, not committed: `b.md`, `c.md`, …".
     List at most 10 paths, then "and M more".
5. **Spec line**: `03_plans/PLAN3.md` + `03_plans/PLAN5.md` (wording) + `03_plans/PLAN7.md`
   (only the named files).

The `Arguments:` line stays the only place with the placeholder (PLAN5's guard test).

### `README.md`

- Usage: `/commit <paths>` → "only these files; every other change stays as it is (listed under
  'Left as is')".
- Step 4 of "Each run": the report lists the changes left out.
- Spec line adds PLAN7.

### `CLAUDE.md`

- Spec reference adds PLAN7.

## Implementation steps

1. `select_paths.py`: add `others`.
2. `test_select_paths.py`, new tests:
   - **Bystanders, end to end:** name one modified file. Also present: a modified, a staged and an
     untracked file. The commit holds only the named file. `git status --porcelain` for the other
     three is the same before and after. `others` lists the three.
   - `others` is `[]` without paths, and when the given paths cover every change.
   - A rename that isn't selected appears once in `others`, under its new name.
   - A directory argument: the files outside it are in `others`.
3. `SKILL.md` (Edit/Write; Bash can't write `.claude/skills/` here), then `README.md` and
   `CLAUDE.md`.
4. Run `python3 .claude/skills/commit/test_select_paths.py` (all tests, including PLAN5's guard).
5. Write the RESULT for the implementing prompt; mark PLAN7 `Implemented · SHA: …` after the commit.

## Verification

- [ ] Tests pass, including the new ones.
- [ ] Manual: in a repo with several changes, `/commit <one file>` → `git show --stat HEAD` lists
      only that file; `git status` still shows the others; the report has "Left as is" with them.
- [ ] Manual: `/commit` with no paths → no "Left as is" line.
- [ ] Manual: `/commit <dir>` → only the changed files under the directory; the rest under
      "Left as is".
- [ ] Manual (from PLAN3, still open): `/commit a.md b.md` → one commit with exactly those two files.

## Items Requiring Confirmation（要確認）

None.
