"""The opt-in PyPI update check (network stubbed; nothing here touches the wire)."""
import tempfile
import unittest
from pathlib import Path

from skald import update as upd


class TestUpdate(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(setattr, upd, "fetch_latest", upd.fetch_latest)

    def stub(self, value):
        def fake(timeout=upd.TIMEOUT):
            return value
        upd.fetch_latest = fake

    def test_version_compare_is_numeric_and_final_only(self):
        self.assertTrue(upd.is_newer("0.8.0", "0.7.0"))
        self.assertTrue(upd.is_newer("0.10.0", "0.9.0"))   # numeric, not lexical
        self.assertFalse(upd.is_newer("0.7.0", "0.7.0"))
        self.assertFalse(upd.is_newer("0.6.9", "0.7.0"))
        self.assertIsNone(upd.parse_version("0.8.0rc1"))   # a pre-release is not a final release
        self.assertFalse(upd.is_newer("0.8.0rc1", "0.7.0"))
        self.assertIsNone(upd.parse_version("latest"))
        self.assertFalse(upd.is_newer("garbage", "0.7.0"))

    def test_check_caches_and_reports_outdated(self):
        self.stub("0.9.0")
        r = upd.check(self.home, "0.7.0")
        self.assertEqual((r["latest"], r["outdated"]), ("0.9.0", True))
        self.assertTrue(upd.state_path(self.home).exists())
        # a fresh cache is served without another fetch
        self.stub("99.0.0")
        self.assertEqual(upd.check(self.home, "0.7.0")["latest"], "0.9.0")
        # force refetches
        self.assertEqual(upd.check(self.home, "0.7.0", force=True)["latest"], "99.0.0")

    def test_up_to_date_and_offline_are_silent(self):
        self.stub("0.7.0")
        self.assertFalse(upd.check(self.home, "0.7.0")["outdated"])
        # offline (a failed lookup returns None) with no cache: not outdated, no crash
        self.stub(None)
        r = upd.check(Path(tempfile.mkdtemp()), "0.7.0")
        self.assertEqual((r["latest"], r["outdated"]), (None, False))
