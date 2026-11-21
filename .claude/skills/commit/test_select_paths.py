#!/usr/bin/env python3
"""Tests for select_paths.py (PLAN3). Builds throwaway git repos under $TMPDIR.

Run: python3 .claude/skills/commit/test_select_paths.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "select_paths.py")

sys.path.insert(0, HERE)
import select_paths  # noqa: E402

# Isolate from the user's git config (hooks, signing, global ignores).
ENV = dict(os.environ)
ENV.update({
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    # Also skip the user's global ignore file ($XDG_CONFIG_HOME/git/ignore).
    "XDG_CONFIG_HOME": os.path.join(os.devnull, "none"),
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
})


def sh(args, cwd):
    proc = subprocess.run(args, cwd=cwd, env=ENV, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise AssertionError("%s failed: %s" % (args, proc.stderr.decode()))
    return proc.stdout.decode()


def write(root, rel, text="x\n"):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path) or root, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class RepoCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = os.path.realpath(self._tmp.name)
        self.repo = os.path.join(self.base, "repo")
        os.makedirs(self.repo)
        sh(["git", "init", "-q", "-b", "main"], self.repo)
        write(self.repo, "tracked.md", "one\n")
        write(self.repo, "gone.md", "bye\n")
        write(self.repo, ".gitignore", "*.log\n")
        sh(["git", "add", "-A"], self.repo)
        sh(["git", "commit", "-q", "-m", "init"], self.repo)

    def tearDown(self):
        self._tmp.cleanup()

    def run_script(self, *args, cwd=None):
        proc = subprocess.run([sys.executable, SCRIPT] + list(args),
                              cwd=cwd or self.repo, env=ENV,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode()
        data = json.loads(out) if proc.returncode == 0 else None
        return proc.returncode, data, out, proc.stderr.decode()

    def git(self, *args):
        return sh(["git"] + list(args), self.repo)


class TestNoPaths(RepoCase):
    def test_new_modified_renamed_deleted_and_not_ignored(self):
        write(self.repo, "tracked.md", "two\n")
        write(self.repo, "new.md")
        write(self.repo, "debug.log")
        os.remove(os.path.join(self.repo, "gone.md"))
        write(self.repo, "old name.md", "r\n" * 20)
        self.git("add", "old name.md")
        self.git("commit", "-q", "-m", "add old")
        self.git("mv", "old name.md", "new name.md")
        rc, data, _, err = self.run_script()
        self.assertEqual(rc, 0, err)
        self.assertEqual(sorted(data["stage"]), ["new name.md", "new.md", "tracked.md"])
        self.assertEqual(data["renamed_from"], ["old name.md"])
        self.assertEqual(data["deleted"], ["gone.md"])
        self.assertNotIn("debug.log", data["stage"])
        self.assertEqual(data["root"], self.repo)
        self.assertEqual(data["branch"], "main")

    def test_new_directory_lists_files(self):
        write(self.repo, "pkg/sub/a.py")
        write(self.repo, "pkg/b.py")
        rc, data, _, err = self.run_script()
        self.assertEqual(rc, 0, err)
        self.assertEqual(sorted(data["stage"]), ["pkg/b.py", "pkg/sub/a.py"])

    def test_nothing_to_commit(self):
        rc, _, out, _ = self.run_script()
        self.assertEqual(rc, 3)
        self.assertEqual(out, "")

    def test_only_ignored_changes_is_nothing(self):
        write(self.repo, "x.log")
        self.assertEqual(self.run_script()[0], 3)


class TestCredentials(RepoCase):
    BLOCKED = [
        ".env", ".env.example", "a/server.key", "certs/x.pem", "id_rsa.pub",
        "credentials.json", "credentials-prod.json",
        ".claude/settings.local.json", "secrets/x.txt", "conf/.aws/config",
        "k/id_ed25519", "w.p12", ".netrc",
    ]

    def test_each_pattern_blocks(self):
        for rel in self.BLOCKED:
            with self.subTest(rel=rel):
                self.assertTrue(select_paths.is_credential_like(rel), rel)

    def test_allowed_names(self):
        for rel in ["README.md", "keys.md", "docs/env.md", "credentials.md",
                    "my-credentials.json", ".claude/settings.json", "secretsauce/a.md",
                    "a.keynote"]:
            with self.subTest(rel=rel):
                self.assertFalse(select_paths.is_credential_like(rel), rel)

    # The end-to-end tests below only create fixture files with names that the
    # script blocks but the Claude Code sandbox lets a test create, read and
    # delete. Names such as .env, *.key or id_rsa can't be cleaned up from inside
    # the sandbox. The full pattern list is covered by the name-only tests above.

    def test_stops_whole_run_and_names_paths(self):
        write(self.repo, "ok.md")
        write(self.repo, "deploy/credentials-prod.json", "SECRET=1\n")
        write(self.repo, ".claude/settings.local.json", "{}\n")
        write(self.repo, "conf/.kube/config")
        rc, _, out, err = self.run_script()
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")
        self.assertIn("deploy/credentials-prod.json", err)
        self.assertIn(".claude/settings.local.json", err)
        self.assertIn("conf/.kube/config", err)
        self.assertNotIn("SECRET", err)

    def test_given_path_credential(self):
        write(self.repo, "credentials.json")
        self.assertEqual(self.run_script("credentials.json")[0], 2)

    def test_given_directory_containing_credential(self):
        write(self.repo, "cfg/a.md")
        write(self.repo, "cfg/credentials.json")
        self.assertEqual(self.run_script("cfg")[0], 2)

    def test_rename_from_credential_name(self):
        write(self.repo, "id_ed25519.pub", "k\n" * 20)
        self.git("add", "id_ed25519.pub")
        self.git("commit", "-q", "-m", "fixture")
        self.git("mv", "id_ed25519.pub", "harmless.txt")
        rc, _, _, err = self.run_script()
        self.assertEqual(rc, 2)
        self.assertIn("id_ed25519.pub", err)


class TestGivenPaths(RepoCase):
    def test_exact_paths_only(self):
        write(self.repo, "a.md")
        write(self.repo, "b.md")
        write(self.repo, "c.md")
        rc, data, _, err = self.run_script("a.md", "@b.md")
        self.assertEqual(rc, 0, err)
        self.assertEqual(data["stage"], ["a.md", "b.md"])

    def test_spaces_round_trip(self):
        write(self.repo, "dir with space/file name.md")
        rc, data, _, err = self.run_script("dir with space/file name.md")
        self.assertEqual(rc, 0, err)
        self.assertEqual(data["stage"], ["dir with space/file name.md"])

    def test_unchanged_is_skipped(self):
        write(self.repo, "a.md")
        rc, data, _, err = self.run_script("a.md", "tracked.md")
        self.assertEqual(rc, 0, err)
        self.assertEqual(data["stage"], ["a.md"])
        self.assertEqual(data["skipped_unchanged"], ["tracked.md"])

    def test_all_unchanged_is_nothing(self):
        self.assertEqual(self.run_script("tracked.md")[0], 3)

    def test_missing_untracked_path(self):
        write(self.repo, "a.md")
        rc, _, out, err = self.run_script("a.md", "typo.md")
        self.assertEqual(rc, 4)
        self.assertEqual(out, "")
        self.assertIn("typo.md", err)

    def test_ignored_path(self):
        write(self.repo, "x.log")
        rc, _, _, err = self.run_script("x.log")
        self.assertEqual(rc, 4)
        self.assertIn("ignored", err)

    def test_outside_repo(self):
        write(self.base, "outside.md")
        self.assertEqual(self.run_script("../outside.md")[0], 4)

    def test_deleted_path(self):
        os.remove(os.path.join(self.repo, "gone.md"))
        rc, data, _, err = self.run_script("gone.md")
        self.assertEqual(rc, 0, err)
        self.assertEqual(data["deleted"], ["gone.md"])
        self.assertEqual(data["stage"], [])

    def test_relative_to_cwd(self):
        write(self.repo, "sub/a.md")
        rc, data, _, err = self.run_script("a.md", cwd=os.path.join(self.repo, "sub"))
        self.assertEqual(rc, 0, err)
        self.assertEqual(data["stage"], ["sub/a.md"])

    def test_directory_means_changed_files_under_it(self):
        write(self.repo, "docs/a.md")
        write(self.repo, "docs/b.md")
        write(self.repo, "other.md")
        rc, data, _, err = self.run_script("docs")
        self.assertEqual(rc, 0, err)
        self.assertEqual(sorted(data["stage"]), ["docs/a.md", "docs/b.md"])

    def test_unknown_option(self):
        self.assertEqual(self.run_script("-m", "msg")[0], 1)

    def test_dashdash_allows_dash_name(self):
        write(self.repo, "-odd.md")
        rc, data, _, err = self.run_script("--", "-odd.md")
        self.assertEqual(rc, 0, err)
        self.assertEqual(data["stage"], ["-odd.md"])


class TestRepoState(RepoCase):
    def test_detached_head(self):
        write(self.repo, "a.md")
        self.git("checkout", "-q", "--detach")
        self.assertEqual(self.run_script()[0], 5)

    def test_outside_a_repo(self):
        plain = os.path.join(self.base, "plain")
        os.makedirs(plain)
        self.assertEqual(self.run_script(cwd=plain)[0], 1)

    def test_no_remote(self):
        write(self.repo, "a.md")
        rc, data, _, err = self.run_script()
        self.assertEqual(rc, 0, err)
        self.assertIsNone(data["upstream"])
        self.assertEqual(data["remotes"], [])

    def test_remote_without_and_with_upstream(self):
        bare = os.path.join(self.base, "remote.git")
        sh(["git", "init", "-q", "--bare", bare], self.base)
        self.git("remote", "add", "origin", bare)
        write(self.repo, "a.md")
        rc, data, _, err = self.run_script()
        self.assertEqual(rc, 0, err)
        self.assertIsNone(data["upstream"])
        self.assertEqual(data["remotes"], ["origin"])
        self.git("push", "-q", "-u", "origin", "main")
        rc, data, _, err = self.run_script()
        self.assertEqual(rc, 0, err)
        self.assertEqual(data["upstream"], "origin/main")


class TestCommitCommands(RepoCase):
    """The two commands SKILL.md runs with the script's output (PLAN3 step 5)."""

    def commit_from(self, data, message="test: commit"):
        paths = data["stage"] + data["renamed_from"] + data["deleted"]
        msg = os.path.join(self.base, "msg.txt")
        with open(msg, "w", encoding="utf-8") as f:
            f.write(message + "\n")
        sh(["git", "-C", data["root"], "add", "--"] + paths, self.base)
        sh(["git", "-C", data["root"], "commit", "-q", "--only", "-F", msg, "--"] + paths,
           self.base)
        return sh(["git", "show", "--name-status", "--format=", "HEAD"], self.repo)

    def test_other_staged_change_stays_staged(self):
        write(self.repo, "a.md")
        write(self.repo, "staged-elsewhere.md")
        self.git("add", "staged-elsewhere.md")
        rc, data, _, err = self.run_script("a.md")
        self.assertEqual(rc, 0, err)
        shown = self.commit_from(data)
        self.assertEqual(shown.split(), ["A", "a.md"])
        status = self.git("status", "--porcelain")
        self.assertIn("A  staged-elsewhere.md", status)

    def test_rename_deletion_and_spaces(self):
        write(self.repo, "old.md", "r\n" * 20)
        self.git("add", "old.md")
        self.git("commit", "-q", "-m", "add old")
        os.rename(os.path.join(self.repo, "old.md"), os.path.join(self.repo, "new.md"))
        os.remove(os.path.join(self.repo, "gone.md"))
        write(self.repo, "a b.md")
        rc, data, _, err = self.run_script()
        self.assertEqual(rc, 0, err)
        shown = self.commit_from(data)
        self.assertIn("D\tgone.md", shown)
        self.assertIn("a b.md", shown)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_initial_commit(self):
        fresh = os.path.join(self.base, "fresh")
        os.makedirs(fresh)
        sh(["git", "init", "-q", "-b", "main"], fresh)
        write(fresh, "first.md")
        rc, data, _, err = self.run_script(cwd=fresh)
        self.assertEqual(rc, 0, err)
        paths = data["stage"]
        msg = os.path.join(self.base, "m.txt")
        with open(msg, "w") as f:
            f.write("docs: first\n")
        sh(["git", "-C", fresh, "add", "--"] + paths, self.base)
        sh(["git", "-C", fresh, "commit", "-q", "--only", "-F", msg, "--"] + paths, self.base)
        self.assertIn("first.md", sh(["git", "ls-files"], fresh))


if __name__ == "__main__":
    unittest.main(verbosity=1)
