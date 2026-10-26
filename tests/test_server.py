import json
import http.cookies
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer

import server
from auth import OfficeAuth


class OfficeHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        profile_root = root / ".hermes"
        (profile_root / "profiles" / "oscar").mkdir(parents=True)
        (profile_root / "profiles" / "artist").mkdir()
        (profile_root / "config.yaml").write_text("profile root fixture\n", encoding="utf-8")
        self.old_data = server.DATA_PATH
        self.old_discover = server.discover_profiles
        self.old_allowed_origin = getattr(server, "ALLOWED_ORIGIN", None)
        self.old_auth = server.AUTH
        self.old_sessions = server._SESSIONS.copy()
        server.DATA_PATH = root / "office.json"
        server.AUTH = OfficeAuth(root / "auth.json")
        server.AUTH.initialize("tommy", "temporary-passphrase", force_change=False)
        server._SESSIONS = {}
        server.discover_profiles = lambda *_: [
            {"name": "oscar", "source": "Hermes"},
            {"name": "artist", "source": "Hermes"},
        ]
        self.http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.http.server_port}"
        server.ALLOWED_ORIGIN = self.base
        self.cookie = self._login()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)
        server.DATA_PATH = self.old_data
        server.discover_profiles = self.old_discover
        server.AUTH = self.old_auth
        server._SESSIONS = self.old_sessions
        if self.old_allowed_origin is None:
            del server.ALLOWED_ORIGIN
        else:
            server.ALLOWED_ORIGIN = self.old_allowed_origin
        self.tmp.cleanup()

    def request_json(self, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            headers["Origin"] = server.ALLOWED_ORIGIN
        if hasattr(self, "cookie"):
            headers["Cookie"] = self.cookie
        req = urllib.request.Request(self.base + path, data=body, method="GET" if payload is None else "POST", headers=headers)
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read())

    def _login(self):
        req = urllib.request.Request(
            self.base + "/api/login",
            data=json.dumps({"username": "tommy", "password": "temporary-passphrase"}).encode(),
            method="POST",
            headers={"Origin": server.ALLOWED_ORIGIN, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as response:
            cookie = http.cookies.SimpleCookie()
            cookie.load(response.headers.get("Set-Cookie", ""))
            return f"office_session={cookie['office_session'].value}"

    def test_profiles_and_team_api(self):
        status, profiles = self.request_json("/api/profiles")
        self.assertEqual(status, 200)
        self.assertEqual({x["name"] for x in profiles}, {"oscar", "artist"})
        status, team = self.request_json("/api/teams", {"name": "Art Room", "members": ["oscar", "artist"], "lead": "oscar"})
        self.assertEqual(status, 201)
        self.assertEqual(team["board_slug"], "office-art-room")
        _, active = self.request_json("/api/teams")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["members"], ["artist", "oscar"])

    def test_ui_discloses_registry_only_scope(self):
        req = urllib.request.Request(self.base + "/", headers={"Cookie": self.cookie})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode()
        self.assertIn("Preview exact changes", html)
        self.assertIn("LAN · AUTHENTICATED", html)
        self.assertIn("authenticated HTTP gateway", html)
        self.assertIn("on-demand cooperation skill", html)
        self.assertIn("SOUL.md untouched", html)
        self.assertIn("not a security boundary", html)

    def test_meeting_history_api_is_authenticated_and_read_only(self):
        status, rows = self.request_json("/api/meetings")
        self.assertEqual(status, 200)
        self.assertEqual(rows, [])
        self.assertFalse(server.DATA_PATH.with_name("meetings.sqlite3").exists())
        req = urllib.request.Request(self.base + "/api/meetings")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req)
        self.assertEqual(caught.exception.code, 401)
        caught.exception.close()

    def test_meeting_api_reads_updates_filters_and_retained_history(self):
        from meetings import MeetingStore
        registry = server.store()
        team = registry.create_team("Review", ["oscar", "artist"], "oscar")
        registry.update_team(team["slug"], {"status": "active"})
        meetings = MeetingStore(server.DATA_PATH)
        source = dict(platform="telegram", chat_id="fixture", thread_id=None, message_id="1", reply_to=None)
        meeting = meetings.start("artist", team["slug"], "<script>not executable</script>", ["Review"], ["artist"], source, explicit_start=True)
        _, rows = self.request_json("/api/meetings")
        self.assertEqual(rows[0]["id"], meeting["id"])
        meetings.append("artist", meeting["id"], 1, "contribution", "Actual fixture reply", dict(source, message_id="2", reply_to="1"))
        _, rows = self.request_json("/api/meetings?team=review")
        self.assertEqual(rows[0]["events"][0]["text"], "Actual fixture reply")
        self.assertEqual(self.request_json("/api/meetings?team=other")[1], [])
        meetings.transition("artist", meeting["id"], 2, "end", dict(source, message_id="3", reply_to="1"))
        registry.disband_team(team["slug"])
        self.assertEqual(self.request_json("/api/meetings")[1][0]["status"], "ended")

    def test_corrupt_meeting_history_is_unavailable_not_empty(self):
        server.DATA_PATH.with_name("meetings.sqlite3").write_bytes(b"not sqlite")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request_json("/api/meetings")
        self.assertEqual(caught.exception.code, 503)
        caught.exception.close()

    def test_ui_shows_conversation_led_live_meetings(self):
        req = urllib.request.Request(self.base + "/", headers={"Cookie": self.cookie})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode()
        self.assertIn('id="meetings"', html)
        self.assertIn("Started in conversation", html)
        self.assertIn("Invited participants", html)
        self.assertIn("/api/meetings", html)
        self.assertIn("Meeting history is retained", html)

    def test_public_team_hides_private_snapshot_paths_and_blocks(self):
        value = server.public_team({
            "name": "Sample", "slug": "sample", "status": "active",
            "activation": {"status": "active", "members": [{"path": "/private/SOUL.md", "block": "private instructions"}]},
        })
        encoded = json.dumps(value)
        self.assertNotIn("/private/SOUL.md", encoded)
        self.assertNotIn("private instructions", encoded)

    def test_rejects_non_loopback_host_header(self):
        req = urllib.request.Request(
            self.base + "/api/teams", data=b"{}", method="POST",
            headers={"Host": "attacker.example", "Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req)
        self.assertEqual(caught.exception.code, 403)
        caught.exception.close()

    def test_rejects_cross_origin_post_before_processing_payload(self):
        req = urllib.request.Request(
            self.base + "/api/teams", data=b"{}", method="POST",
            headers={"Origin": "https://attacker.example", "Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req)
        self.assertEqual(caught.exception.code, 403)
        caught.exception.close()
        self.assertFalse(server.DATA_PATH.exists())

    def test_rejects_post_without_origin_before_processing_payload(self):
        req = urllib.request.Request(
            self.base + "/api/teams", data=b"{}", method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req)
        self.assertEqual(caught.exception.code, 403)
        caught.exception.close()
        self.assertFalse(server.DATA_PATH.exists())

    def test_unknown_route_is_not_served(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.base + "/../../etc/passwd")
        self.assertEqual(caught.exception.code, 404)
        caught.exception.close()


if __name__ == "__main__":
    unittest.main()
