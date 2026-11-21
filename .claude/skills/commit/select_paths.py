#!/usr/bin/env python3
"""Decide which paths /commit stages, and check them. Never runs add, commit or push.

Usage: select_paths.py [--] [<path> ...]

  No paths: every new, modified, renamed and deleted file in `git status`
            (ignored files never appear there).
  Paths:    exactly those paths (a directory means the changed files under it),
            resolved against the current directory. A leading "@" is stripped.

Prints JSON on stdout (paths relative to "root"):

  {"root": "/abs/repo", "branch": "main", "upstream": "origin/main" | null,
   "remotes": ["origin"], "stage": [...], "renamed_from": [...],
   "deleted": [...], "skipped_unchanged": [...]}

Exit codes:
  0  JSON on stdout
  1  not a git repository / usage error
  2  a credential-like path would be included (stderr lists them; stdout empty)
  3  nothing to commit
  4  a given path doesn't exist and isn't tracked, is ignored, or is outside the repo
  5  detached HEAD (no current branch)

Spec: PLAN3 in the commit project (03_plans/PLAN3.md).
"""
import fnmatch
import json
import os
import subprocess
import sys

USAGE = "usage: select_paths.py [--] [<path> ...]"

# Credential-like names (PLAN3, PROMPT2 #4). Checked on path names only; file
# contents are never opened.
BASENAME_PATTERNS = (
    ".env", ".env.*",
    "*.pem", "*.key", "*.pfx", "*.p12", "*.ppk",
    "id_rsa*", "id_ed25519*", "id_ecdsa*",
    ".netrc", ".pgpass", "credentials*.json",
)
DIR_COMPONENTS = (
    "secrets", "credentials", ".ssh", ".aws", ".gnupg", ".kube", ".docker",
)
PATH_SUFFIXES = (".claude/settings.local.json",)


class Usage(Exception):
    pass


def git(args, cwd):
    """Run git; return (returncode, stdout as str)."""
    proc = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode, proc.stdout.decode("utf-8", "surrogateescape")


def is_credential_like(rel):
    parts = rel.split("/")
    base = parts[-1]
    if any(fnmatch.fnmatchcase(base, pat) for pat in BASENAME_PATTERNS):
        return True
    if any(part in DIR_COMPONENTS for part in parts[:-1]):
        return True
    return any(rel == suf or rel.endswith("/" + suf) for suf in PATH_SUFFIXES)


def parse_status(raw):
    """Parse `git status --porcelain=v1 -z` into a list of entries.

    Each entry: {"path", "orig" (rename source or None), "kind"} where kind is
    "stage", "rename" or "deleted". "AD" (added to the index, then deleted from
    the worktree) has nothing to commit and is left out.
    """
    fields = raw.split("\0")
    entries = []
    i = 0
    while i < len(fields):
        rec = fields[i]
        i += 1
        if len(rec) < 4:
            continue
        x, y, path = rec[0], rec[1], rec[3:]
        orig = None
        if x in "RC" or y in "RC":
            orig = fields[i] if i < len(fields) else None
            i += 1
        if x == "!":
            continue
        if x == "A" and y == "D":
            continue
        if x == "R" or y == "R":
            kind = "rename"
        elif x == "D" or y == "D":
            kind = "deleted"
        else:
            # ??, M, A, T, C (copy: the source is unchanged), unmerged states
            kind = "stage"
            orig = None
        entries.append({"path": path, "orig": orig, "kind": kind})
    return entries


def parse_args(argv):
    paths = []
    after_dashdash = False
    for arg in argv:
        if not after_dashdash and arg == "--":
            after_dashdash = True
            continue
        if not after_dashdash and arg.startswith("-"):
            raise Usage("unknown option: %s" % arg)
        if arg.startswith("@"):
            arg = arg[1:]
        if not arg:
            raise Usage("empty path")
        paths.append(arg)
    return paths


def to_repo_rel(path, cwd, root):
    """Path relative to root with "/" separators, or None if outside the repo."""
    absolute = os.path.realpath(os.path.join(cwd, path))
    rel = os.path.relpath(absolute, root)
    if rel == os.curdir:
        return ""
    if rel == os.pardir or rel.startswith(os.pardir + os.sep):
        return None
    return rel.replace(os.sep, "/")


def select_given(paths, entries, cwd, root):
    """Return (selected entries, skipped_unchanged, problems)."""
    selected = []
    skipped = []
    problems = []
    for given in paths:
        rel = to_repo_rel(given, cwd, root)
        if rel is None:
            problems.append("%s: outside the repository" % given)
            continue

        def under(p):
            return rel == "" or p == rel or p.startswith(rel + "/")

        hits = [e for e in entries if under(e["path"]) or (e["orig"] and under(e["orig"]))]
        if hits:
            selected.extend(hits)
            continue
        if git(["check-ignore", "-q", "--", rel or "."], root)[0] == 0:
            problems.append("%s: ignored by git (never force-added)" % given)
        elif git(["ls-files", "--error-unmatch", "--", rel or "."], root)[0] == 0:
            skipped.append(rel or ".")
        elif os.path.lexists(os.path.join(root, rel)):
            problems.append("%s: untracked, with nothing to add" % given)
        else:
            problems.append("%s: doesn't exist and isn't tracked" % given)
    return selected, skipped, problems


def main(argv):
    try:
        paths = parse_args(argv)
    except Usage as exc:
        print(str(exc), file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    cwd = os.getcwd()
    rc, out = git(["rev-parse", "--show-toplevel"], cwd)
    if rc != 0:
        print("not a git repository: %s" % cwd, file=sys.stderr)
        return 1
    root = os.path.realpath(out.strip())

    rc, out = git(["symbolic-ref", "--short", "-q", "HEAD"], root)
    if rc != 0:
        print("detached HEAD: no current branch to commit on", file=sys.stderr)
        return 5
    branch = out.strip()

    rc, raw = git(["status", "--porcelain=v1", "-z", "--untracked-files=all"], root)
    if rc != 0:
        print("git status failed", file=sys.stderr)
        return 1
    entries = parse_status(raw)

    if paths:
        selected, skipped, problems = select_given(paths, entries, cwd, root)
        if problems:
            for line in problems:
                print(line, file=sys.stderr)
            return 4
    else:
        selected, skipped = entries, []

    stage, renamed_from, deleted = [], [], []
    seen = set()
    for e in selected:
        key = (e["path"], e["orig"], e["kind"])
        if key in seen:
            continue
        seen.add(key)
        if e["kind"] == "deleted":
            deleted.append(e["path"])
        else:
            stage.append(e["path"])
            if e["kind"] == "rename" and e["orig"]:
                renamed_from.append(e["orig"])

    flagged = [p for p in stage + renamed_from + deleted if is_credential_like(p)]
    if flagged:
        print("credential-like paths; nothing staged or committed:", file=sys.stderr)
        for p in flagged:
            print("  %s" % p, file=sys.stderr)
        return 2

    if not (stage or deleted):
        print("nothing to commit", file=sys.stderr)
        return 3

    rc, out = git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], root)
    upstream = out.strip() if rc == 0 and out.strip() else None
    rc, out = git(["remote"], root)
    remotes = [r for r in out.splitlines() if r.strip()] if rc == 0 else []

    result = {
        "root": root,
        "branch": branch,
        "upstream": upstream,
        "remotes": remotes,
        "stage": stage,
        "renamed_from": renamed_from,
        "deleted": deleted,
        "skipped_unchanged": skipped,
    }
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
