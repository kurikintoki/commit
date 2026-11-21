# commit

`/commit` is a Claude Code skill that makes **one** commit on the current branch, with exactly the
paths you give it, or, with none, every new, updated and deleted file. It writes a Conventional
Commits message, never pushes, and never stages files that look like credentials.

## Usage

    /commit                          # all new, updated and deleted files
    /commit 02_prompts/PROMPT4.md 03_plans/PLAN4.md   # exactly these paths
    /commit docs                     # the changed files under docs/

Only you can start it (Claude never runs `/commit` on its own). Each run:

1. Works out what to commit (`select_paths.py`) and stops, committing nothing, if:
   - a path looks like a credential file (table below);
   - a path you gave doesn't exist and isn't tracked (a typo), is ignored by git, or is outside
     the repository;
   - HEAD is detached, the folder isn't a git repository, or there's nothing to commit.

   A path you gave that has no changes is skipped and listed; it doesn't stop the run.
2. Writes the message: `<type>: <summary>` (`docs:` when only Markdown changed, otherwise
   `feat:` / `fix:` / `refactor:` / `test:` / `chore:`). The project's `CLAUDE.md` commit
   conventions win. Attribution lines come from the session's instructions.
3. Commits with `git add -- <paths>` and `git commit --only -- <paths>`. Anything you had already
   staged for other files stays staged and out of the commit.
4. Reports the short SHA, subject and files, plus a push command you can run, chosen from the repo's
   state:

   | Repo | Suggested |
   |---|---|
   | Branch tracks a remote branch | `! git push` |
   | `origin` exists, no upstream yet | `! git push -u origin <branch>` |
   | One other remote, no upstream | `! git push -u <remote> <branch>` |
   | Several remotes, none `origin` | the list, and `<remote>` for you to fill in |
   | No remote | "No remote configured", no command |

It never pushes, never uses `--no-verify` / `--amend` / `reset` / `git add -A` / `commit -a`, and
never asks for confirmation (running it is the request). If a pre-commit hook rejects the commit,
it shows git's error and leaves the files staged.

### Never staged

Matched on the path name only; file contents are never read.

| Kind | Patterns |
|---|---|
| Env files | `.env`, `.env.*` (including `.env.example`) |
| Keys and certificates | `*.pem`, `*.key`, `*.pfx`, `*.p12`, `*.ppk`, `id_rsa*`, `id_ed25519*`, `id_ecdsa*` |
| Credential files | `.netrc`, `.pgpass`, `credentials*.json`, `.claude/settings.local.json` |
| Directories | `secrets/`, `credentials/`, `.ssh/`, `.aws/`, `.gnupg/`, `.kube/`, `.docker/` |

If one of these would be included, nothing is committed. Commit such a file by hand with git if
you really mean to.

### With `/prompt`

`/prompt --commit` (the prompt project's PLAN16) reads this skill's `SKILL.md` and follows it with
the run's files and a suggested subject. Without `/commit` installed, `/prompt --commit` says so
and doesn't commit.

## Install

The skill lives in `.claude/skills/commit/`. Expose it to every project with a symlink:

    ln -s "$PWD/.claude/skills/commit" ~/.claude-personal/skills/commit

## Files

| File | Role |
|---|---|
| `.claude/skills/commit/SKILL.md` | The procedure Claude follows |
| `.claude/skills/commit/select_paths.py` | Picks and checks the paths; prints JSON. Never runs add, commit or push |
| `.claude/skills/commit/test_select_paths.py` | Tests (throwaway git repos under `$TMPDIR`) |

Test: `python3 .claude/skills/commit/test_select_paths.py`

Spec: [`03_plans/PLAN3.md`](03_plans/PLAN3.md) (index: [`03_plans/INDEX.md`](03_plans/INDEX.md)).
