"""gitutil helpers that shell out to git."""
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
