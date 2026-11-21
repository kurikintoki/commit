# RESULT4 — Answers to RESULT3's 要確認

Source: `02_prompts/PROMPT4.md` (answers to the 要確認 in [[RESULT3]]). Date: 2026-11-21

## Task

Apply PROMPT4's answers to RESULT3's two 要確認 items: "1. a" (the leftover temporary folders)
and "2. a" (the details settled while implementing PLAN3).

## Result

| # | RESULT3 item | Answer | Outcome |
|---|---|---|---|
| 1 | Leftover temporary folders in `$TMPDIR` | (a) You delete them | Not deleted by the agent: option (a) is your step, and the LY AI Policy hook blocks `rm -r…` for the agent anyway. All eight folders are still there (checked 2026-11-21). The command is below |
| 2 | Details settled during implementation | (a) Accept | Accepted as implemented in `8ad898f`. No code or doc change |

### 1. The command to remove the folders

All eight are under `/tmp/claude-502` and hold only fake fixtures. Look at them first if you like
(`! ls -la /tmp/claude-502/{dbg1,sbx}`), then:

```
! rm -rf /tmp/claude-502/{dbg1,sbx,tmp3y_wbxjs,tmpcquh_xwu,tmphsz5u5_f,tmpjddi3qfp,tmpm64_g_75,tmpv38fgn3f}
```

New ones won't appear: the tests no longer create fixture names that the sandbox can't delete
(RESULT3, problem 1).

### 2. The accepted details (now part of `/commit`'s behavior)

- A directory path means the changed files under it; the credential check runs on each one.
- `--` ends the option check, so a file named `-x` can be given. Any other word starting with
  `-` is a usage error (exit 1).
- Deleting a credential-like file also stops the run.
- `AD` entries (added to the index, then deleted from the worktree) are left out.
- Check order: not a repo (1) → detached HEAD (5) → path problems (4) → credential (2) → nothing
  to commit (3).

They're in `select_paths.py` and covered by `test_select_paths.py`. If one of them is ever changed,
that change starts as a new PLAN (`CLAUDE.md` conventions).

### Status

- PLAN3 is `Implemented · SHA: 8ad898f` (`8822bd0`). That commit hasn't been pushed yet: local
  `main` is 1 ahead of `origin/main`.
- No `TODO.md` in this project, so no `todo.py check`.

## Items Requiring Confirmation（要確認）

1. **Follow-up for `SKILL.md`'s `$ARGUMENTS` wording** (raised in chat after the first `/commit`
   run, not part of PROMPT4). Claude Code replaces every `$ARGUMENTS` in `SKILL.md`, including the
   sentence telling a calling skill to ignore it. That sentence then reads "ignore ``".
   Options: (a) a small PLAN4 that rewords it ("ignore the Arguments line above") / (b) leave it.
   (Recommendation: (a). It's harmless today, but it's confusing exactly when `/prompt --commit`
   follows the file.)
