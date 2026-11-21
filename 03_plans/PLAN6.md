# PLAN6 — `/commit <file>`: commit only the named files

> Status: Superseded · Depends-on: PLAN3 · Superseded by: PLAN7

Source: `02_prompts/PROMPT6.md`. Date: 2026-11-22

Requirement (PROMPT6): 引数としてファイル名が渡された場合には、そのファイルのみを commit する
(when file names are passed as arguments, commit only those files).

Extends [[PLAN3]] (Implemented, `8ad898f`) and [[PLAN5]] (wording, `f870b2b`); replaces neither.

## Finding: the current skill already does this

PLAN3 built path mode to the same rule ("Stage exactly those paths … and make one commit", C3).
`select_paths.py` selects only the given paths, and `SKILL.md` commits with
`git commit --only -- <paths>`, so the commit holds exactly those paths whatever else is in the
index or the worktree.

Checked on 2026-11-22 in a throwaway repo, running the installed skill's script and `SKILL.md`'s
two commands:

| | Before | `/commit a.md` | After |
|---|---|---|---|
| `a.md` | modified | **committed** (`M a.md`, the only entry) | clean |
| `b.md` | modified, not staged | — | still modified |
| `c.md` | new, staged | — | still staged |
| `d.md` | untracked | — | still untracked |

Already covered by tests: `test_exact_paths_only` (selection) and
`test_other_staged_change_stays_staged` (the commit). There's no test with *unstaged* and
*untracked* bystanders, and `SKILL.md` / `README.md` don't say "only" in so many words.

So this PLAN can't add the behavior; it can only make the guarantee explicit and tested, unless
PROMPT6 means something the current behavior doesn't cover (要確認 #1).

## Proposed change (if 要確認 #1 is (a))

No change to the selection or the commit commands. Changes:

1. **`SKILL.md`:**
   - Intro: "With paths, the commit contains **only** those files. Every other change (modified,
     staged or untracked) is left exactly as it was."
   - Step 1, the "Typed" bullet: the same sentence, short form.
   - Step 6: the report line from 要確認 #4, if adopted.
   - Spec line adds `03_plans/PLAN6.md`.
2. **`test_select_paths.py`:** an end-to-end test like the check above. Name one file, with one
   modified, one staged and one untracked bystander. The commit holds only the named file, and
   `git status` for the other three is unchanged. Tests for 要確認 #2–#4 as decided.
3. **`README.md`:** the usage line for `/commit <paths>` says "only these files; everything else
   stays as it is". Spec line adds PLAN6.
4. **`CLAUDE.md`:** spec reference adds PLAN6.

## Implementation steps

1. Edit `SKILL.md` (Edit/Write; Bash can't write `.claude/skills/` here).
2. Add the tests; change `select_paths.py` only if #2–#4 require it; run
   `python3 .claude/skills/commit/test_select_paths.py`.
3. Update `README.md` and `CLAUDE.md`.
4. Write the RESULT for the implementing prompt; mark PLAN6 `Implemented · SHA: …` after the commit.

## Verification

- [ ] Tests pass, including the new bystander test.
- [ ] Manual: in a repo with several changes, `/commit <one file>` → the report and
      `git show --stat HEAD` list only that file; `git status` still shows the others.
- [ ] Manual: the cases decided in 要確認 #2–#4 behave as decided.

## Items Requiring Confirmation（要確認）

1. **What PROMPT6 should change, given the behavior already exists.**
   - (a) No behavior change. Make "only those files" explicit in `SKILL.md` / `README.md` and add
     the bystander test (the proposed change above).
   - (b) You saw `/commit <file>` commit more than that file. Then please give the command and
     what it committed: that would be a bug, and the plan becomes a fix.
   - (c) You meant something else by "そのファイルのみ" (for example, refuse directories; see #2).

   Recommendation: (a), unless (b) happened. Every `/commit` run so far was without arguments, so
   path mode hasn't been tried by hand yet (PLAN3's manual check `/commit a.md b.md` is still
   open).
2. **Directories as arguments.** Today `/commit docs` commits the changed files under `docs/`
   (accepted in RESULT4 #2). PROMPT6 says file names ("ファイル名").
   - (a) Keep it. A directory stands for the changed files under it, as with `git add -- docs`.
   - (b) Files only: a directory argument stops the run (exit 4, "a directory, not a file").

   Recommendation: (a). It's what git does with a path and it's already documented. (b) is safer
   if you want "only what I named, file by file".
3. **Renames.** If `new.md` is a rename of `old.md`, `/commit new.md` (or `old.md`) commits both
   sides, so the commit records a rename (`old.md → new.md`), not a new file plus a leftover
   deletion.
   - (a) Keep both sides. It's one change, and the report shows it as `old → new`.
   - (b) Only the named side. The other half (the deletion or the add) stays uncommitted.

   Recommendation: (a). (b) leaves the repo half-renamed.
4. **Show what was left out.** Add a report line such as "Left as is: 3 other changes (`b.md`,
   `c.md`, `d.md`)" in path mode, so you can see at a glance that only your files went in.
   `select_paths.py` would add an `others` list to its JSON.
   - (a) Yes, list up to 10 paths, then "and N more".
   - (b) Count only.
   - (c) No line.

   Recommendation: (a). It makes the "only" visible on every run, at little cost.
