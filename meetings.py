"""Local Office meeting records; invitations are not evidence of attendance.

Co-operative same-UNIX-user enforcement, not an ACL against shell access.
No chat scanning, dispatch, scheduling, profile writes or network operations.
"""
from __future__ import annotations

import json
import fcntl
import threading
import time
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class MeetingError(ValueError):
    """Invalid, unauthorised or conflicting meeting operation."""


_locks_guard = threading.Lock()
_locks = {}
_depth = threading.local()


@contextmanager
def registry_lock(registry_path):
    """Shared lifecycle/mutation lock, nested-reentrant in the owning thread.

    Acquire before reading registry state; Office disband must use this too.
    Lock acquisition is bounded to three seconds. Never remove the lock file.
    """
    path = Path(registry_path).resolve().with_name('.office-meetings.lock')
    with _locks_guard:
        lock = _locks.setdefault(str(path), threading.RLock())
    if not lock.acquire(timeout=3):
        raise MeetingError('Office meeting lock is busy.')
    depths = getattr(_depth, 'paths', None)
    if depths is None:
        depths = _depth.paths = {}
    fd = None
    try:
        if str(path) not in depths:
            try:
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
                os.fchmod(fd, 0o600)
                deadline = time.monotonic() + 3
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            raise MeetingError('Office meeting lock is busy.')
                        time.sleep(.02)
            except OSError as exc:
                raise MeetingError('Cannot acquire Office meeting lock safely.') from exc
        depths[str(path)] = depths.get(str(path), 0) + 1
        try:
            yield
        finally:
            depths[str(path)] -= 1
            if not depths[str(path)]:
                del depths[str(path)]
    finally:
        if fd is not None:
            os.close(fd)
        lock.release()


def _text(value, limit=512):
    if (not isinstance(value, str) or not value.strip() or len(value) > limit
            or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value)):
        raise MeetingError('Expected bounded nonempty text without control characters.')
    return value


def _source(value):
    if not isinstance(value, dict) or set(value) != {'platform', 'chat_id', 'thread_id', 'message_id', 'reply_to'}:
        raise MeetingError('Source must contain exactly platform, chat_id, thread_id, message_id, reply_to.')
    for key, item in value.items():
        if key in ('thread_id', 'reply_to') and item is None:
            continue
        _text(item)
    return dict(value)


def _route(source):
    return tuple(source[k] for k in ('platform', 'chat_id', 'thread_id'))


def _json_pairs(pairs):
    """Do not silently accept ambiguous duplicate fields in persisted data."""
    value = {}
    for key, item in pairs:
        if key in value:
            raise MeetingError('Duplicate JSON fields are not permitted.')
        value[key] = item
    return value


def _now():
    return datetime.now(timezone.utc).isoformat()


