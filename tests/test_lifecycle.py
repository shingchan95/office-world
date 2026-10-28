import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from office import OfficeStore
from lifecycle import LifecycleError, TeamLifecycle, _board_description


class FakeCLI:
    """In-memory Hermes CLI double.

    By default the lead (``oscar``) already has the Kanban toolset enabled on
    ``telegram`` — the read-only prerequisite Office now requires before it will
    activate anything. ``set_kanban`` is retained only as a spy so tests can
    prove Office never writes the lead's Kanban configuration.
    """

    def __init__(self, profile_home, lead_kanban_enabled=True):
        self.homes = {"oscar": profile_home}
        self.enabled = {("oscar", "telegram"): lead_kanban_enabled}
        self.board_map = {}
        self.set_kanban_calls = []

    def profiles(self):
        return set(self.homes)

    def profile_home(self, profile):
        return self.homes[profile]

    def boards(self):
        return list(self.board_map.values())

    def create_board(self, team):
        if team["board_slug"] in self.board_map:
            raise LifecycleError("slug conflict")
        self.board_map[team["board_slug"]] = {
            "slug": team["board_slug"], "description": _board_description(team),
            "archived": False, "counts": {}}

    def archive_board(self, slug):
        self.board_map[slug]["archived"] = True

    def kanban_enabled(self, profile, platform):
        return self.enabled.get((profile, platform), False)

    def set_kanban(self, profile, platform, enabled):
        # Spy: record attempts to write the lead's Kanban toolset. Office must
        # never invoke this; asserting the list stays empty proves it.
        self.set_kanban_calls.append((profile, platform, enabled))
        self.enabled[(profile, platform)] = enabled


class TeamLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.profile = self.root / "profiles" / "oscar"
        self.profile.mkdir(parents=True)
        self.soul = self.profile / "SOUL.md"
        self.baseline = "# Oscar identity\nPreserve the existing creative mandate.\n"
        self.soul.write_text(self.baseline, encoding="utf-8")
        self.store = OfficeStore(self.root / "office.json", {"oscar"})
        self.cli = FakeCLI(self.profile)
        self.lifecycle = TeamLifecycle(self.store, self.cli)

    def tearDown(self):
        self.tmp.cleanup()

    def new_team(self, name):
        return self.store.create_team(name, ["oscar"], "oscar")

    def activate(self, team):
        plan = self.lifecycle.preview_activation(team["slug"], "telegram")
        return self.lifecycle.activate(team["slug"], "telegram", plan["plan_id"], confirmed=True)

    def disband(self, team):
        plan = self.lifecycle.preview_disband(team["slug"])
        return self.lifecycle.disband(team["slug"], plan["plan_id"], confirmed=True)

    def active_skill_dir(self, slug):
        return self.profile / "skills" / f"office-team-{slug}"

    def test_activation_installs_on_demand_skill_and_disband_archives_it(self):
        team = self.new_team("Research")
        os.chmod(self.profile, 0o755)
        profile_mode = self.profile.stat().st_mode & 0o777
        plan = self.lifecycle.preview_activation(team["slug"], "telegram")
        self.assertIn("kanban_toolset_will_change", plan)
        self.assertFalse(plan["kanban_toolset_will_change"])
        with self.assertRaisesRegex(LifecycleError, "explicit confirmation"):
            self.lifecycle.activate(team["slug"], "telegram", plan["plan_id"], confirmed=False)
        self.assertFalse(self.cli.boards())
        self.assertEqual(self.soul.read_text(), self.baseline)
        self.assertEqual(self.cli.set_kanban_calls, [])

        active = self.lifecycle.activate(team["slug"], "telegram", plan["plan_id"], confirmed=True)
        self.assertEqual(active["status"], "active")
        self.assertEqual(self.profile.stat().st_mode & 0o777, profile_mode)
        self.assertTrue(self.cli.kanban_enabled("oscar", "telegram"))
        self.assertEqual(self.soul.read_text(), self.baseline)
        self.assertEqual(self.cli.set_kanban_calls, [])
        member = active["activation"]["members"][0]
        skill_file = Path(member["path"])
        self.assertTrue(skill_file.is_file())
        self.assertIn("board=office-research", skill_file.read_text())
        self.assertEqual(skill_file.stat().st_mode & 0o777, 0o600)
        self.assertEqual(Path(member["directory"]).stat().st_mode & 0o777, 0o700)
        self.assertTrue(Path(member["archive_path"]).is_relative_to(self.profile / "office-archive"))

        self.cli.board_map[team["board_slug"]]["counts"] = {"todo": 1}
        with self.assertRaisesRegex(LifecycleError, "non-terminal Kanban tasks"):
            self.lifecycle.preview_disband(team["slug"])
        self.cli.board_map[team["board_slug"]]["counts"] = {"done": 1}
        self.disband(team)
        self.assertFalse(self.active_skill_dir(team["slug"]).exists())
        self.assertFalse((self.profile / "skills").exists())
        self.assertTrue((Path(member["archive_path"]) / "SKILL.md").is_file())
        self.assertEqual(self.soul.read_text(), self.baseline)
        self.assertTrue(self.cli.kanban_enabled("oscar", "telegram"))
        self.assertTrue(self.cli.board_map[team["board_slug"]]["archived"])
        self.assertIsNone(self.store.get_team(team["slug"]))
        self.assertEqual(self.cli.set_kanban_calls, [])

    def test_missing_lead_kanban_capability_fails_before_any_side_effects(self):
        team = self.new_team("Research")
        self.cli.enabled[("oscar", "telegram")] = False  # prerequisite missing

        with self.assertRaisesRegex(LifecycleError, "does not have the Kanban toolset enabled"):
            self.lifecycle.preview_activation(team["slug"], "telegram")
        # No Office side effects and no config writes occurred.
        self.assertFalse(self.cli.boards())
        self.assertEqual(self.cli.set_kanban_calls, [])
        self.assertFalse(self.active_skill_dir(team["slug"]).exists())
        self.assertFalse((self.profile / "skills").exists())
        self.assertEqual(self.soul.read_text(), self.baseline)

        # activate() re-runs the read-only prerequisite check, so it also fails
        # before any board/skill/config mutation.
        with self.assertRaisesRegex(LifecycleError, "does not have the Kanban toolset enabled"):
            self.lifecycle.activate(team["slug"], "telegram", "unverified-plan-id", confirmed=True)
        self.assertFalse(self.cli.boards())
        self.assertEqual(self.cli.set_kanban_calls, [])
        self.assertFalse((self.profile / "skills").exists())
        self.assertEqual(self.soul.read_text(), self.baseline)

    def test_activation_and_disband_never_write_kanban_config(self):
        team = self.new_team("Research")
        before = dict(self.cli.enabled)
        plan = self.lifecycle.preview_activation(team["slug"], "telegram")
        self.assertEqual(self.cli.set_kanban_calls, [])
        active = self.lifecycle.activate(team["slug"], "telegram", plan["plan_id"], confirmed=True)
        self.assertFalse(active["activation"]["kanban_added_by_office"])
        self.assertEqual(self.cli.set_kanban_calls, [])
        self.assertEqual(self.cli.enabled, before)  # unchanged on success
        dplan = self.lifecycle.preview_disband(team["slug"])
        self.assertEqual(dplan["disable_kanban"], False)
        self.lifecycle.disband(team["slug"], dplan["plan_id"], confirmed=True)
        self.assertEqual(self.cli.set_kanban_calls, [])  # never disabled
        self.assertEqual(self.cli.enabled, before)  # unchanged end-to-end
        self.assertTrue(self.cli.kanban_enabled("oscar", "telegram"))

    def test_personal_skills_and_identity_are_never_mutated(self):
        team = self.new_team("Research")
        personal = self.profile / "skills" / "my-notes" / "SKILL.md"
        personal.parent.mkdir(parents=True, mode=0o700)
        personal.write_text("# My personal notes\n", encoding="utf-8")
        identity = self.soul.read_text()

        plan = self.lifecycle.preview_activation(team["slug"], "telegram")
        self.lifecycle.activate(team["slug"], "telegram", plan["plan_id"], confirmed=True)
        # Protected agent state is byte-for-byte unchanged; Office never wrote it.
        self.assertEqual(self.soul.read_text(), identity)
        self.assertEqual(personal.read_text(), "# My personal notes\n")
        self.assertEqual(self.cli.set_kanban_calls, [])

        dplan = self.lifecycle.preview_disband(team["slug"])
        self.lifecycle.disband(team["slug"], dplan["plan_id"], confirmed=True)
        self.assertEqual(self.soul.read_text(), identity)
        self.assertEqual(personal.read_text(), "# My personal notes\n")
        self.assertTrue(personal.is_file())  # personal skill not removed
        self.assertTrue(self.cli.kanban_enabled("oscar", "telegram"))  # preserved
        self.assertEqual(self.cli.set_kanban_calls, [])

    def test_activation_supplies_conversation_led_meeting_contract(self):
        team = self.new_team("Research")
        text = self.lifecycle._team_skill(team)
        self.assertIn("## Conversation-led meetings", text)
        self.assertIn("description: Use when working or meeting with Office team research", text)
        self.assertIn("meeting_cli.py", text)
        self.assertIn(str(self.store.path.resolve()), text)
        self.assertIn("explicit_start", text)
        self.assertIn("reply_to", text)
        self.assertIn("not proof of participation", text)
        self.assertIn("same operating-system user", text)
        active = self.activate(team)
        installed = Path(active["activation"]["members"][0]["path"]).read_text()
        self.assertEqual(installed, text)
        self.assertEqual(self.cli.set_kanban_calls, [])
        self.disband(team)
        self.assertEqual(self.soul.read_text(), self.baseline)
        self.assertFalse(self.active_skill_dir(team["slug"]).exists())
        self.assertEqual(self.cli.set_kanban_calls, [])

    def test_activation_plan_binds_the_exact_meeting_guidance(self):
        team = self.new_team("Research")
        plan = self.lifecycle.preview_activation(team["slug"], "telegram")
        original = self.lifecycle._team_skill
        with patch.object(self.lifecycle, "_team_skill", side_effect=lambda t: original(t) + "\nChanged contract\n"):
            with self.assertRaisesRegex(LifecycleError, "stale"):
                self.lifecycle.activate(team["slug"], "telegram", plan["plan_id"], confirmed=True)
        self.assertFalse(self.cli.boards())
        self.assertFalse(self.active_skill_dir(team["slug"]).exists())
        self.assertEqual(self.cli.set_kanban_calls, [])

    def test_disband_refuses_open_meetings_and_retains_closed_history(self):
        from meetings import MeetingStore
        team = self.new_team("Research")
        self.activate(team)
        plan = self.lifecycle.preview_disband(team["slug"])
        meetings = MeetingStore(self.store.path)
        source = dict(platform="telegram", chat_id="fixture-chat", thread_id=None,
                      message_id="start", reply_to=None)
        m = meetings.start("oscar", team["slug"], "Review", ["Discuss"], ["oscar"], source, explicit_start=True)
        with self.assertRaisesRegex(LifecycleError, "open.*meeting"):
            self.lifecycle.preview_disband(team["slug"])
        with self.assertRaisesRegex(LifecycleError, "open.*meeting"):
            self.lifecycle.disband(team["slug"], plan["plan_id"], True)
        self.assertEqual(self.store.get_team(team["slug"])["status"], "active")
        meetings.transition("oscar", m["id"], 1, "end", dict(source, message_id="end", reply_to="start"))
        self.disband(team)
        self.assertEqual(meetings.get_meeting(m["id"])["status"], "ended")
        self.assertEqual(self.cli.set_kanban_calls, [])

    def test_shared_profile_toolset_stays_preserved_across_multiple_teams(self):
        first, second = self.new_team("Research"), self.new_team("Design")
        self.activate(first)
        self.activate(second)
        self.assertTrue(self.active_skill_dir(first["slug"]).exists())
        self.assertTrue(self.active_skill_dir(second["slug"]).exists())
        self.assertEqual(self.cli.set_kanban_calls, [])
        self.disband(first)
        self.assertTrue(self.cli.kanban_enabled("oscar", "telegram"))  # preserved, not disabled
        self.assertFalse(self.active_skill_dir(first["slug"]).exists())
        self.assertTrue(self.active_skill_dir(second["slug"]).exists())
        self.disband(second)
        self.assertTrue(self.cli.kanban_enabled("oscar", "telegram"))  # preserved
        self.assertFalse(self.active_skill_dir(second["slug"]).exists())
        self.assertEqual(self.soul.read_text(), self.baseline)
        self.assertEqual(self.cli.set_kanban_calls, [])

    def test_failed_skill_file_write_cleans_empty_office_created_dirs(self):
        team = self.new_team("Research")
        plan = self.lifecycle.preview_activation(team["slug"], "telegram")
        with patch("lifecycle._write_new_file", side_effect=OSError("synthetic write failure")):
            with self.assertRaisesRegex(LifecycleError, "rolled back"):
                self.lifecycle.activate(team["slug"], "telegram", plan["plan_id"], confirmed=True)
        planned = self.store.get_team(team["slug"])
        assert planned is not None
        self.assertEqual(planned["status"], "planned")
        self.assertFalse((self.profile / "skills").exists())
        self.assertFalse(self.active_skill_dir(team["slug"]).exists())
        self.assertTrue(self.cli.kanban_enabled("oscar", "telegram"))  # unchanged, never disabled
        self.assertTrue(self.cli.board_map[team["board_slug"]]["archived"])
        self.assertEqual(self.soul.read_text(), self.baseline)
        self.assertEqual(self.cli.set_kanban_calls, [])

    def test_failed_activation_rolls_back_owned_skill_and_board_without_kanban_writes(self):
        team = self.new_team("Research")

        class VerifyFailCLI(FakeCLI):
            """Fails activation at the post-install Kanban capability verification.

            The read-only verify in activate() runs only after a team skill has been
            installed for the lead; failing there exercises rollback of the board and
            skills without ever writing the lead's Kanban config.
            """

            def kanban_enabled(self, profile, platform):
                home = self.homes[profile]
                skills = home / "skills"
                if skills.is_dir() and any((d / "SKILL.md").exists() for d in skills.iterdir() if d.is_dir()):
                    raise LifecycleError("synthetic verify failure")
                return super().kanban_enabled(profile, platform)

        cli = VerifyFailCLI(self.profile)
        lifecycle = TeamLifecycle(self.store, cli)
        plan = lifecycle.preview_activation(team["slug"], "telegram")
        with self.assertRaisesRegex(LifecycleError, "rolled back"):
            lifecycle.activate(team["slug"], "telegram", plan["plan_id"], confirmed=True)
        planned = self.store.get_team(team["slug"])
        self.assertEqual(planned["status"], "planned")
        self.assertFalse(self.active_skill_dir(team["slug"]).exists())
        archive_dir = Path(planned["activation"]["members"][0]["archive_path"])
        self.assertTrue((archive_dir / "SKILL.md").is_file())
        self.assertEqual(self.soul.read_text(), self.baseline)
        self.assertEqual(cli.set_kanban_calls, [])  # never enabled or disabled on rollback
        self.assertTrue(cli.board_map[team["board_slug"]]["archived"])

    def test_stale_plan_refuses_existing_profile_skill_without_other_changes(self):
        team = self.new_team("Research")
        plan = self.lifecycle.preview_activation(team["slug"], "telegram")
        conflict = self.active_skill_dir(team["slug"])
        conflict.mkdir(parents=True)
        (conflict / "SKILL.md").write_text("User-owned skill.\n")
        with self.assertRaisesRegex(LifecycleError, "already exists"):
            self.lifecycle.activate(team["slug"], "telegram", plan["plan_id"], confirmed=True)
        self.assertFalse(self.cli.boards())
        self.assertTrue(self.cli.kanban_enabled("oscar", "telegram"))  # untouched
        self.assertEqual(self.cli.set_kanban_calls, [])
        self.assertEqual((conflict / "SKILL.md").read_text(), "User-owned skill.\n")

    def test_disband_refuses_to_move_an_edited_office_skill(self):
        team = self.new_team("Research")
        active = self.activate(team)
        skill_file = Path(active["activation"]["members"][0]["path"])
        skill_file.write_text(skill_file.read_text().replace("explicit hand-offs", "changed guidance"))
        with self.assertRaisesRegex(LifecycleError, "was edited"):
            self.lifecycle.preview_disband(team["slug"])
        self.assertTrue(self.cli.kanban_enabled("oscar", "telegram"))
        self.assertFalse(self.cli.board_map[team["board_slug"]]["archived"])
        self.assertEqual(self.cli.set_kanban_calls, [])

    def test_preexisting_kanban_permission_is_preserved(self):
        team = self.new_team("Research")
        self.cli.enabled[("oscar", "telegram")] = True
        active = self.activate(team)
        self.assertFalse(active["activation"]["kanban_added_by_office"])
        self.disband(team)
        self.assertTrue(self.cli.kanban_enabled("oscar", "telegram"))
        self.assertEqual(self.cli.set_kanban_calls, [])

    def test_disband_resume_accepts_an_already_archived_exact_skill(self):
        team = self.new_team("Research")
        active = self.activate(team)
        member = active["activation"]["members"][0]
        Path(member["archive_path"]).parent.mkdir(parents=True, mode=0o700)
        Path(member["directory"]).rename(member["archive_path"])
        self.store.update_team(team["slug"], {"status": "disbanding"})
        plan = self.lifecycle.preview_disband(team["slug"])
        self.assertTrue(plan["member_targets"][0]["already_archived"])
        self.lifecycle.disband(team["slug"], plan["plan_id"], confirmed=True)
        self.assertTrue(self.cli.board_map[team["board_slug"]]["archived"])
        self.assertTrue(self.cli.kanban_enabled("oscar", "telegram"))  # preserved
        self.assertEqual(self.cli.set_kanban_calls, [])


if __name__ == "__main__":
    unittest.main()
