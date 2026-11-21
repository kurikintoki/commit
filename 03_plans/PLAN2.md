# PLAN2 — `/commit` skill: commit given paths (or all changes) in one Conventional Commit

> Status: Draft

Source: `02_prompts/PROMPT2.md` (answers to the 要確認 in [[PLAN]]). Date: 2026-11-21

Replaces [[PLAN]] (PLAN is marked `Superseded by: PLAN2`). Input to PLAN: the prompt project's
`03_plans/PLAN15.md` (Superseded) and `03_plans/PLAN16.md` (Confirmed). PLAN16 fixes the
**interface** of `/commit` that `/prompt --commit` relies on and leaves the rest to "its own PLAN
there". This is that PLAN. It is self-contained: you don't need to read PLAN, PLAN15 or PLAN16 to
implement it. The `/prompt` side of PLAN16 (the `--commit` option, the snapshot, the mixed-file
check) is implemented in the prompt project, not here.

## Goal

- `/commit [<path> …]` commits exactly the given paths, or, with no paths, all new, updated and
  deleted files, in **one** commit with a Conventional Commits message, on the current branch.
- It never pushes and never stages credential-like files.
- `/prompt --commit` uses it by reading `~/.claude-personal/skills/commit/SKILL.md` and following
  it with the run's file list and a suggested subject. So the SKILL.md must work both when the
  user types `/commit` and when another skill follows it.

## Decisions

From PROMPT2 ("I take all recommendations"), on PLAN's 要確認:

| # | Topic | Decision |
|---|---|---|
| 1 | Helper script or SKILL.md only | (a) `select_paths.py` decides what to stage and runs the checks; SKILL.md runs `add` / `commit` |
| 2 | Path mode when other changes are already staged | (a) `git commit --only -- <paths>`: only the given paths are committed; other staged changes stay staged |
| 3 | Edge cases | (a) Unchanged tracked path → skipped and listed. Missing untracked path, ignored path, detached HEAD → stop, commit nothing |
| 4 | Credential-like patterns | (i) Also block `credentials*.json` and `.claude/settings.local.json`. (ii) `.env.example` / `.env.sample` stay blocked by `.env*` |
| 5 | Subject option for typed use | (a) No `-m` option in this version |
| 6 | Start `/plan-index` here | (a) Yes: `03_plans/INDEX.md` is built with this PLAN |
| 7 | No-path mode and deleted files | (a) Include deletions, listed separately in the report |

## Fixed by PLAN16 (not re-decided here)