class MeetingStore:
    def __init__(self, registry_path: Path):
        self.registry_path = Path(registry_path).absolute()
        self.path = self.registry_path.with_name('meetings.sqlite3')

    @contextmanager
    def _db(self, write=False):
        if not write and not self.path.exists():
            yield None
            return
        try:
            created = False
            if write:
                self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                if not self.path.exists():
                    fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
                    os.close(fd)
                    created = True
                if self.path.is_symlink() or not self.path.is_file():
                    raise MeetingError('Meeting database must be a regular local file.')
                os.chmod(self.path, 0o600)
            if self.path.stat().st_size > 256_000_000:
                raise MeetingError('Meeting database exceeds size limit.')
            db = sqlite3.connect(self.path.as_uri() + ('?mode=rw' if write else '?mode=ro'), uri=True, timeout=3)
            try:
                db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 8_000_000)
                db.execute('PRAGMA trusted_schema=OFF')
                if write:
                    db.execute('BEGIN IMMEDIATE')
                if created:
                    db.execute('CREATE TABLE meetings (id TEXT PRIMARY KEY, record TEXT NOT NULL)')
                    db.execute('PRAGMA user_version=1')
                if db.execute('PRAGMA user_version').fetchone()[0] != 1:
                    raise MeetingError('Unsupported or missing meeting database schema.')
                yield db
                if write:
                    db.commit()
            finally:
                db.close()
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, RecursionError) as exc:
            if isinstance(exc, MeetingError):
                raise
            raise MeetingError('Cannot access meeting data safely.') from exc

    def _records(self, db):
        if db is None:
            return []
        rows = db.execute('SELECT id, record FROM meetings ORDER BY rowid LIMIT 10001').fetchall()
        if len(rows) > 10000:
            raise MeetingError('Meeting record limit exceeded.')
        records = []
        for ident, raw in rows:
            m = json.loads(raw, object_pairs_hook=_json_pairs)
            self._validate_record(m)
            if m['id'] != ident:
                raise MeetingError('Meeting record identifier mismatch.')
            records.append(m)
        return records

    @staticmethod
    def _validate_record(m):
        required = {'id', 'team_office_id', 'team_slug', 'actor', 'title', 'agenda', 'participants', 'source', 'status', 'revision', 'created_at', 'updated_at', 'events'}
        if not isinstance(m, dict) or set(m) != required:
            raise MeetingError('Invalid meeting record shape.')
        _text(m['id'])
        if str(uuid.UUID(m['id'])) != m['id']:
            raise MeetingError('Invalid meeting identifier.')
        for k in ('team_office_id', 'team_slug', 'actor', 'created_at', 'updated_at'):
            _text(m[k])
        _text(m['title'], 160)
        if not isinstance(m['agenda'], list) or len(m['agenda']) > 20:
            raise MeetingError('Invalid stored agenda.')
        for item in m['agenda']:
            _text(item, 500)
        people = m['participants']
        if not isinstance(people, list) or not 1 <= len(people) <= 50:
            raise MeetingError('Invalid stored invitations.')
        for person in people:
            _text(person)
        if len(set(people)) != len(people) or m['actor'] not in people:
            raise MeetingError('Invalid stored invitations.')
        _source(m['source'])
        if not isinstance(m['events'], list) or len(m['events']) > 500 or type(m['revision']) is not int or m['revision'] != len(m['events']) + 1:
            raise MeetingError('Invalid event history revision.')
        status = 'active'
        seen = {m['source']['message_id']: m['actor']}
        for revision, e in enumerate(m['events'], 2):
            if not isinstance(e, dict):
                raise MeetingError('Invalid event history.')
            transition = e.get('kind') == 'transition'
            fields = {'actor', 'source', 'revision', 'created_at', 'kind'} | ({'action'} if transition else {'text'})
            if set(e) != fields or type(e['revision']) is not int or e['revision'] != revision:
                raise MeetingError('Invalid event history shape.')
            _text(e['actor'])
            if e['actor'] not in people:
                raise MeetingError('Stored event actor was not invited.')
            _text(e['created_at'])
            src = _source(e['source'])
            if _route(src) != _route(m['source']) or src['message_id'] in seen:
                raise MeetingError('Invalid event source history.')
            if src['thread_id'] is None and (src['reply_to'] != m['source']['message_id'] and seen.get(src['reply_to']) != e['actor']):
                raise MeetingError('Invalid reply evidence history.')
            seen[src['message_id']] = e['actor']
            if transition:
                if not isinstance(e['action'], str):
                    raise MeetingError('Invalid stored transition.')
                status = {'active': {'pause': 'paused', 'end': 'ended', 'cancel': 'cancelled'}, 'paused': {'resume': 'active', 'end': 'ended', 'cancel': 'cancelled'}}.get(status, {}).get(e['action'])
                if status is None:
                    raise MeetingError('Invalid stored transition.')
            else:
                if status != 'active' or not isinstance(e['kind'], str) or e['kind'] not in ('contribution', 'agenda', 'decision', 'question', 'summary'):
                    raise MeetingError('Invalid stored entry.')
                _text(e['text'], 8000)
        if m['status'] != status:
            raise MeetingError('Invalid meeting status history.')

    def list_meetings(self, team_slug=None):
        with self._db() as db:
            return [m for m in self._records(db) if team_slug is None or m['team_slug'] == team_slug]

    def get_meeting(self, id):
        return next((m for m in self.list_meetings() if m['id'] == id), None)

    def open_for_team(self, team_office_id):
        return [m for m in self.list_meetings() if m['team_office_id'] == team_office_id and m['status'] in ('active', 'paused')]

    def _team(self, actor, slug, office_id=None):
        _text(actor)
        _text(slug)
        try:
            if self.registry_path.stat().st_size > 4_000_000:
                raise MeetingError('Office registry exceeds size limit.')
            data = json.loads(self.registry_path.read_text(encoding='utf-8'), object_pairs_hook=_json_pairs)
            if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1:
                raise ValueError()
            teams = data['teams']
            archive = data.get('archive', [])
            if not isinstance(teams, list) or not isinstance(archive, list):
                raise ValueError()
            seen_ids, seen_slugs = set(), set()
            for t in teams + archive:
                if not isinstance(t, dict):
                    raise ValueError()
                for field in ('slug', 'office_id', 'status'):
                    _text(t[field])
                members = t['members']
                if not isinstance(members, list) or not members or len(members) > 500:
                    raise ValueError()
                for member in members:
                    _text(member)
                if len(set(members)) != len(members) or t['office_id'] in seen_ids:
                    raise ValueError()
                seen_ids.add(t['office_id'])
            for t in teams:
                if t['slug'] in seen_slugs:
                    raise ValueError()
                seen_slugs.add(t['slug'])
            team = next((t for t in teams if t['slug'] == slug), None)
        except (OSError, ValueError, KeyError, TypeError, UnicodeError, RecursionError) as exc:
            raise MeetingError('Cannot read Office registry safely.') from exc
        if team is None or team['status'] != 'active' or actor not in team['members'] or (office_id is not None and team['office_id'] != office_id):
            raise MeetingError('Actor must belong to the active team instance.')
        return team

    def start(self, actor, team_slug, title, agenda, participants, source, explicit_start=False):
        if explicit_start is not True:
            raise MeetingError('Explicit confirmed start intent is required.')
        _text(title, 160)
        if not isinstance(agenda, list) or len(agenda) > 20:
            raise MeetingError('Agenda must be a list of at most 20 items.')
        for item in agenda:
            _text(item, 500)
        if not isinstance(participants, list) or not 1 <= len(participants) <= 50:
            raise MeetingError('Participants must be a list of 1–50 members.')
        for participant in participants:
            _text(participant)
        if len(set(participants)) != len(participants) or actor not in participants:
            raise MeetingError('Participants must be unique and include actor.')
        source = _source(source)
        with registry_lock(self.registry_path):
            team = self._team(actor, team_slug)
            if not set(participants) <= set(team['members']):
                raise MeetingError('All invitees must be team members.')
            with self._db(True) as db:
                records = self._records(db)
                for m in records:
                    if _route(m['source']) == _route(source):
                        if m['source']['message_id'] == source['message_id']:
                            if (m['team_office_id'] == team['office_id'] and m['source'] == source and all(m[k] == v for k, v in dict(actor=actor, title=title, agenda=agenda, participants=participants).items())):
                                return m
                            raise MeetingError('Start message already used with different payload.')
                        if m['status'] in ('active', 'paused'):
                            raise MeetingError('An open meeting already occupies this source route.')
                now = _now()
                meeting = dict(id=str(uuid.uuid4()), team_office_id=team['office_id'], team_slug=team_slug, actor=actor, title=title, agenda=agenda, participants=participants, source=source, status='active', revision=1, created_at=now, updated_at=now, events=[])
                db.execute('INSERT INTO meetings VALUES (?, ?)', (meeting['id'], json.dumps(meeting)))
                return meeting

    def append(self, actor, meeting_id, expected_revision, kind, text, source):
        if not isinstance(kind, str) or kind not in ('contribution', 'agenda', 'decision', 'question', 'summary'):
            raise MeetingError('Unsupported entry kind.')
        _text(text, 8000)
        return self._event(actor, meeting_id, expected_revision, dict(kind=kind, text=text), source)

    def transition(self, actor, meeting_id, expected_revision, action, source):
        if not isinstance(action, str) or action not in ('pause', 'resume', 'end', 'cancel'):
            raise MeetingError('Unsupported transition.')
        return self._event(actor, meeting_id, expected_revision, dict(kind='transition', action=action), source)

    def _event(self, actor, meeting_id, expected_revision, payload, source):
        _text(actor)
        _text(meeting_id)
        if type(expected_revision) is not int or expected_revision < 1:
            raise MeetingError('Expected revision must be a positive integer.')
        source = _source(source)
        with registry_lock(self.registry_path):
            # Do not create a missing database when attempting to edit a record.
            if not self.path.exists():
                raise MeetingError('Meeting not found.')
            with self._db(True) as db:
                m = next((m for m in self._records(db) if m['id'] == meeting_id), None)
                if m is None:
                    raise MeetingError('Meeting not found.')
                self._team(actor, m['team_slug'], m['team_office_id'])
                if actor not in m['participants']:
                    raise MeetingError('Actor must be an invited meeting participant.')
                if _route(source) != _route(m['source']):
                    raise MeetingError('Source route cannot change.')
                if source['message_id'] == m['source']['message_id']:
                    raise MeetingError('Start message cannot be reused for an event.')
                for event in m['events']:
                    if event['source']['message_id'] == source['message_id']:
                        if event['source'] == source and event['actor'] == actor and all(event.get(k) == v for k, v in payload.items()):
                            return m
                        raise MeetingError('Message already used with different event payload.')
                if m['revision'] != expected_revision:
                    raise MeetingError('Meeting revision conflict; read the latest record.')
                if source['thread_id'] is None:
                    replies = {m['source']['message_id']} | {e['source']['message_id'] for e in m['events'] if e['actor'] == actor}
                    if source['reply_to'] not in replies:
                        raise MeetingError('Unthreaded receipt must reply to start or actor’s own accepted event.')
                if payload['kind'] == 'transition':
                    allowed = {'active': {'pause': 'paused', 'end': 'ended', 'cancel': 'cancelled'}, 'paused': {'resume': 'active', 'end': 'ended', 'cancel': 'cancelled'}}
                    status = allowed.get(m['status'], {}).get(payload['action'])
                    if status is None:
                        raise MeetingError('Transition is not allowed from current status.')
                    m['status'] = status
                elif m['status'] != 'active':
                    raise MeetingError('Entries require an active meeting.')
                if len(m['events']) >= 500:
                    raise MeetingError('Meeting event limit reached.')
                now = _now()
                m['revision'] += 1
                m['updated_at'] = now
                m['events'].append(dict(actor=actor, source=source, revision=m['revision'], created_at=now, **payload))
                db.execute('UPDATE meetings SET record = ? WHERE id = ?', (json.dumps(m), meeting_id))
                return m
