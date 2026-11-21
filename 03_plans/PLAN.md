# PLAN — `/commit` skill: commit given paths (or all changes) in one Conventional Commit

> Status: Draft

Source: `02_prompts/PROMPT.md`. Date: 2026-11-21

Input: the prompt project's `03_plans/PLAN15.md` (Superseded) and `03_plans/PLAN16.md`
(Confirmed). PLAN16 fixes the **interface** of `/commit` that `/prompt --commit` relies on and
leaves the rest to "its own PLAN there". This is that PLAN. It is self-contained: you don't need
to read PLAN15/16 to implement it. The `/prompt` side of PLAN16 (the `--commit` option, the
snapshot, the mixed-file check) is implemented in the prompt project, not here.

## Goal

- `/commit [<path> …]` commits exactly the given paths, or, with no paths, all new and updated
  files, in **one** commit with a Conventional Commits message, on the current branch.
- It never pushes and never stages credential-like files.
- `/prompt --commit` uses it by reading `~/.claude-personal/skills/commit/SKILL.md` and following
  it with the run's file list and a suggested subject. So the SKILL.md must work both when the
  user types `/commit` and when another skill follows it.

## Fixed by PLAN16 (not re-decided here)

| Topic | Behavior | PLAN16 source |
|---|---|---|
| With paths | Stage exactly those paths (`git add -- <path> …`) and make one commit | Interface table |
| Without paths | All new and updated files in `git status --porcelain`, minus ignored files, listed in the report | Decision 5 (PROMPT16 #5) |
| Credential-like files (`.env*`, `*.pem`, `*.key`, `id_rsa*` …) | Never staged. If one would be included, **stop** and report it (nothing is committed) | Interface table; managed policy rule 1 |
| Message | Conventional Commits. `docs:` when only prompt/PLAN/RESULT/INDEX files change, otherwise `feat:` / `fix:` / `chore:` …. A subject suggested by the caller is used if it fits. The project's `CLAUDE.md` conventions come first. Attribution lines come from the session's instructions, never hard-coded | Interface table |
| Branch | The current branch, including the default branch | PROMPT15 #3 |
| Never | push, `--no-verify`, `--amend`, `reset`, `git add -A` / `.` / `commit -a` | Interface table |
| Not a git repository / nothing to commit | Report it; do nothing | Interface table |
| Commit fails (e.g. pre-commit hook) | Report git's error; leave the files as they are. No retry with `--no-verify` | Interface table |
| Frontmatter | `disable-model-invocation: true`: Claude never starts `/commit` on its own | Decision 3 (PROMPT16 #3) |
| Location | Its own project (this repo), symlinked into `~/.claude-personal/skills/commit` | Decision 4 (PROMPT16 #4) |

## Requirements

| # | Requirement |
|---|---|
| C1 | One invocation → at most one commit |
| C2 | Staging is always by explicit path (`git add -- <p> …`), quoted (paths may contain spaces) |
| C3 | Path mode commits only the given paths, even if other changes are staged (要確認 #2) |
| C4 | The credential check looks at **path names only**; it never opens or prints a file's content (managed policy rule 1) |
| C5 | Untracked directories are expanded to files (`--untracked-files=all`), so a credential-like file inside a new directory is caught |
| C6 | Renames list both the old and the new path, so the commit records the rename |
| C7 | The report gives: the short SHA and subject, the committed files, anything skipped and why, and `! git push origin <branch>`. Or, when there's no commit, one line saying why |
| C8 | Works the same when typed as `/commit …` and when followed from `/prompt --commit` |

## Design

### Project layout (this repo)

```
.claude/skills/commit/
  SKILL.md               # the procedure (live global copy via the symlink)
  select_paths.py        # decides what to stage; never runs add/commit (要確認 #1)
  test_select_paths.py   # unittest, builds throwaway git repos under $TMPDIR
```

Python 3.9+, standard library only, like the other skills. Exposed by the symlink
`~/.claude-personal/skills/commit → <this repo>/.claude/skills/commit` (created by you).

### Frontmatter

```yaml
---
name: commit
description: Commit the given paths (or, with none, all new and updated files) in one Conventional Commit on the current branch. Never pushes, never stages credential-like files.
argument-hint: "[<path> …]"
disable-model-invocation: true
---
```

### `select_paths.py`

```
python3 ~/.claude-personal/skills/commit/select_paths.py [<path> …]
```

- Runs in the current directory. Strips a leading `@` from each path (as `/prompt` does).
- Reads `git rev-parse --show-toplevel`, `git symbolic-ref --short -q HEAD` and
  `git status --porcelain=v1 -z --untracked-files=all`. Never runs `add` or `commit`.
- **No paths:** every entry in the status (new, modified, renamed; deletions per 要確認 #7).
- **Paths:** each path is resolved against CWD and matched with the status entries
  (edge cases per 要確認 #3).
- Applies the credential patterns (要確認 #4) to every selected path's components.
- Prints JSON on stdout (robust with spaces in paths):

  ```json
  {"root": "/abs/repo", "branch": "main",
   "stage": ["03_plans/PLAN.md", "02_prompts/PROMPT.md"],
   "renamed_from": [], "deleted": [], "skipped_unchanged": []}
  ```

  Paths are relative to `root`.

| Exit | Meaning | SKILL.md does |
|---|---|---|
| 0 | JSON on stdout | Continue |
| 1 | Not a git repository / usage error | Report it; stop |
| 2 | A credential-like path would be included (stderr lists them) | Report the paths; stop, commit nothing |
| 3 | Nothing to commit | Report it; stop |
| 4 | A given path is a problem (doesn't exist and isn't tracked, or is ignored) | Report it; stop |
| 5 | Detached HEAD (no current branch) | Report it; stop |

### `SKILL.md` procedure

1. **Inputs.** Typed: paths from `$ARGUMENTS`. Followed from another skill (`/prompt --commit`):
   the file list and suggested subject that skill passes; `$ARGUMENTS` isn't substituted in that
   case, so the SKILL.md says to use the caller's list instead.
2. **Select.** Run `select_paths.py` with the paths; act on its exit code (table above).
3. **Look at the change.** `git -C <root> diff HEAD --stat -- <paths>` (and `git diff` of small
   files) to choose the type and write the subject. Content of credential-like files is never
   shown, because step 2 has already stopped on them.
4. **Message.**
   - Subject: `<type>: <summary>`, imperative, ≤ 72 characters. The project's `CLAUDE.md`
     conventions win (language, scope, types). Without them: English, no scope.
   - Type: `docs:` if every path is a prompt / PLAN / RESULT / `INDEX.md` / other Markdown doc;
     otherwise the type that fits the main change (`feat:`, `fix:`, `refactor:`, `test:`, `chore:`).
   - A caller's suggested subject is used as-is if it fits these rules; otherwise adjusted, and the
     report says so.
   - Body only when it adds information. Then the attribution lines from the session's
     instructions, if any.
   - Written to a file under `$TMPDIR` and passed with `-F` (no shell quoting issues).
5. **Commit.**

   ```
   git -C <root> add -- <stage…> <renamed_from…> <deleted…>
   git -C <root> commit --only -F <msgfile> -- <same paths>
   ```

   `--only` makes the commit contain exactly these paths even if something else was already
   staged; that other change stays staged (C3, 要確認 #2).
   If the commit fails, report git's output and stop. Don't retry, don't unstage, no
   `--no-verify` / `--amend` / `reset`. (The paths stay staged; the report says so.)
6. **Report** (C7): `abc1234 docs: add PROMPT and PLAN`, the file list, skipped files, and
   `! git push origin <branch>`. Never push, and never offer to.

No step asks for confirmation: typing `/commit` (or `/prompt --commit`) is the request. The file
list is in the report.

### Docs

- `README.md`: what `/commit` does, usage, what is never staged, install (the symlink), and that
  `/prompt --commit` uses it.
- `CLAUDE.md`: fill in Overview / How to run (test command) / Conventions (SKILL.md is the live
  global copy; Bash can't write `.claude/skills/` here, so skill files are edited with Edit/Write;
  scripts stdlib-only, exit codes kept in sync with SKILL.md and tests; Conventional Commits).

## Implementation steps

1. Write `.claude/skills/commit/select_paths.py` and `test_select_paths.py`; run
   `python3 .claude/skills/commit/test_select_paths.py`.
2. Write `.claude/skills/commit/SKILL.md`.
3. Update `README.md` and `CLAUDE.md`.
4. **You:** create the symlink:
   `! ln -s "$PWD/.claude/skills/commit" ~/.claude-personal/skills/commit`
   (the sandbox blocks the agent from writing `~/.claude-personal/skills/`).
5. **You:** the manual checks below (`/commit` is user-invoked only).
6. Write the RESULT for the implementing prompt. Mark this PLAN `Implemented · SHA: …` after the
   commit.

Note: the sandbox in this repo denies Bash writes to `.claude/skills/`; steps 1–2 use the
Edit/Write tools. If those are blocked too, the step stops and reports it (no workaround).

## Verification

Automated (`test_select_paths.py`, throwaway repos):

- [ ] No paths: new, modified and renamed files are selected; ignored files aren't.
- [ ] A new directory with a file inside → the file is listed (not the directory).
- [ ] `.env`, `a/server.key`, `certs/x.pem`, `id_rsa.pub` (and the 要確認 #4 additions) → exit 2.
- [ ] Paths with spaces round-trip through the JSON.
- [ ] Given paths: an unchanged tracked path → `skipped_unchanged`; all unchanged → exit 3.
- [ ] A missing untracked path / an ignored path → exit 4.
- [ ] Detached HEAD → exit 5. Outside a repo → exit 1.
- [ ] `@path` is accepted.

Manual (yours, in a scratch repo):

- [ ] `/commit a.md b.md` → one commit with exactly those two files; push command shown, nothing pushed.
- [ ] `/commit` with no paths → all new and updated files, listed in the report.
- [ ] Another file staged beforehand + `/commit a.md` → commit has only `a.md`; the other stays staged.
- [ ] A `.env` among the changes → nothing staged or committed; it's named in the report.
- [ ] A pre-commit hook rejects the commit → error reported, no `--no-verify`, no retry.
- [ ] A project `CLAUDE.md` with its own commit convention → the message follows it.
- [ ] `/prompt --commit` (after PLAN16 is implemented in the prompt project) → one commit with the
      run's files, subject as suggested by `/prompt`.

## Items Requiring Confirmation（要確認）

1. **Helper script or SKILL.md only?**
   - (a) `select_paths.py` decides what to stage and runs the checks; SKILL.md runs `add`/`commit`.
   - (b) Everything in SKILL.md (the agent parses `git status` itself).
   - (c) A script that also runs `add` and `commit` (message passed as a file).

   Recommendation: (a). Porcelain parsing, renames, untracked directories and the credential
   patterns are where mistakes happen, and a script makes them testable, like your other skills.
   The commit itself is two lines and needs the agent anyway (the message).
2. **Path mode when other changes are already staged.**
   - (a) `git commit --only -- <paths>`: commit just the given paths; the other staged changes stay
     staged.
   - (b) Stop and report the other staged files.
   - (c) Commit them too.

   Recommendation: (a). It's what "stage exactly those paths and make one commit" means, and with
   (b) `/prompt --commit` would refuse whenever you had something unrelated staged.
3. **Edge cases for given paths and the branch.** Proposed:
   - a tracked path with no change → skipped and listed (e.g. a prompt file committed earlier);
   - a path that doesn't exist and isn't tracked (typo) → stop, commit nothing;
   - an ignored path → stop, commit nothing (never `git add -f`);
   - detached HEAD → stop.

   Options: (a) as proposed / (b) skip every problem path and commit the rest.
   Recommendation: (a). A typo shouldn't produce a partial commit; an unchanged path is harmless.
4. **Credential-like patterns.** Base list (from PLAN16 and the managed sandbox rules), matched
   on any path component: `.env`, `.env.*`, `*.pem`, `*.key`, `*.pfx`, `*.p12`, `*.ppk`,
   `id_rsa*`, `id_ed25519*`, `id_ecdsa*`, `.netrc`, `.pgpass`, `secrets/`, `credentials/`,
   `.ssh/`, `.aws/`, `.gnupg/`, `.kube/`, `.docker/`. Open points:
   - (i) Also block `credentials*.json` and `.claude/settings.local.json`? Recommendation: yes
     (both commonly hold tokens).
   - (ii) `.env.example` / `.env.sample`: blocked by `.env*`, or allowed?
     Recommendation: blocked, as PLAN16 says `.env*`; you can still commit it with plain git.
5. **A subject option for typed use** (e.g. `/commit -m "…" <paths>`)? PLAN16's interface has
   none; callers pass a subject in context. Options: (a) no option in this version / (b) add `-m`.
   Recommendation: (a). Keep the interface PLAN16 fixed; add it later if you miss it.
6. **Start `/plan-index` here?** `03_plans/` has no `INDEX.md` yet, so none was built for this
   PLAN. Options: (a) run `build_index.py 03_plans` now / (b) not for this repo.
   Recommendation: (a), as in your other skill projects.
7. **No-path mode and deleted files.** PLAN16 says "new and updated files"; it doesn't mention
   deletions of tracked files.
   - (a) Include deletions (staged with `git add -- <path>`), listed separately in the report.
   - (b) Leave deletions out.

   Recommendation: (a). A deletion is a change; leaving it out leaves the tree dirty and the
   commit inconsistent with what you see. In path mode, a deleted path you name is always
   included.
