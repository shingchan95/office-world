from __future__ import annotations

import json
import hashlib
import os
import re
import secrets
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from meetings import MeetingStore, MeetingError
from auth import OfficeAuth, PasswordPolicyError
from office import OfficeStore, ValidationError, discover_profiles
from lifecycle import HermesCLI, LifecycleError, TeamLifecycle, resolve_kanban_home

ROOT = Path(__file__).resolve().parent
DATA_PATH = Path(os.environ.get("OFFICE_DATA", ROOT / "data" / "office.json")).expanduser()
ALLOWED_ORIGIN = os.environ.get("OFFICE_ALLOWED_ORIGIN", "http://127.0.0.1:8765")
AUTH_PATH = Path(os.environ.get("OFFICE_AUTH_FILE", Path.home() / ".local" / "state" / "office" / "auth.json")).expanduser()
AUTH = OfficeAuth(AUTH_PATH)
_SESSIONS: dict[str, float] = {}
_SESSION_LOCK = threading.RLock()
_SESSION_MAX_AGE = 12 * 60 * 60
_LOGIN_FAILURES: list[float] = []
_MUTATION_LOCK = threading.RLock()


def store(refresh_profiles: bool = True) -> OfficeStore:
    profiles = [p["name"] for p in discover_profiles()] if refresh_profiles else []
    return OfficeStore(DATA_PATH, profiles)


def public_team(team: dict) -> dict:
    activation = team.get("activation") or {}
    public_activation = {key: activation[key] for key in (
        "status", "platform", "lead", "kanban_baseline_enabled",
        "kanban_added_by_office", "board_created", "error", "recovery_error",
    ) if key in activation}
    fields = {key: team[key] for key in (
        "name", "slug", "board_slug", "lead", "members", "status",
        "created_at", "disbanded_at", "platform", "lifecycle_error",
    ) if key in team}
    if public_activation:
        fields["activation"] = public_activation
    return fields


def public_plan(plan: dict) -> dict:
    keys = {"plan_id", "slug", "board_slug", "lead", "members", "platform",
            "kanban_enabled_before", "kanban_baseline_enabled", "kanban_toolset_will_change",
            "board_will_be_created", "skill_name", "guidance_will_be_added_to", "guidance_will_be_removed",
            "archive_board", "disable_kanban", "other_teams_share_kanban"}
    result = {key: value for key, value in plan.items() if key in keys}
    if "member_targets" in plan:
        result["guidance_will_be_removed"] = [m["profile"] for m in plan["member_targets"]]
    return result


def lifecycle() -> TeamLifecycle:
    return TeamLifecycle(store(), HermesCLI(kanban_home=resolve_kanban_home()))


