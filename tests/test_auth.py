import json
import tempfile
import unittest
from pathlib import Path

from auth import OfficeAuth, PasswordPolicyError


class OfficeAuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "auth.json"
        self.auth = OfficeAuth(self.path)
        self.auth.initialize("tommy", "temporary-passphrase", force_change=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_initial_password_authenticates_but_requires_change(self):
        self.assertTrue(self.auth.authenticate("tommy", "temporary-passphrase"))
        self.assertTrue(self.auth.must_change)

    def test_password_change_replaces_initial_password_and_clears_gate(self):
        self.auth.change_password("a-new-strong-passphrase", force_change=False)
        self.assertFalse(self.auth.authenticate("tommy", "temporary-passphrase"))
        self.assertTrue(self.auth.authenticate("tommy", "a-new-strong-passphrase"))
        self.assertFalse(self.auth.must_change)

    def test_password_change_rejects_password_shorter_than_eight(self):
        with self.assertRaises(PasswordPolicyError):
            self.auth.change_password("1234567", force_change=False)
        self.assertTrue(self.auth.must_change)

    def test_password_change_accepts_eight_characters(self):
        self.auth.change_password("eight123", force_change=False)
        self.assertTrue(self.auth.authenticate("tommy", "eight123"))
        self.assertFalse(self.auth.must_change)

    def test_password_file_is_private_and_contains_only_a_hash(self):
        mode = self.path.stat().st_mode & 0o777
        stored = self.path.read_text(encoding="utf-8")
        self.assertEqual(mode, 0o600)
        self.assertNotIn("temporary-passphrase", stored)
        self.assertEqual(json.loads(stored)["username"], "tommy")

    def test_corrupt_auth_file_fails_closed(self):
        self.path.write_text("not-json", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.auth.authenticate("tommy", "temporary-passphrase")


if __name__ == "__main__":
    unittest.main()