| Topic | Behavior | PLAN16 source |
|---|---|---|
| With paths | Stage exactly those paths (`git add -- <path> …`) and make one commit | Interface table |
| Without paths | All new and updated files in `git status --porcelain`, minus ignored files, listed in the report (deletions too: decision 7) | Decision 5 (PROMPT16 #5) |
| Credential-like files | Never staged. If one would be included, **stop** and report it (nothing is committed) | Interface table; managed policy rule 1 |
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
| C3 | Path mode commits only the given paths, even if other changes are staged (decision 2) |
| C4 | The credential check looks at **path names only**; it never opens or prints a file's content (managed policy rule 1) |
| C5 | Untracked directories are expanded to files (`--untracked-files=all`), so a credential-like file inside a new directory is caught |
| C6 | Renames list both the old and the new path, so the commit records the rename |
| C7 | The report gives: the short SHA and subject, the committed files (deletions listed separately), anything skipped and why, and the push hint (要確認 #1). Or, when there's no commit, one line saying why |
| C8 | Works the same when typed as `/commit …` and when followed from `/prompt --commit` |
| C9 | A typo'd, ignored or missing path never produces a partial commit (decision 3) |

## Design

### Project layout (this repo)

```
.claude/skills/commit/
  SKILL.md               # the procedure (live global copy via the symlink)
  select_paths.py        # decides what to stage; never runs add/commit (decision 1)
  test_select_paths.py   # unittest, builds throwaway git repos under $TMPDIR
```

Python 3.9+, standard library only, like the other skills. Exposed by the symlink
`~/.claude-personal/skills/commit → <this repo>/.claude/skills/commit` (created by you).

### Frontmatter

```yaml
---
name: commit
description: Commit the given paths (or, with none, all new, updated and deleted files) in one Conventional Commit on the current branch. Never pushes, never stages credential-like files.
argument-hint: "[<path> …]"
disable-model-invocation: true
---
```

No `-m` / subject option (decision 5). Any word in `$ARGUMENTS` is a path.

### `select_paths.py`

```
python3 ~/.claude-personal/skills/commit/select_paths.py [<path> …]
```

- Runs in the current directory. Strips a leading `@` from each path (as `/prompt` does).
- Reads `git rev-parse --show-toplevel`, `git symbolic-ref --short -q HEAD` and
  `git status --porcelain=v1 -z --untracked-files=all`. Never runs `add` or `commit`.
- **No paths:** every entry in the status: new, modified, renamed, and deleted (decision 7).
  Ignored files never appear (`git status` leaves them out).
- **Paths:** each path is resolved against CWD, made relative to the repo root, and matched with
  the status entries (decision 3):

  | Given path | Result |
  |---|---|
  | Has a change (new / modified / renamed / deleted) | Selected |
  | Tracked, no change | `skipped_unchanged`; not an error |
  | Doesn't exist and isn't tracked (typo) | Exit 4 |
  | Ignored (`git check-ignore`) | Exit 4 (never `git add -f`) |
  | All given paths unchanged | Exit 3 |

- **Credential patterns** (decision 4), checked on every selected path (both sides of a rename),
  by name only (C4). Matched against the basename, or any directory component where marked `/`:

  | Kind | Patterns |
  |---|---|
  | Env files | `.env`, `.env.*` (includes `.env.example`, `.env.sample`) |
  | Keys and certificates | `*.pem`, `*.key`, `*.pfx`, `*.p12`, `*.ppk`, `id_rsa*`, `id_ed25519*`, `id_ecdsa*` |
  | Credential files | `.netrc`, `.pgpass`, `credentials*.json`, `.claude/settings.local.json` (this one by path suffix) |
  | Directories | `secrets/`, `credentials/`, `.ssh/`, `.aws/`, `.gnupg/`, `.kube/`, `.docker/` |

  Any hit → exit 2, nothing else printed on stdout; stderr lists the matching paths. The whole
  invocation stops, even in no-path mode (PLAN16: "stop and report").
- **Detached HEAD** → exit 5.
- Prints JSON on stdout (robust with spaces in paths). Paths are relative to `root`:

  ```json
  {"root": "/abs/repo", "branch": "main",
   "stage": ["03_plans/PLAN2.md", "02_prompts/PROMPT2.md"],
   "renamed_from": [], "deleted": [], "skipped_unchanged": []}
  ```

  (Fields for the push hint are added per 要確認 #1.)

| Exit | Meaning | SKILL.md does |
|---|---|---|
| 0 | JSON on stdout | Continue |
| 1 | Not a git repository / usage error | Report it; stop |
| 2 | A credential-like path would be included (stderr lists them) | Report the paths; stop, commit nothing |
| 3 | Nothing to commit | Report it; stop |
| 4 | A given path doesn't exist and isn't tracked, or is ignored | Report it; stop, commit nothing |
| 5 | Detached HEAD (no current branch) | Report it; stop |

### `SKILL.md` procedure

1. **Inputs.** Typed: paths from `$ARGUMENTS`. Followed from another skill (`/prompt --commit`):
   the file list and suggested subject that skill passes; `$ARGUMENTS` isn't substituted in that
   case, so the SKILL.md says to use the caller's list instead.
2. **Select.** Run `select_paths.py` with the paths; act on its exit code (table above).
3. **Look at the change.** `git -C <root> diff HEAD --stat -- <paths>` (and the diff of small
   files) to choose the type and write the subject. Credential-like files never get here, because
   step 2 has already stopped on them.
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
   staged; that other change stays staged (decision 2). `git add -- <deleted path>` stages the
   deletion.
   If the commit fails, report git's output and stop. Don't retry, don't unstage, no
   `--no-verify` / `--amend` / `reset`. (The paths stay staged; the report says so.)
6. **Report** (C7): `abc1234 docs: add PROMPT2 and PLAN2`, the committed files, the deleted files,
   skipped files, and the push hint (要確認 #1). Never push, and never offer to.

No step asks for confirmation: typing `/commit` (or `/prompt --commit`) is the request. The file
list is in the report.

### Docs

- `README.md`: what `/commit` does, usage, what is never staged (the pattern table), install (the
  symlink), and that `/prompt --commit` uses it.
- `CLAUDE.md`: fill in Overview / How to run (test command) / Conventions (SKILL.md is the live
  global copy; Bash can't write `.claude/skills/` here, so skill files are edited with Edit/Write;
  scripts stdlib-only, exit codes kept in sync with SKILL.md and tests; Conventional Commits;
  PLANs managed with `/plan-index`).

### Plan index (decision 6)

`03_plans/INDEX.md` is generated with this PLAN by
`python3 ~/.claude/skills/plan-index/build_index.py 03_plans`, and rebuilt after every PLAN change
from now on.

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

- [ ] No paths: new, modified, renamed and deleted files are selected; ignored files aren't.
- [ ] A new directory with a file inside → the file is listed (not the directory).
- [ ] `.env`, `.env.example`, `a/server.key`, `certs/x.pem`, `id_rsa.pub`, `credentials.json`,
      `credentials-prod.json`, `.claude/settings.local.json`, `secrets/x.txt` → exit 2, stderr
      names them.
- [ ] A rename whose old name is credential-like → exit 2.
- [ ] Paths with spaces round-trip through the JSON.
- [ ] Given paths: an unchanged tracked path → `skipped_unchanged`; all unchanged → exit 3.
- [ ] A missing untracked path / an ignored path → exit 4.
- [ ] A given deleted path → in `deleted`.
- [ ] Detached HEAD → exit 5. Outside a repo → exit 1.
- [ ] `@path` is accepted.

Manual (yours, in a scratch repo):

- [ ] `/commit a.md b.md` → one commit with exactly those two files; push hint shown, nothing pushed.
- [ ] `/commit` with no paths → all new, updated and deleted files, listed in the report.
- [ ] Another file staged beforehand + `/commit a.md` → commit has only `a.md`; the other stays staged.
- [ ] A `.env` among the changes → nothing staged or committed; it's named in the report.
- [ ] `/commit typo.md` → stops; nothing committed.
- [ ] A pre-commit hook rejects the commit → error reported, no `--no-verify`, no retry.
- [ ] A project `CLAUDE.md` with its own commit convention → the message follows it.
- [ ] A repo without a remote → the report doesn't suggest pushing to `origin` (要確認 #1).
- [ ] `/prompt --commit` (after PLAN16 is implemented in the prompt project) → one commit with the
      run's files, subject as suggested by `/prompt`.

## Items Requiring Confirmation（要確認）

1. **The push hint in the report (new).** PLAN16 has the report show `! git push origin <branch>`.
   In this repo that failed after the first commit, because no `origin` existed yet
   (`fatal: 'origin' does not appear to be a git repository`). Options:
   - (a) Choose the hint from the repo's state: the branch has an upstream → `! git push`; no
     upstream but a remote exists → `! git push -u <remote> <branch>` (`origin` if present,
     otherwise the only remote); no remote → "No remote configured; nothing to push to" and no
     command. `select_paths.py` adds `"upstream"` and `"remotes"` to its JSON.
   - (b) Always `! git push origin <branch>`, as PLAN16 says.

   Recommendation: (a). It never suggests a command that can't work. PLAN16's `/prompt` report
   (R7) has the same fixed command; aligning it would be a follow-up in the prompt project, not
   part of this PLAN.
