from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import tempfile
from pathlib import Path


_SCRYPT_N = 1 << 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_BYTES = 32
_SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 8


class PasswordPolicyError(ValueError):
    """Raised when a replacement password does not meet local policy."""


class OfficeAuth:
    """Private, file-backed password store for the Office LAN application."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    @property
    def must_change(self) -> bool:
        return self._read()["must_change"]

    def initialize(self, username: str, password: str, *, force_change: bool = True) -> None:
        if self.path.exists():
            raise FileExistsError("Office authentication is already initialized.")
        if not isinstance(username, str) or not username.strip():
            raise ValueError("A username is required.")
        if not isinstance(password, str) or not password:
            raise ValueError("An initial password is required.")
        record = self._new_record(username.strip(), password, force_change)
        self._write(record)

    def authenticate(self, username: str, password: str) -> bool:
        record = self._read()
        supplied_user = username if isinstance(username, str) else ""
        supplied_password = password if isinstance(password, str) else ""
        user_ok = hmac.compare_digest(supplied_user.encode(), record["username"].encode())
        salt = base64.b64decode(record["salt"], validate=True)
        expected = base64.b64decode(record["password_hash"], validate=True)
        actual = self._derive(supplied_password, salt)
        return user_ok and hmac.compare_digest(actual, expected)

    def change_password(self, password: str, *, force_change: bool = False) -> None:
        if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
            raise PasswordPolicyError(
                f"Choose a password with at least {MIN_PASSWORD_LENGTH} characters."
            )
        record = self._read()
        record.update(self._password_fields(password))
        record["must_change"] = bool(force_change)
        self._write(record)

    @staticmethod
    def _derive(password: str, salt: bytes) -> bytes:
        return hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=_SCRYPT_N,
            r=_SCRYPT_R, p=_SCRYPT_P, dklen=_SCRYPT_BYTES,
            maxmem=64 * 1024 * 1024,
        )

    @classmethod
    def _password_fields(cls, password: str) -> dict[str, str]:
        salt = os.urandom(_SALT_BYTES)
        digest = cls._derive(password, salt)
        return {
            "salt": base64.b64encode(salt).decode("ascii"),
            "password_hash": base64.b64encode(digest).decode("ascii"),
        }

    @classmethod
    def _new_record(cls, username: str, password: str, force_change: bool) -> dict:
        return {
            "version": 1,
            "username": username,
            **cls._password_fields(password),
            "must_change": bool(force_change),
        }

    def _read(self) -> dict:
        try:
            record = json.loads(self.path.read_text(encoding="utf-8"))
            if (not isinstance(record, dict) or record.get("version") != 1
                    or not isinstance(record.get("username"), str)
                    or not isinstance(record.get("salt"), str)
                    or not isinstance(record.get("password_hash"), str)
                    or not isinstance(record.get("must_change"), bool)):
                raise ValueError
            base64.b64decode(record["salt"], validate=True)
            base64.b64decode(record["password_hash"], validate=True)
            return record
        except (OSError, json.JSONDecodeError, TypeError, KeyError) as exc:
            raise ValueError("Office authentication state is unavailable or invalid.") from exc
        except Exception as exc:
            if isinstance(exc, ValueError) and str(exc) == "Office authentication state is unavailable or invalid.":
                raise
            raise ValueError("Office authentication state is unavailable or invalid.") from exc

    def _write(self, record: dict) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".office-auth-", dir=self.path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(record, stream, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)
            directory_fd = os.open(self.path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
