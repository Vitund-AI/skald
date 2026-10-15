"""gitutil helpers that shell out to git."""
from unittest import mock

from skald import gitutil

from .helpers import SkaldTestCase, git


class TestGithubSlug(SkaldTestCase):
    def test_parses_every_origin_form(self):
        forms = {
            "git@github.com:acme/widgets.git": "acme/widgets",
            "git@github.com:acme/widgets": "acme/widgets",
            "https://github.com/acme/widgets.git": "acme/widgets",
            "https://github.com/acme/widgets": "acme/widgets",
            "https://github.com/acme/widgets/": "acme/widgets",
            "ssh://git@github.com/acme/widgets.git": "acme/widgets",
            "https://user@github.com/acme/widgets.git": "acme/widgets",
            "https://github.com/Acme-Org/my.repo.git": "Acme-Org/my.repo",
        }
        for url, expected in forms.items():
            git(self.repo, "config", "remote.origin.url", url)
            self.assertEqual(gitutil.github_slug(self.repo), expected, url)

    def test_none_when_not_github_or_no_origin(self):
        for url in ("git@gitlab.com:acme/widgets.git", "https://example.com/acme/widgets.git",
                    "https://github.com/acme/widgets/extra", "https://github.com/acme"):
            git(self.repo, "config", "remote.origin.url", url)
            self.assertIsNone(gitutil.github_slug(self.repo), url)
        git(self.repo, "config", "--unset", "remote.origin.url")
        self.assertIsNone(gitutil.github_slug(self.repo))   # no origin
        self.assertIsNone(gitutil.github_slug(self.tmp))    # not a git repo


class TestNoConsoleWindow(SkaldTestCase):
    """On Windows, git must not flash a console window when Skald has none (the background board server)."""

    def flags(self, platform, has_console):
        with mock.patch.object(gitutil.sys, "platform", platform), \
                mock.patch.object(gitutil, "_has_console", return_value=has_console):
            return gitutil.no_window()

    def test_only_windows_without_a_console_hides_git(self):
        self.assertEqual(self.flags("linux", False), {})
        self.assertEqual(self.flags("darwin", False), {})
        self.assertEqual(self.flags("win32", False), {"creationflags": 0x08000000})
        self.assertEqual(self.flags("win32", True), {})  # a terminal: git shares it and can prompt there

    def test_every_git_call_carries_the_flags(self):
        calls = []

        def fake_run(*args, **kwargs):
            calls.append(kwargs)
            raise OSError("stop here")

        with mock.patch.object(gitutil, "no_window", return_value={"creationflags": 0x08000000}), \
                mock.patch.object(gitutil.subprocess, "run", side_effect=fake_run):
            gitutil.available()
            for call in (lambda: gitutil._run(["status"], self.repo), lambda: gitutil.cat_file_batch(self.repo, "HEAD", ["x"])):
                with self.assertRaises(gitutil.GitError):
                    call()
        self.assertEqual([c.get("creationflags") for c in calls], [0x08000000] * 3)
