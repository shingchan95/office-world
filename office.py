"""Small, dependency-free Office team registry for Hermes profiles.

This first slice is intentionally declarative: it stores Office membership
separately and never edits Hermes profiles or Kanban state.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


class ValidationError(ValueError):
    pass


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise ValidationError("Team name must contain letters or numbers.")
    return slug[:48].rstrip("-")


class OfficeStore:
    def __init__(self, path: Path, profiles: Iterable[str]):
        self.path = Path(path)
        self.profiles = set(profiles)

    def _read(self) -> dict:
        if not self.path.exists():
            return {"version": 1, "teams": [], "archive": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cannot read Office data safely: {exc}") from exc
        if (not isinstance(data, dict) or data.get("version") != 1
                or not isinstance(data.get("teams"), list)
                or any(not isinstance(team, dict) for team in data["teams"])):
            raise RuntimeError("Office data has an unsupported or invalid format.")
        data.setdefault("archive", [])
        if not isinstance(data["archive"], list) or any(not isinstance(team, dict) for team in data["archive"]):
            raise RuntimeError("Office archive has an unsupported or invalid format.")
        return data

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".office-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def list_teams(self) -> list[dict]:
        return self._read()["teams"]

    def get_team(self, slug: str) -> dict | None:
        return next((team for team in self.list_teams() if team["slug"] == slug), None)

    def create_team(self, name: str, members: Iterable[str], lead: str) -> dict:
        name = name.strip()
        if not name or len(name) > 60 or any(ord(char) < 32 for char in name):
            raise ValidationError("Team name must be 1–60 printable characters.")
        if isinstance(members, (str, bytes)) or not isinstance(members, Iterable):
            raise ValidationError("Members must be a list of Hermes profiles.")
        member_list = list(members)
        if any(not isinstance(member, str) or not member.strip() for member in member_list):
            raise ValidationError("Each team member must be a Hermes profile name.")
        member_list = sorted(set(member_list))
        if not member_list:
            raise ValidationError("Choose at least one team member.")
        unknown = sorted(set(member_list) - self.profiles)
        if unknown:
            raise ValidationError("Unknown Hermes profile(s): " + ", ".join(unknown))
        if lead not in member_list:
            raise ValidationError("Team Lead must also be a team member.")
        slug = slugify(name)
        data = self._read()
        if any(team["slug"] == slug for team in data["teams"]):
            raise ValidationError("A team with this name already exists.")
        team = {
            "name": name,
            "slug": slug,
            "board_slug": f"office-{slug}",
            "lead": lead,
            "members": member_list,
            "status": "planned",
            "office_id": uuid.uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        data["teams"].append(team)
        self._write(data)
        return team

    def update_team(self, slug: str, changes: dict) -> dict:
        data = self._read()
        team = next((t for t in data["teams"] if t["slug"] == slug), None)
        if team is None:
            raise ValidationError("Team not found.")
        team.update(changes)
        self._write(data)
        return team

    def disband_team(self, slug: str) -> dict:
        data = self._read()
        team = next((t for t in data["teams"] if t["slug"] == slug), None)
        if team is None:
            raise ValidationError("Team not found.")
        data["teams"].remove(team)
        archived = {**team, "status": "disbanded", "disbanded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        data["archive"].append(archived)
        self._write(data)
        return archived


def discover_profiles(hermes_home: Path | None = None) -> list[dict]:
    """List the profiles Hermes itself recognises; fail closed on CLI errors."""
    executable = shutil.which("hermes")
    if not executable:
        raise RuntimeError("Hermes CLI was not found on PATH.")
    try:
        result = subprocess.run(
            [executable, "profile", "list"], capture_output=True, text=True,
            timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Could not read Hermes profiles.") from exc
    if result.returncode != 0:
        raise RuntimeError(f"Hermes profile list failed (exit {result.returncode}).")
    profiles = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 2:
            continue
        name = "default" if "(default)" in fields else fields[0].lstrip("◆●*")
        if name.casefold() in {"profile", "hermes", "usage"}:
            continue
        if re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            profiles.append({"name": name, "source": "Hermes"})
    unique = {item["name"]: item for item in profiles}
    if not unique:
        raise RuntimeError("Hermes returned no recognisable profile names.")
    return sorted(unique.values(), key=lambda p: p["name"].casefold())


