# PLAN5 — `/commit`: word `SKILL.md` so the arguments placeholder appears only once

> Status: Confirmed · Depends-on: PLAN3

Source: `02_prompts/PROMPT5.md` (answers to the 要確認 in [[RESULT4]]; the prompt's "RESULR4" is
read as RESULT4, the only RESULT with that item). Date: 2026-11-21

RESULT4's option (a) called this "a small PLAN4". It's PLAN5 because plans are numbered after the
prompt that asks for them (PROMPT5). Extends [[PLAN3]] (Implemented, `8ad898f`); doesn't replace
it.

## Decision

| # | Topic | Decision |
|---|---|---|
| RESULT4 #1 | `SKILL.md`'s arguments wording | (a) A small PLAN that rewords it (PROMPT5 "1. a") |

## Problem

Claude Code replaces **every** `$ARGUMENTS` in a skill's `SKILL.md` with the typed arguments, not
just the one on the `Arguments:` line. `/commit`'s step 1 also names the placeholder:

```
- **Followed from another skill** (e.g. `/prompt --commit` read this file): the arguments line
  above is not filled in. Use the file list and the suggested subject that skill gave you instead,
  and ignore `$ARGUMENTS`.
```

So when you type `/commit`, the sentence is shown as "and ignore ``." (seen on the first run,
`8822bd0`). The sentence matters exactly when another skill follows the file: `/prompt --commit`
reads `SKILL.md` directly, so it sees the raw placeholder, and the text should tell it clearly what
to ignore.

## Change

1. **`SKILL.md` step 1**, the second bullet becomes:

   ```
   - **Followed from another skill** (e.g. `/prompt --commit` read this file): ignore the
     Arguments line above. It is either empty or an unfilled placeholder. Use the file list and
     the suggested subject that skill gave you instead.
   ```

   The placeholder token then appears **once**, on the `Arguments:` line, which is the only place
   it's meant to be filled in.
2. **`SKILL.md` Spec line:** `03_plans/PLAN3.md` → `03_plans/PLAN3.md` + `03_plans/PLAN5.md`
   (wording).
3. **Guard test** in `test_select_paths.py` (so the test command stays the same): `SKILL.md`
   contains the placeholder token exactly once, and that line starts with `Arguments:`.
4. **Docs:** `CLAUDE.md`, add PLAN5 to the spec reference and a convention line: "Write the
   arguments placeholder in `SKILL.md` only on the `Arguments:` line; Claude Code substitutes it
   everywhere." `README.md`, the spec line adds PLAN5.

No behavior change: `select_paths.py`, the procedure's steps and the exit codes stay as they are.

## Implementation steps

1. Edit `.claude/skills/commit/SKILL.md` (step 1 bullet, Spec line) with Edit/Write. Bash can't
   write `.claude/skills/` here.
2. Add the guard test; run `python3 .claude/skills/commit/test_select_paths.py`.
3. Update `CLAUDE.md` and `README.md`.
4. Write the RESULT for the implementing prompt; mark PLAN5 `Implemented · SHA: …` after the commit.

## Verification

- [ ] Tests pass, including the guard: `grep -c 'ARGUMENTS' .claude/skills/commit/SKILL.md` → 1.
- [ ] Manual: type `/commit` in a repo with a change. Step 1's second bullet reads "ignore the
      Arguments line above …", with no empty backticks.
- [ ] Manual (once PLAN16 is implemented in the prompt project): `/prompt --commit` still commits
      the run's files using the list `/prompt` passes.

## Items Requiring Confirmation（要確認）

None.
