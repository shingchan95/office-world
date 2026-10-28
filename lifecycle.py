"""Reversible, explicitly confirmed Hermes team integration.

No actions run on import. The web UI must obtain a current preview and a
separate confirmation before calling activate() or disband().
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Callable

from office import OfficeStore, ValidationError
from meeting_guidance import meeting_guidance
from meetings import MeetingStore, MeetingError, registry_lock


class LifecycleError(RuntimeError):
    pass


ACTIVE_STATUSES = {"triage", "todo", "ready", "running", "review", "blocked", "scheduled"}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_hash(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def resolve_kanban_home(environ=None) -> Path:
    """Resolve Hermes' shared Kanban root, not the active named-profile home."""
    env = os.environ if environ is None else environ
    override = env.get("HERMES_KANBAN_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    native = (Path.home() / ".hermes").resolve()
    configured_home = env.get("HERMES_HOME", "").strip()
    if not configured_home:
        return native
    configured = Path(configured_home).expanduser().resolve()
    try:
        configured.relative_to(native)
        return native
    except ValueError:
        if configured.parent.name == "profiles":
            return configured.parent.parent
        return configured


def _board_description(team: dict) -> str:
    return (f"Office team board {team['slug']}; members: {', '.join(team['members'])}; "
            f"lead: {team['lead']}; ownership token: {team['office_id']}.")


def _ensure_private_dir(path: Path) -> None:
    missing = []
    current = path
    while not current.exists():
        if current.is_symlink():
            raise LifecycleError(f"Refusing to follow a symlink in Office path {current}.")
        missing.append(current)
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise LifecycleError(f"Unsafe Office directory path: {current}.")
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        os.chmod(directory, 0o700)


def _write_new_file(path: Path, data: bytes, mode: int = 0o600) -> None:
    """Create a file exclusively via a same-directory temp file; never overwrite."""
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise LifecycleError("Target directory is missing or unsafe.")
    if path.exists() or path.is_symlink():
        raise LifecycleError(f"Refusing to overwrite existing Office target: {path.name}.")
    fd, temp = tempfile.mkstemp(prefix=".office-", suffix=".tmp", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _only_skill_file(skill_dir: Path) -> Path:
    if skill_dir.is_symlink() or not skill_dir.is_dir():
        raise LifecycleError("Office skill directory is missing or unsafe.")
    entries = list(skill_dir.iterdir())
    if len(entries) != 1 or entries[0].name != "SKILL.md" or entries[0].is_symlink() or not entries[0].is_file():
        raise LifecycleError("Office skill directory contains unexpected files; refusing to move it.")
    return entries[0]


class HermesCLI:
    """Narrow wrapper around supported Hermes CLI commands."""

    def __init__(self, executable: str = "hermes", kanban_home: Path | None = None,
                 runner: Callable = subprocess.run):
        self.executable = shutil.which(executable) or executable
        self.kanban_home = Path(kanban_home or resolve_kanban_home()).resolve()
        self.runner = runner

    def run(self, args: list[str], profile: str | None = None) -> str:
        command = [self.executable]
        if profile and profile != "default":
            command += ["-p", profile]
        command += args
        env = os.environ.copy()
        env["HERMES_KANBAN_HOME"] = str(self.kanban_home)
        if profile == "default":
            env["HERMES_HOME"] = str(self.kanban_home)
        try:
            result = self.runner(command, capture_output=True, text=True, timeout=30, check=False, env=env)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LifecycleError(f"Hermes command could not run: {args[0]}.") from exc
        if result.returncode != 0:
            raise LifecycleError(f"Hermes command failed ({args[0]}, exit {result.returncode}).")
        return result.stdout

    def profiles(self) -> set[str]:
        from office import discover_profiles
        return {p["name"] for p in discover_profiles()}

    def profile_home(self, profile: str) -> Path:
        if profile == "default":
            return self.kanban_home
        output = self.run(["config", "path"], profile=profile)
        config_paths = [Path(line.strip()).expanduser() for line in output.splitlines()
                        if line.strip().endswith("config.yaml")]
        if len(config_paths) != 1:
            raise LifecycleError(f"Could not resolve the config path for profile {profile!r}.")
        config = config_paths[0].resolve()
        expected_parent = self.kanban_home / "profiles"
        try:
            config.relative_to(expected_parent.resolve())
        except ValueError as exc:
            raise LifecycleError(f"Profile {profile!r} resolves outside the Hermes profile root.") from exc
        return config.parent

    def boards(self) -> list[dict]:
        try:
            payload = json.loads(self.run(["kanban", "boards", "list", "--json", "--all"]))
        except json.JSONDecodeError as exc:
            raise LifecycleError("Hermes returned invalid board data.") from exc
        if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
            raise LifecycleError("Hermes returned an unexpected board list.")
        return payload

    def create_board(self, team: dict) -> None:
        self.run(["kanban", "boards", "create", team["board_slug"], "--name", team["name"],
                  "--description", _board_description(team)])

    def archive_board(self, board_slug: str) -> None:
        self.run(["kanban", "boards", "rm", board_slug])

    def kanban_enabled(self, profile: str, platform: str) -> bool:
        output = self.run(["tools", "list", "--platform", platform], profile=profile)
        for line in output.splitlines():
            match = re.search(r"[✓✗]\s+(enabled|disabled)\s+kanban\b", line, flags=re.I)
            if match:
                return match.group(1).casefold() == "enabled"
        raise LifecycleError(f"Could not verify the Kanban toolset state for {profile!r} ({platform}).")


class TeamLifecycle:
    def __init__(self, store: OfficeStore, cli: HermesCLI | None = None):
        self.store = store
        self.cli = cli or HermesCLI()

    def _team_skill(self, team: dict) -> str:
        people = ", ".join(team["members"])
        return ("---\n"
                f"name: office-team-{team['slug']}\n"
                f"description: Use when working or meeting with Office team {team['slug']}, including one-to-one meetings with its members.\n"
                "version: 1.0.0\n"
                "---\n\n"
                f"# Office team {team['slug']}\n\n"
                f"Members: {people}. Team lead: {team['lead']}.\n\n"
                "## When to use\n"
                f"Use only for work explicitly assigned to Office team {team['slug']}.\n\n"
                "## Cooperation rules\n"
                f"- Keep this team's Kanban work on board `{team['board_slug']}`; pass `board={team['board_slug']}` to each Kanban tool call.\n"
                "- Coordinate through task comments and explicit hand-offs; keep unrelated work on its own board.\n"
                "- Follow the existing profile identity, role, production windows, and approval rules. Team membership grants no extra permissions.\n"
                "- Outside this team's explicitly assigned work, follow the profile's existing instructions unchanged.\n"
                + meeting_guidance(team, self.store.path))

    def _profile_skill_paths(self, profile: str, slug: str) -> tuple[Path, Path, Path]:
        home = self.cli.profile_home(profile)
        skills_root = home / "skills"
        skill_dir = skills_root / f"office-team-{slug}"
        return skills_root, skill_dir, skill_dir / "SKILL.md"

    def _archive_path(self, profile_home: Path, slug: str, attempt_id: str) -> Path:
        return profile_home / "office-archive" / f"office-team-{slug}-{attempt_id}"

    def preview_activation(self, slug: str, platform: str) -> dict:
        team = self.store.get_team(slug)
        if team is None:
            raise LifecycleError("Team not found.")
        if team.get("status") != "planned":
            raise LifecycleError("Only a planned team can be activated.")
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", platform):
            raise LifecycleError("Platform name is invalid.")
        if not set(team["members"]).issubset(self.cli.profiles()):
            raise LifecycleError("A selected Hermes profile is no longer available.")
        if any(b.get("slug") == team["board_slug"] for b in self.cli.boards()):
            raise LifecycleError("The planned board name is already in use, including archived boards.")
        member_targets = []
        for profile in team["members"]:
            skills_root, skill_dir, skill_file = self._profile_skill_paths(profile, slug)
            if skills_root.is_symlink() or (skills_root.exists() and not skills_root.is_dir()):
                raise LifecycleError(f"Profile {profile!r} has an unsafe skills path; no file was changed.")
            if skill_dir.exists() or skill_dir.is_symlink():
                raise LifecycleError(f"Office skill path already exists for profile {profile!r}; refusing to overwrite it.")
            member_targets.append({"profile": profile, "path": str(skill_file),
                                   "directory": str(skill_dir), "skills_root": str(skills_root),
                                   "skills_root_existed": skills_root.is_dir()})
        enabled_now = self.cli.kanban_enabled(team["lead"], platform)
        if not enabled_now:
            raise LifecycleError(
                f"Lead profile {team['lead']!r} does not have the Kanban toolset enabled "
                f"on {platform!r}. Office never enables or disables Kanban on your behalf; "
                "it only verifies the prerequisite capability before any Office-owned change. "
                "Enable the Kanban toolset for this profile and platform through Hermes' "
                "supported configuration flow, then retry activation."
            )
        shared = [t for t in self.store.list_teams()
                  if t.get("status") == "active" and t.get("activation", {}).get("lead") == team["lead"]
                  and t.get("activation", {}).get("platform") == platform]
        baseline = shared[0]["activation"]["kanban_baseline_enabled"] if shared else enabled_now
        plan = {"slug": slug, "name": team["name"], "office_id": team["office_id"],
                "board_slug": team["board_slug"], "lead": team["lead"],
                "members": team["members"], "platform": platform,
                "member_targets": member_targets, "kanban_enabled_before": enabled_now,
                "kanban_baseline_enabled": baseline,
                "kanban_toolset_will_change": False,
                "board_will_be_created": True, "skill_name": f"office-team-{slug}",
                "guidance_will_be_added_to": [m["profile"] for m in member_targets],
                "meeting_integration": True,
                "skill_sha256": _sha(self._team_skill(team).encode("utf-8")), "plan_id": ""}
        plan["plan_id"] = _canonical_hash({k: v for k, v in plan.items() if k != "plan_id"})
        return plan

    def activate(self, slug: str, platform: str, plan_id: str, confirmed: bool) -> dict:
        if not confirmed:
            raise LifecycleError("Activation requires an explicit confirmation.")
        plan = self.preview_activation(slug, platform)
        if plan["plan_id"] != plan_id:
            raise LifecycleError("The activation preview is stale; refresh it before confirming.")
        team = self.store.get_team(slug)
        if team is None:
            raise LifecycleError("Team not found after preview.")
        attempt_id = uuid.uuid4().hex
        activation = {"status": "applying", "platform": platform, "lead": team["lead"],
                      "kanban_baseline_enabled": plan["kanban_baseline_enabled"],
                      "kanban_added_by_office": plan["kanban_toolset_will_change"],
                      "board_marker": team["office_id"], "board_created": False,
                      "attempt_id": attempt_id, "members": []}
        self.store.update_team(slug, {"status": "activating", "activation": activation})
        try:
            self.cli.create_board(team)
            created_board = next((b for b in self.cli.boards() if b.get("slug") == team["board_slug"]), None)
            if not created_board or created_board.get("description") != _board_description(team):
                raise LifecycleError("A board slug conflict prevented verified Office ownership.")
            activation["board_created"] = True
            self.store.update_team(slug, {"activation": activation})
            skill_text = self._team_skill(team).encode("utf-8")
            for target in plan["member_targets"]:
                profile = target["profile"]
                skills_root = Path(target["skills_root"])
                skill_dir = Path(target["directory"])
                skill_file = Path(target["path"])
                home = self.cli.profile_home(profile)
                archive_dir = self._archive_path(home, slug, attempt_id)
                member = {"profile": profile, "path": str(skill_file), "directory": str(skill_dir),
                          "skills_root": str(skills_root), "skills_root_existed": target["skills_root_existed"],
                          "archive_path": str(archive_dir), "skill_sha256": _sha(skill_text), "skill_text": skill_text.decode("utf-8"),
                          "created": False}
                if skill_dir.exists() or skill_dir.is_symlink():
                    raise LifecycleError(f"Profile {profile!r} skill path changed after preview; stopping.")
                activation["members"].append(member)
                self.store.update_team(slug, {"activation": activation})
                _ensure_private_dir(skills_root)
                skill_dir.mkdir(mode=0o700)
                os.chmod(skill_dir, 0o700)
                _write_new_file(skill_file, skill_text)
                member["created"] = True
                self.store.update_team(slug, {"activation": activation})
            # Office never enables or disables the lead's Kanban toolset; it only
            # verifies the prerequisite capability that preview_activation already checked.
            if not self.cli.kanban_enabled(team["lead"], platform):
                raise LifecycleError(
                    f"Lead {team['lead']!r} is missing the Kanban toolset on {platform!r}; "
                    "activation cannot continue without altering protected config.")
            board = next((b for b in self.cli.boards()
                          if b.get("slug") == team["board_slug"] and not b.get("archived")), None)
            if not board or board.get("description") != _board_description(team):
                raise LifecycleError("Created board did not verify as active and Office-owned.")
            for member in activation["members"]:
                skill_file = Path(member["path"])
                if _sha(skill_file.read_bytes()) != member["skill_sha256"]:
                    raise LifecycleError(f"Team skill did not verify for {member['profile']!r}.")
            activation["status"] = "active"
            return self.store.update_team(slug, {"status": "active", "platform": platform, "activation": activation})
        except Exception as exc:
            recovery_errors = []
            for member in reversed(activation["members"]):
                try:
                    skill_dir = Path(member["directory"])
                    if not skill_dir.exists() and not skill_dir.is_symlink():
                        continue
                    if not member["created"]:
                        if skill_dir.is_dir() and not skill_dir.is_symlink() and not any(skill_dir.iterdir()):
                            skill_dir.rmdir()
                            if not member["skills_root_existed"]:
                                try:
                                    Path(member["skills_root"]).rmdir()
                                except OSError:
                                    pass
                        continue
                    skill_file = _only_skill_file(skill_dir)
                    if _sha(skill_file.read_bytes()) != member["skill_sha256"]:
                        recovery_errors.append(f"team skill rollback conflicted for {member['profile']}")
                        continue
                    archive_dir = Path(member["archive_path"])
                    _ensure_private_dir(archive_dir.parent)
                    if archive_dir.exists() or archive_dir.is_symlink():
                        recovery_errors.append(f"skill archive path already exists for {member['profile']}")
                        continue
                    os.rename(skill_dir, archive_dir)
                    if not member["skills_root_existed"]:
                        try:
                            Path(member["skills_root"]).rmdir()
                        except OSError:
                            pass
                except Exception as recovery_exc:
                    recovery_errors.append(f"skill rollback failed for {member['profile']}: {recovery_exc}")
            # Office never disabled the lead's Kanban toolset, so activation
            # rollback performs no write-capability restoration.
            if activation["board_created"]:
                try:
                    owned = next((b for b in self.cli.boards()
                                  if b.get("slug") == team["board_slug"]
                                  and b.get("description") == _board_description(team)), None)
                    if owned and int(owned.get("total", 0)) == 0:
                        self.cli.archive_board(team["board_slug"])
                    elif owned:
                        recovery_errors.append("Office-created board now contains tasks; left it intact.")
                except Exception as recovery_exc:
                    recovery_errors.append(f"board rollback failed: {recovery_exc}")
            if recovery_errors:
                activation["status"] = "partial"
                activation["error"] = str(exc)
                activation["recovery_error"] = "; ".join(recovery_errors)
                self.store.update_team(slug, {"status": "partial", "activation": activation})
                raise LifecycleError(f"Activation failed and rollback was incomplete: {activation['recovery_error']}") from exc
            activation["status"] = "rolled_back"
            activation["error"] = str(exc)
            self.store.update_team(slug, {"status": "planned", "activation": activation})
            raise LifecycleError(f"Activation failed; its verified Office changes were rolled back: {exc}") from exc

    def preview_disband(self, slug: str) -> dict:
        team = self.store.get_team(slug)
        if team is None:
            raise LifecycleError("Team not found.")
        if team.get("status") not in {"active", "disbanding"}:
            raise LifecycleError("Only an active Office team can be disbanded.")
        try:
            if MeetingStore(self.store.path).open_for_team(team["office_id"]):
                raise LifecycleError("Close or cancel open team meetings before disbanding.")
        except MeetingError as exc:
            raise LifecycleError("Cannot verify meeting state; refusing disband.") from exc
        activation = team["activation"]
        board = next((b for b in self.cli.boards() if b.get("slug") == team["board_slug"]), None)
        if not board:
            raise LifecycleError("The team's Hermes board is missing; refusing an incomplete disband.")
        counts = board.get("counts") or {}
        open_statuses = {k: v for k, v in counts.items() if k in ACTIVE_STATUSES and int(v) > 0}
        if open_statuses:
            raise LifecycleError("Resolve or archive the team's non-terminal Kanban tasks before disbanding.")
        if board.get("description") != _board_description(team):
            raise LifecycleError("Board ownership metadata changed; refusing to archive a board Office cannot verify.")
        member_targets = []
        for member in activation.get("members", []):
            profile = member["profile"]
            home = self.cli.profile_home(profile)
            skills_root, expected_dir, expected_file = self._profile_skill_paths(profile, slug)
            skill_dir, skill_file = Path(member["directory"]), Path(member["path"])
            archive_dir = Path(member["archive_path"])
            if skill_dir.resolve() != expected_dir.resolve() or skill_file.resolve() != expected_file.resolve():
                raise LifecycleError(f"Stored skill target for {profile!r} no longer matches its Hermes profile.")
            try:
                archive_dir.resolve().relative_to((home / "office-archive").resolve())
            except ValueError as exc:
                raise LifecycleError(f"Stored archive path for {profile!r} is outside its profile archive.") from exc
            if skill_dir.exists() or skill_dir.is_symlink():
                file_path = _only_skill_file(skill_dir)
                if file_path != skill_file or _sha(file_path.read_bytes()) != member["skill_sha256"]:
                    raise LifecycleError(f"Office skill for {profile!r} was edited; refusing to move it.")
                if archive_dir.exists() or archive_dir.is_symlink():
                    raise LifecycleError(f"Archive path for {profile!r} already exists; refusing to overwrite it.")
                already_archived = False
            elif team.get("status") == "disbanding" and archive_dir.is_dir() and not archive_dir.is_symlink():
                archived_skill = _only_skill_file(archive_dir)
                if archived_skill.name != "SKILL.md" or _sha(archived_skill.read_bytes()) != member["skill_sha256"]:
                    raise LifecycleError(f"Archived Office skill for {profile!r} was changed; refusing to continue.")
                already_archived = True
            else:
                raise LifecycleError(f"Office skill for {profile!r} is missing; refusing an incomplete disband.")
            member_targets.append({"profile": profile, "path": str(skill_file), "directory": str(skill_dir),
                                   "archive_path": str(archive_dir), "skill_sha256": member["skill_sha256"],
                                   "skills_root": str(skills_root),
                                   "skills_root_existed": member.get("skills_root_existed", True),
                                   "already_archived": already_archived})
        shared = [t for t in self.store.list_teams()
                  if t["slug"] != slug and t.get("status") == "active"
                  and t.get("activation", {}).get("lead") == activation["lead"]
                  and t.get("activation", {}).get("platform") == activation["platform"]]
        # Office never disables the lead's Kanban toolset, regardless of whether
        # other active teams share it; disband archives only Office-owned resources.
        plan = {"slug": slug, "board_slug": team["board_slug"], "lead": activation["lead"],
                "platform": activation["platform"], "member_targets": member_targets,
                "archive_board": not board.get("archived"), "disable_kanban": False,
                "other_teams_share_kanban": bool(shared), "plan_id": ""}
        plan["plan_id"] = _canonical_hash({k: v for k, v in plan.items() if k != "plan_id"})
        return plan

    def disband(self, slug: str, plan_id: str, confirmed: bool) -> dict:
        if not confirmed:
            raise LifecycleError("Disbanding requires an explicit confirmation.")
        try:
            with registry_lock(self.store.path):
                return self._disband_locked(slug, plan_id, confirmed)
        except MeetingError as exc:
            raise LifecycleError("Cannot lock meeting state; refusing disband.") from exc

    def _disband_locked(self, slug: str, plan_id: str, confirmed: bool) -> dict:
        if not confirmed:
            raise LifecycleError("Disbanding requires an explicit confirmation.")
        plan = self.preview_disband(slug)
        if plan["plan_id"] != plan_id:
            raise LifecycleError("The disband preview is stale; refresh it before confirming.")
        team = self.store.get_team(slug)
        if team is None:
            raise LifecycleError("Team not found after preview.")
        activation = team["activation"]
        self.store.update_team(slug, {"status": "disbanding"})
        moved = []
        try:
            for target in plan["member_targets"]:
                if target["already_archived"]:
                    if not target["skills_root_existed"]:
                        try:
                            Path(target["skills_root"]).rmdir()
                        except OSError:
                            pass
                    continue
                skill_dir = Path(target["directory"])
                skill_file = _only_skill_file(skill_dir)
                if _sha(skill_file.read_bytes()) != target["skill_sha256"]:
                    raise LifecycleError(f"Office skill for {target['profile']!r} changed after preview.")
                archive_dir = Path(target["archive_path"])
                _ensure_private_dir(archive_dir.parent)
                if archive_dir.exists() or archive_dir.is_symlink():
                    raise LifecycleError(f"Archive path for {target['profile']!r} appeared after preview.")
                os.rename(skill_dir, archive_dir)
                if not target["skills_root_existed"]:
                    try:
                        Path(target["skills_root"]).rmdir()
                    except OSError:
                        pass
                moved.append(target)
            # Office never disables the lead's Kanban toolset, so disband archives only
            # Office-owned skills and board, leaving the lead's capability intact.
            if plan["archive_board"]:
                self.cli.archive_board(team["board_slug"])
            archived_board = next((b for b in self.cli.boards()
                                   if b.get("slug") == team["board_slug"] and b.get("archived")), None)
            if not archived_board:
                raise LifecycleError("The board archive did not verify.")
            return self.store.disband_team(slug)
        except Exception as exc:
            recovery_errors = []
            # Office never disabled the lead's Kanban toolset, so disband rollback
            # restores only Office-owned skills and never re-enables a grant.
            for target in reversed(moved):
                try:
                    original_dir = Path(target["directory"])
                    archive_dir = Path(target["archive_path"])
                    archived_skill = _only_skill_file(archive_dir)
                    if _sha(archived_skill.read_bytes()) != target["skill_sha256"]:
                        recovery_errors.append(f"skill restoration conflicted for {target['profile']}")
                    elif original_dir.exists() or original_dir.is_symlink():
                        recovery_errors.append(f"skill destination reappeared for {target['profile']}")
                    else:
                        _ensure_private_dir(original_dir.parent)
                        os.rename(archive_dir, original_dir)
                except Exception as restore_exc:
                    recovery_errors.append(f"skill restoration failed for {target['profile']}: {restore_exc}")
            detail = "; ".join(recovery_errors)
            self.store.update_team(slug, {"status": "disbanding", "lifecycle_error": str(exc),
                                          "recovery_error": detail or None})
            raise LifecycleError(f"Disband stopped; Office preserved recovery state: {exc}" + (f" ({detail})" if detail else "")) from exc
