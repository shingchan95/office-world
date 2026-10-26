import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from office import OfficeStore, ValidationError, discover_profiles


class HermesProfileDiscoveryTests(unittest.TestCase):
    @patch("office.subprocess.run")
    @patch("office.shutil.which", return_value="/usr/local/bin/hermes")
    def test_uses_canonical_default_name_and_named_profiles(self, _which, run):
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout=("Profile Model Gateway Alias Distribution\n"
                    "virtual_assistant (default) gpt-6-luna running — —\n"
                    "◆story-studio gpt-6.1-sol running story-studio —\n"),
        )
        self.assertEqual(
            discover_profiles(),
            [{"name": "default", "source": "Hermes"},
             {"name": "story-studio", "source": "Hermes"}],
        )

    @patch("office.shutil.which", return_value=None)
    def test_fails_closed_when_cli_missing(self, _which):
        with self.assertRaisesRegex(RuntimeError, "not found"):
            discover_profiles()


class OfficeStoreTests(unittest.TestCase):
    def test_team_with_member_lead_persists_and_reloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = OfficeStore(Path(tmp) / "office.json", profiles={"oscar", "research"})
            team = store.create_team("Research", members=["oscar", "research"], lead="oscar")
            loaded = OfficeStore(Path(tmp) / "office.json", profiles={"oscar", "research"})
            self.assertEqual(loaded.get_team(team["slug"]), team)
            self.assertEqual(team["board_slug"], "office-research")

    def test_rejects_lead_not_in_team_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "office.json"
            store = OfficeStore(path, profiles={"oscar", "research"})
            with self.assertRaises(ValidationError):
                store.create_team("Research", members=["research"], lead="oscar")
            self.assertFalse(path.exists())

    def test_rejects_unknown_profile_and_duplicate_team_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = OfficeStore(Path(tmp) / "office.json", profiles={"oscar", "research"})
            store.create_team("Research", members=["oscar"], lead="oscar")
            with self.assertRaises(ValidationError):
                store.create_team("Research", members=["oscar"], lead="oscar")
            with self.assertRaises(ValidationError):
                store.create_team("Other", members=["missing"], lead="missing")

    def test_rejects_string_as_member_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = OfficeStore(Path(tmp) / "office.json", profiles={"oscar"})
            with self.assertRaises(ValidationError):
                store.create_team("Research", members="oscar", lead="oscar")

    def test_disband_archives_team_and_keeps_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = OfficeStore(Path(tmp) / "office.json", profiles={"oscar", "research"})
            team = store.create_team("Research", members=["oscar", "research"], lead="oscar")
            archived = store.disband_team(team["slug"])
            self.assertFalse(store.get_team(team["slug"]))
            self.assertEqual(archived["status"], "disbanded")
            self.assertEqual(archived["members"], ["oscar", "research"])


if __name__ == "__main__":
    unittest.main()
