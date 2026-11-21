---
name: commit
description: Commit the given paths (or, with none, all new, updated and deleted files) in one Conventional Commit on the current branch. Never pushes, never stages credential-like files.
argument-hint: "[<path> …]"
disable-model-invocation: true
---

# /commit

Make **one** commit on the current branch with exactly the given paths, or, with no paths, every
new, updated and deleted file. Write a Conventional Commits message, and suggest a push command
the user can run. **Never push.**

The skill lives in the commit project (`.claude/skills/commit/`) and is exposed globally by the
symlink `~/.claude-personal/skills/commit`. Spec: that project's `03_plans/PLAN3.md`.

Arguments: `$ARGUMENTS`

## Never

- `git push` (of any kind), and never offer to push.
- `--no-verify`, `--amend`, `git reset`, `git restore --staged`, `git add -f`.
- `git add -A`, `git add .`, `git commit -a`. Staging is always by explicit path.
- Open, `cat`, `diff` or print a credential-like file. Step 2 stops before that can happen.
- Ask for confirmation. Typing `/commit` (or running `/prompt --commit`) is the request.

## Procedure

### 1. Inputs

- **Typed as `/commit …`:** every word in the arguments above is a path (a leading `@` is fine).
  There are no options; in particular no `-m`. No words means "all new, updated and deleted files".
- **Followed from another skill** (e.g. `/prompt --commit` read this file): the arguments line
  above is not filled in. Use the file list and the suggested subject that skill gave you instead,
  and ignore `$ARGUMENTS`.

Pass a path that contains spaces as one argument (quote it).

### 2. Select

Run, in the current directory:

```
python3 ~/.claude-personal/skills/commit/select_paths.py -- <path> …
```

(with no paths: `python3 ~/.claude-personal/skills/commit/select_paths.py`)

| Exit | Meaning | What to do |
|---|---|---|
| 0 | stdout is JSON (below) | Continue |
| 1 | Not a git repository / usage error | Report it (stderr) in one line; stop |
| 2 | A credential-like path would be included | Report the paths from stderr; say nothing was staged or committed; stop |
| 3 | Nothing to commit | Report it in one line; stop |
| 4 | A given path doesn't exist and isn't tracked, is ignored, or is outside the repo | Report stderr's lines; say nothing was committed; stop |
| 5 | Detached HEAD | Report it in one line; stop |

The JSON (paths relative to `root`):

```json
{"root": "/abs/repo", "branch": "main", "upstream": "origin/main", "remotes": ["origin"],
 "stage": ["…"], "renamed_from": ["…"], "deleted": ["…"], "skipped_unchanged": ["…"]}
```

From here on, **PATHS** = `stage` + `renamed_from` + `deleted`, in that order.

### 3. Look at the change

```
git -C <root> diff HEAD --stat -- <PATHS>
```

For new files (untracked, so not in that diff) the file names are usually enough; read one only
if you need it to name the change. Read a diff (`git -C <root> diff HEAD -- <path>`) only for
files whose kind of change you can't tell from the name and the stat. In a repository with no
commits yet, skip the diff and use the file names.

### 4. Message

- **Project rules first.** If the project's `CLAUDE.md` has commit conventions (language, scope,
  types, format), follow them; they override the defaults below.
- **Subject:** `<type>: <summary>`, imperative mood, at most 72 characters, no trailing period.
  Defaults: English, no scope.
- **Type:**
  - `docs:` when every path is documentation: prompts, PLANs, RESULTs, `INDEX.md`, `README.md`,
    `CLAUDE.md`, other Markdown.
  - Otherwise the type of the main change: `feat:` (new behavior), `fix:` (bug fix), `refactor:`,
    `test:` (tests only), `chore:` (config, scaffolding, housekeeping).
- **Suggested subject** (from a calling skill): use it as-is if it follows these rules; otherwise
  adjust it and say so in the report.
- **Body:** only when it adds information the subject can't hold. Wrap at 72.
- **Attribution:** end with the commit attribution lines from this session's instructions, if
  there are any. Never invent them.

Write the message to a new file under `$TMPDIR` (e.g. `$TMPDIR/commit-msg.txt`), not into the
repository.

### 5. Commit

```
git -C <root> add -- <PATHS>
git -C <root> commit --only -F <message file> -- <PATHS>
```

Quote every path. `--only` makes the commit contain exactly PATHS: anything the user had already
staged for other paths stays staged and out of this commit. `git add -- <deleted path>` stages the
deletion; listing both sides of a rename records the rename.

If either command fails (a pre-commit hook, for example): report git's output, say that PATHS are
left staged and nothing was committed, and stop. Don't retry, don't unstage, don't change the
files.

### 6. Report

On success:

```
<short SHA> <subject>
```

then:

- **Committed:** the `stage` paths (renames as `old → new`).
- **Deleted:** the `deleted` paths, if any.
- **Skipped (unchanged):** `skipped_unchanged`, if any.
- If you adjusted a suggested subject, the original and why.
- **Push hint**, from `upstream`, `remotes` and `branch`:

| State | Line |
|---|---|
| `upstream` is set | `! git push` |
| No upstream; `origin` in `remotes` | `! git push -u origin <branch>` |
| No upstream; exactly one remote, not `origin` | `! git push -u <that remote> <branch>` |
| No upstream; several remotes, none `origin` | "No upstream for `<branch>`. Remotes: `a`, `b`." and `! git push -u <remote> <branch>` (the user picks `<remote>`) |
| `remotes` is empty | "No remote configured; nothing to push to." No command |

When there's no commit, the report is the one line from step 2 or 5 saying why.
