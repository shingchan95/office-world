import http.cookies
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import server
from auth import OfficeAuth


class OfficeAuthHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.old_auth = getattr(server, "AUTH", None)
        self.old_origin = server.ALLOWED_ORIGIN
        self.old_sessions = getattr(server, "_SESSIONS", {}).copy()
        server.AUTH = OfficeAuth(self.root / "auth.json")
        server.AUTH.initialize("tommy", "temporary-passphrase", force_change=True)
        server._SESSIONS = {}
        self.http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.http.server_port}"
        server.ALLOWED_ORIGIN = self.base

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)
        if self.old_auth is None:
            del server.AUTH
        else:
            server.AUTH = self.old_auth
        server.ALLOWED_ORIGIN = self.old_origin
        server._SESSIONS = self.old_sessions
        self.tmp.cleanup()

    def request(self, path, payload=None, cookie=None):
        body = None if payload is None else json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            headers["Origin"] = server.ALLOWED_ORIGIN
        if cookie:
            headers["Cookie"] = cookie
        req = urllib.request.Request(
            self.base + path, data=body,
            method="GET" if payload is None else "POST", headers=headers,
        )
        try:
            response = urllib.request.urlopen(req)
            return response.status, response.headers, response.read()
        except urllib.error.HTTPError as exc:
            result = (exc.code, exc.headers, exc.read())
            exc.close()
            return result

    def login(self, password):
        status, headers, body = self.request(
            "/api/login", {"username": "tommy", "password": password}
        )
        self.assertEqual(status, 200, body.decode())
        parsed = http.cookies.SimpleCookie()
        parsed.load(headers.get("Set-Cookie", ""))
        return f"office_session={parsed['office_session'].value}", json.loads(body)

    def test_first_login_is_forced_to_change_password_before_app_access(self):
        status, _, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"Sign in", page)

        cookie, result = self.login("temporary-passphrase")
        self.assertTrue(result["must_change"])
        status, _, page = self.request("/", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertIn(b"Change your password", page)

        status, _, _ = self.request("/api/profiles", cookie=cookie)
        self.assertEqual(status, 403)

        status, _, body = self.request(
            "/api/change-password", {"password": "eight123"}, cookie
        )
        self.assertEqual(status, 200, body.decode())
        self.assertFalse(json.loads(body)["must_change"])
        status, _, _ = self.request("/api/profiles", cookie=cookie)
        self.assertEqual(status, 401)

        new_cookie, result = self.login("eight123")
        self.assertFalse(result["must_change"])
        status, _, page = self.request("/", cookie=new_cookie)
        self.assertEqual(status, 200)
        self.assertIn(b"Hermes workspace", page)

    def test_wrong_initial_password_is_rejected(self):
        status, _, _ = self.request(
            "/api/login", {"username": "tommy", "password": "wrong-password"}
        )
        self.assertEqual(status, 401)

    def test_mutation_requires_authenticated_session(self):
        status, _, _ = self.request("/api/teams", {"name": "Nope"})
        self.assertEqual(status, 401)
        self.assertFalse((self.root / "office.json").exists())


if __name__ == "__main__":
    unittest.main()