class Handler(BaseHTTPRequestHandler):
    server_version = "OfficeEnv/0.2"

    def log_message(self, format, *args):
        # Request bodies and query strings are not logged.
        route = urlsplit(self.path).path
        print(f"OfficeEnv: {self.command} {route} {args[1] if len(args) > 1 else ''}")

    def _local_host(self) -> bool:
        host = self.headers.get("Host", "")
        return bool(re.fullmatch(r"(?:localhost|127\.0\.0\.1|\[::1\])(?::[0-9]{1,5})?", host, re.I))

    def _guard_host(self) -> bool:
        if self._local_host():
            return True
        self._json(403, {"error": "Office accepts loopback Host headers only."})
        return False

    def _guard_origin(self) -> bool:
        if self.headers.get("Origin") == ALLOWED_ORIGIN:
            return True
        self._json(403, {"error": "Write request origin does not match the configured Office address."})
        return False

    def _json(self, status: int, payload: dict | list, headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _html(self, filename: str) -> None:
        body = (ROOT / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _session_key(self) -> str | None:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            morsel = cookie.get("office_session")
        except Exception:
            return None
        if morsel is None or not morsel.value:
            return None
        key = hashlib.sha256(morsel.value.encode("ascii", errors="ignore")).hexdigest()
        with _SESSION_LOCK:
            expires = _SESSIONS.get(key)
            if expires is None or expires <= time.monotonic():
                _SESSIONS.pop(key, None)
                return None
            return key

    def _issue_session(self) -> tuple[str, str]:
        token = secrets.token_urlsafe(32)
        key = hashlib.sha256(token.encode("ascii")).hexdigest()
        with _SESSION_LOCK:
            _SESSIONS[key] = time.monotonic() + _SESSION_MAX_AGE
        cookie = f"office_session={token}; Path=/; Max-Age={_SESSION_MAX_AGE}; HttpOnly; SameSite=Strict"
        return key, cookie

    def _clear_sessions(self) -> None:
        with _SESSION_LOCK:
            _SESSIONS.clear()

    def _protected(self, allow_change: bool = False) -> bool:
        if self._session_key() is None:
            self._json(401, {"error": "Sign in to Office."})
            return False
        try:
            if AUTH.must_change and not allow_change:
                self._json(403, {"error": "Change your password before using Office."})
                return False
        except (OSError, ValueError):
            self._json(503, {"error": "Office authentication state is unavailable."})
            return False
        return True

    def _login(self) -> None:
        global _LOGIN_FAILURES
        now = time.monotonic()
        _LOGIN_FAILURES = [stamp for stamp in _LOGIN_FAILURES if now - stamp < 60]
        if len(_LOGIN_FAILURES) >= 5:
            self._json(429, {"error": "Too many failed sign-in attempts. Wait one minute and try again."})
            return
        try:
            payload = self._payload()
        except OverflowError as exc:
            self._json(413, {"error": str(exc)})
            return
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": f"Invalid request: {exc}"})
            return
        try:
            username, password = payload.get("username", ""), payload.get("password", "")
            if not isinstance(username, str) or not isinstance(password, str):
                self._json(400, {"error": "Enter a username and password."})
                return
            if not AUTH.authenticate(username, password):
                _LOGIN_FAILURES.append(now)
                self._json(401, {"error": "Username or password is incorrect."})
                return
            _LOGIN_FAILURES = []
            _, cookie = self._issue_session()
            self._json(200, {"must_change": AUTH.must_change}, {"Set-Cookie": cookie})
        except (ValueError, OSError):
            self._json(503, {"error": "Office authentication state is unavailable."})

    def _change_password(self) -> None:
        if not self._protected(allow_change=True):
            return
        try:
            payload = self._payload()
        except OverflowError as exc:
            self._json(413, {"error": str(exc)})
            return
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": f"Invalid request: {exc}"})
            return
        try:
            password = payload.get("password", "")
            if not isinstance(password, str):
                raise PasswordPolicyError("Enter a new password.")
            if not AUTH.must_change:
                self._json(403, {"error": "The first-login password change is already complete."})
                return
            AUTH.change_password(password, force_change=False)
            self._clear_sessions()
            self._json(200, {"must_change": False}, {"Set-Cookie": "office_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"})
        except PasswordPolicyError as exc:
            self._json(400, {"error": str(exc)})
        except (ValueError, OSError):
            self._json(503, {"error": "Office could not save the new password safely."})

    def _payload(self) -> dict:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("Send an application/json request.")
        raw_length = self.headers.get("Content-Length", "")
        if not raw_length.isdigit():
            raise ValueError("Invalid Content-Length.")
        length = int(raw_length)
        if length > 32768:
            raise OverflowError("Request too large.")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("JSON request must be an object.")
        return value

    def do_GET(self):
        if not self._guard_host():
            return
        path = urlsplit(self.path).path
        if path in {"/", "/index.html"}:
            if self._session_key() is None:
                self._html("login.html")
                return
            try:
                self._html("change_password.html" if AUTH.must_change else "index.html")
            except (OSError, ValueError):
                self._json(503, {"error": "Office authentication state is unavailable."})
            return
        if path == "/api/profiles":
            if not self._protected():
                return
            try:
                self._json(200, discover_profiles())
            except RuntimeError as exc:
                self._json(503, {"error": str(exc)})
            return
        if path == "/api/meetings":
            if not self._protected():
                return
            try:
                query = parse_qs(urlsplit(self.path).query)
                self._json(200, MeetingStore(DATA_PATH).list_meetings(query.get("team", [None])[0]))
            except MeetingError:
                self._json(503, {"error": "Meeting history is unavailable; no healthy/empty state is implied."})
            return
        if path == "/api/teams":
            if not self._protected():
                return
            try:
                self._json(200, [public_team(t) for t in store(refresh_profiles=False).list_teams()])
            except RuntimeError as exc:
                self._json(500, {"error": str(exc)})
            return
        if path in {"/api/activation-plan", "/api/disband-plan"}:
            if not self._protected():
                return
            query = parse_qs(urlsplit(self.path).query)
            slug = query.get("slug", [""])[0]
            try:
                manager = lifecycle()
                plan = (manager.preview_activation(slug, query.get("platform", [""])[0])
                        if path == "/api/activation-plan" else manager.preview_disband(slug))
                self._json(200, public_plan(plan))
            except (LifecycleError, ValidationError) as exc:
                self._json(409, {"error": str(exc)})
            except RuntimeError as exc:
                self._json(503, {"error": str(exc)})
            return
        self._json(404, {"error": "Not found"})

    def do_POST(self):
        if not self._guard_host():
            return
        if not self._guard_origin():
            return
        if self.path == "/api/login":
            self._login()
            return
        if self.path == "/api/change-password":
            self._change_password()
            return
        if self.path == "/api/logout":
            if not self._protected(allow_change=True):
                return
            self._clear_sessions()
            self._json(200, {"ok": True}, {"Set-Cookie": "office_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"})
            return
        if self.path not in {"/api/teams", "/api/activate", "/api/disband"}:
            self._json(404, {"error": "Not found"})
            return
        if not self._protected():
            return
        try:
            payload = self._payload()
        except OverflowError as exc:
            self._json(413, {"error": str(exc)})
            return
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": f"Invalid request: {exc}"})
            return
        try:
            with _MUTATION_LOCK:
                if self.path == "/api/teams":
                    result = store().create_team(payload.get("name", ""), payload.get("members", []), payload.get("lead", ""))
                elif self.path == "/api/activate":
                    result = lifecycle().activate(payload.get("slug", ""), payload.get("platform", ""),
                                                  payload.get("plan_id", ""), payload.get("confirmed") is True)
                else:
                    planned = store(refresh_profiles=False).get_team(payload.get("slug", ""))
                    if planned and planned.get("status") == "planned":
                        if payload.get("confirmed") is not True:
                            raise LifecycleError("Archiving a planned team requires explicit confirmation.")
                        result = store(refresh_profiles=False).disband_team(planned["slug"])
                    else:
                        result = lifecycle().disband(payload.get("slug", ""), payload.get("plan_id", ""),
                                                     payload.get("confirmed") is True)
            self._json(201, public_team(result))
        except LifecycleError as exc:
            self._json(409, {"error": str(exc)})
        except ValidationError as exc:
            self._json(400, {"error": str(exc)})
        except RuntimeError as exc:
            self._json(503, {"error": str(exc)})
        except (AttributeError, TypeError) as exc:
            self._json(400, {"error": f"Invalid request fields: {exc}"})
        except OSError:
            self._json(500, {"error": "Could not save Office data safely."})


def main() -> None:
    address = os.environ.get("OFFICE_BIND", "127.0.0.1")
    port = int(os.environ.get("OFFICE_PORT", "8765"))
    if address not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("LAN binding is disabled; Office is loopback-only in this build.")
    server = ThreadingHTTPServer((address, port), Handler)
    print(f"Office environment available locally at http://{address}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
