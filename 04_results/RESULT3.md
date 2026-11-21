# RESULT3 — Implement PLAN3: the `/commit` skill

Source: chat instruction "implement @03_plans/PLAN3.md and write results in RESULT3.md" (no prompt
file). Date: 2026-11-21

## Task

Implement [[PLAN3]] (Confirmed): the `/commit` skill with `select_paths.py`, its tests, `SKILL.md`,
and the docs (`README.md`, `CLAUDE.md`).

## Result

### Files

| File | Change |
|---|---|
| `.claude/skills/commit/select_paths.py` | New. Picks the paths and checks them; prints JSON; exit codes 0–5 as in PLAN3. Read-only git calls only (`rev-parse`, `symbolic-ref`, `status -z --untracked-files=all`, `check-ignore`, `ls-files`, `remote`) |
| `.claude/skills/commit/test_select_paths.py` | New. 29 tests in throwaway repos under `$TMPDIR`, including end-to-end runs of SKILL.md's `git add` / `git commit --only` commands |
| `.claude/skills/commit/SKILL.md` | New. Frontmatter as in PLAN3 (`disable-model-invocation: true`, `argument-hint: "[<path> …]"`), the "Never" list, procedure steps 1–6, the push-hint table |
| `README.md` | Written from the scaffold placeholder: usage, stop conditions, the never-staged table, push hints, `/prompt --commit`, install, files |
| `CLAUDE.md` | Filled in Overview / How to run / Conventions (live global copy, exit codes, test isolation, sandbox limits, Conventional Commits) |

PLAN3 isn't marked `Implemented` yet: that needs the SHA of the commit that contains this work
(PLAN3, step 6).

### Tests

`python3 .claude/skills/commit/test_select_paths.py` → `Ran 29 tests … OK`.

They cover PLAN3's automated checklist: new / modified / renamed / deleted files, ignored files left
out, untracked directories expanded, credential patterns (unit test per pattern plus end-to-end
stops), a rename from a credential-like name, spaces in paths, unchanged → `skipped_unchanged`,
all unchanged → 3, typo / ignored / outside-repo path → 4, given deleted path, detached HEAD → 5,
not a repo → 1, `@path`, and `upstream` / `remotes` with no remote, a remote without upstream, and
after `push -u` to a local bare repo. Also checked:

- `git commit --only -- <paths>` leaves another file's staged change staged and out of the commit
  (PLAN3 C3).
- Renames, deletions and spaces commit cleanly with the documented commands, and the tree is clean
  afterwards.
- `--only` works for the first commit in a new repository.

Smoke run in this repo: no paths → JSON with the three new skill files, `"upstream": "origin/main"`;
`-- typo.md README.md` → exit 4, `typo.md: doesn't exist and isn't tracked`.

### Details settled during implementation (within PLAN3)

- **A directory path** means the changed files under it (what `git add -- <dir>` would stage).
  The credential check runs on each of those files.
- **`--`** ends the paths-only check, so a file named `-x` can be given (`-- -x`). Any other word
  starting with `-` is a usage error (exit 1): there's no `-m` (PROMPT2 #5).
- **Deleted credential-like files** also stop the run. PLAN3 says "every selected path"; it doesn't
  carve out deletions.
- **`AD`** status (added to the index, then deleted from the worktree) is left out: there's
  nothing to commit for it.
- Order of checks: not a repo (1) → detached HEAD (5) → path problems (4) → credential (2) →
  nothing to commit (3).

### Problems hit (and what was done)

1. **The sandbox blocks deleting files with credential-like names.** The first version of the
   end-to-end tests created `.env`, `server.key` and `id_rsa` fixtures. The tests passed, but
   `TemporaryDirectory` cleanup failed. Python 3.9 retries `chmod` on a `PermissionError`, which
   ends in a `RecursionError`. Fix: the end-to-end fixtures now use names that the script blocks
   but the sandbox lets a test delete (`credentials*.json`, `.claude/settings.local.json`,
   `.kube/`, `id_ed25519.pub`). Every pattern is still unit-tested by name. Noted in `CLAUDE.md`.
2. **The user's global git ignore file** (`~/.config/git/ignore`) hid
   `.claude/settings.local.json` inside the test repos. The script was right (ignored files are
   left out), but the tests weren't isolated. Fix: the tests set `XDG_CONFIG_HOME` to a
   nonexistent path, in addition to `GIT_CONFIG_GLOBAL=/dev/null`.
3. **The LY AI Policy hook blocked `rm -rf`** (rule `rm -r…`) while I was cleaning up a diagnostic
   folder. I didn't try another way to delete it. Leftovers are listed under 要確認 #1.

### Yours to do

- Create the symlink:
  `! ln -s "$PWD/.claude/skills/commit" ~/.claude-personal/skills/commit`
- Run PLAN3's manual checks (`/commit` is user-invoked only).
- After the commit: mark PLAN3 `Implemented · SHA: <sha>` and rebuild `03_plans/INDEX.md`.

## Items Requiring Confirmation（要確認）

1. **Leftover temporary folders in `$TMPDIR` (`/tmp/claude-502`)**: `dbg1/`, `sbx/` (my
   diagnostics) and `tmp3y_wbxjs/`, `tmpcquh_xwu/`, `tmphsz5u5_f/`, `tmpjddi3qfp/`,
   `tmpm64_g_75/`, `tmpv38fgn3f/` (from the failed test runs). They hold only fake fixtures (`x`,
   `{}`, `SECRET=1`) with credential-like names. Options: (a) you delete them, e.g.
   `! rm -rf /tmp/claude-502/{dbg1,sbx,tmp3y_wbxjs,tmpcquh_xwu,tmphsz5u5_f,tmpjddi3qfp,tmpm64_g_75,tmpv38fgn3f}`
   / (b) leave them for the OS to clear. (Recommendation: (a). Check the list first. They're
   harmless, but the names look like secrets.)
2. **The details settled during implementation** (above: directory paths, `--`, deleted
   credential-like files stop the run, `AD` left out). Options: (a) accept / (b) change any of them
   in a new PLAN. (Recommendation: (a). Each one follows PLAN3's wording or git's own behavior.)
