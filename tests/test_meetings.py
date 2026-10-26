from contextlib import closing
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from meetings import MeetingStore, MeetingError, registry_lock


class MeetingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.registry = Path(self.tmp.name) / 'office.json'
        self.data = {'version': 1, 'teams': [{'slug': 'ops', 'office_id': 'team-1', 'status': 'active', 'members': ['alice', 'bob']}], 'archive': []}
        self.save()
        self.source = dict(platform='telegram', chat_id='-001', thread_id=None, message_id='0001', reply_to=None)

    def save(self):
        self.registry.write_text(json.dumps(self.data))

    def store(self):
        self.assertIsNotNone(MeetingStore, 'MeetingStore implementation is missing')
        return MeetingStore(self.registry)

    def start(self, **changes):
        args = dict(actor='alice', team_slug='ops', title='Review', agenda=['Risks'], participants=['alice', 'bob'], source=self.source, explicit_start=True)
        args.update(changes)
        return self.store().start(**args)

    def test_start_persists_and_reads_without_registry_changes(self):
        before = self.registry.read_bytes()
        meeting = self.start()
        self.assertEqual(meeting['revision'], 1)
        self.assertEqual(meeting['status'], 'active')
        self.assertEqual(meeting['team_office_id'], 'team-1')
        self.assertEqual(meeting['source'], self.source)
        self.assertEqual(self.store().get_meeting(meeting['id']), meeting)
        self.assertEqual(self.store().list_meetings('ops'), [meeting])
        self.assertEqual(self.store().open_for_team('team-1'), [meeting])
        self.assertEqual(self.registry.read_bytes(), before)
        self.assertEqual(self.registry.with_name('meetings.sqlite3').stat().st_mode & 0o777, 0o600)

    def test_start_requires_explicit_intent_membership_and_valid_fields(self):
        invalid = [dict(explicit_start=False), dict(explicit_start=1), dict(actor='mallory'), dict(participants=['bob']), dict(participants=['alice', 'mallory']), dict(participants='alice'), dict(participants=['alice', 'alice']), dict(title='x'*161), dict(title='bad\n'), dict(agenda=['x']*21), dict(agenda=['x'*501]), dict(team_slug='missing'), dict(source={**self.source, 'extra': 'x'}), dict(source={**self.source, 'message_id': 1}), dict(source={**self.source, 'chat_id': 'a\x00b'})]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(MeetingError):
                self.start(**change)
        self.assertFalse(self.registry.with_name('meetings.sqlite3').exists())

    def test_start_idempotency_and_exclusive_route_across_teams(self):
        first = self.start()
        self.assertEqual(self.start(), first)
        with self.assertRaises(MeetingError):
            self.start(title='different')
        with self.assertRaises(MeetingError):
            self.start(source={**self.source, 'message_id': '2'})
        self.data['teams'].append({**self.data['teams'][0], 'slug': 'other', 'office_id': 'team-2'})
        self.save()
        with self.assertRaises(MeetingError):
            self.start(team_slug='other', source={**self.source, 'message_id': '2'})
        second = self.start(source={**self.source, 'thread_id': 'topic', 'message_id': '2'})
        self.assertNotEqual(second['id'], first['id'])

    def test_reads_do_not_create_and_registry_fails_closed(self):
        self.assertEqual(self.store().list_meetings(), [])
        self.assertIsNone(self.store().get_meeting('unknown'))
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [self.registry])
        for data in [{}, {'version': 1, 'teams': [{}]}, {**self.data, 'teams': [{**self.data['teams'][0], 'members': 'alice'}]}, {**self.data, 'teams': [{**self.data['teams'][0], 'status': 'planned'}]}]:
            self.registry.write_text(json.dumps(data))
            with self.subTest(data=data), self.assertRaises(MeetingError):
                self.start()
        self.registry.unlink()
        with self.assertRaises(MeetingError):
            self.start()

    def test_duplicate_and_over_nested_registry_fail_closed(self):
        duplicate = json.dumps(self.data).replace('"version": 1', '"version": 0, "version": 1')
        nested = '[' * 1100 + '0' + ']' * 1100
        for raw in [duplicate, nested]:
            self.registry.write_text(raw)
            with self.subTest(raw=raw[:70]), self.assertRaises(MeetingError):
                self.start()
        self.assertFalse(self.registry.with_name('meetings.sqlite3').exists())

    def receipt(self, message='2', **changes):
        return {**self.source, 'message_id': message, 'reply_to': '0001', **changes}

    def test_append_records_own_evidence_and_idempotent_retries(self):
        m = self.start()
        args = dict(actor='bob', meeting_id=m['id'], expected_revision=1, kind='contribution', text='Observed risk', source=self.receipt())
        updated = self.store().append(**args)
        self.assertEqual(updated['revision'], 2)
        self.assertEqual(updated['events'][0]['actor'], 'bob')
        self.assertEqual(updated['events'][0]['source'], self.receipt())
        self.assertEqual(self.store().append(**args), updated)
        with self.assertRaises(MeetingError):
            self.store().append(**{**args, 'text': 'forged'})
        with self.assertRaises(MeetingError):
            self.store().append(**{**args, 'source': self.receipt('3')})
        for changes in [dict(actor='mallory'), dict(kind='attended'), dict(text='x'*8001), dict(expected_revision=True), dict(source=self.receipt('3', reply_to=None)), dict(source=self.receipt('3', thread_id='other')), dict(source=self.receipt('3', chat_id='different')), dict(source=self.receipt('0001'))]:
            with self.subTest(changes=changes), self.assertRaises(MeetingError):
                self.store().append(**{**args, 'expected_revision': 2, **changes})
        own_reply = self.store().append('bob', m['id'], 2, 'question', 'Clarify?', self.receipt('3', reply_to='2'))
        self.assertEqual(own_reply['revision'], 3)
        with self.assertRaises(MeetingError):
            self.store().append('alice', m['id'], 3, 'decision', 'No', self.receipt('4', reply_to='2'))

    def test_only_invited_current_members_can_supply_receipts(self):
        m = self.start(participants=['alice'])
        with self.assertRaises(MeetingError):
            self.store().append('bob', m['id'], 1, 'contribution', 'Not invited', self.receipt())
        with self.assertRaises(MeetingError):
            self.store().transition('bob', m['id'], 1, 'pause', self.receipt())
        m = self.store().append('alice', m['id'], 1, 'contribution', 'Own receipt', self.receipt())
        self.data['teams'][0]['members'] = ['bob']
        self.save()
        with self.assertRaises(MeetingError):
            self.store().append('alice', m['id'], 2, 'summary', 'Removed member', self.receipt('3'))
        with self.assertRaises(MeetingError):
            self.store().transition('alice', m['id'], 2, 'pause', self.receipt('3'))
        self.assertEqual(self.store().get_meeting(m['id']), m)
        self.data['teams'][0]['members'] = ['alice', 'bob']
        self.save()
        forged = json.loads(json.dumps(m))
        forged['events'][0]['actor'] = 'bob'
        with closing(sqlite3.connect(self.registry.with_name('meetings.sqlite3'))) as db:
            db.execute('UPDATE meetings SET record=?', (json.dumps(forged),))
            db.commit()
        with self.assertRaises(MeetingError):
            self.store().list_meetings()

    def test_threaded_topic_does_not_require_reply(self):
        m = self.start(source={**self.source, 'thread_id': 'topic'})
        updated = self.store().append('bob', m['id'], 1, 'agenda', 'Extra', self.receipt(thread_id='topic', reply_to=None))
        self.assertEqual(updated['revision'], 2)

    def test_transition_lifecycle_and_closed_read_after_archive(self):
        m = self.start()
        self.assertTrue(callable(getattr(self.store(), 'transition', None)), 'transition is missing')
        for revision, action, status in [(1, 'pause', 'paused'), (2, 'resume', 'active'), (3, 'end', 'ended')]:
            src = self.receipt(str(revision+1))
            m = self.store().transition('alice', m['id'], revision, action, src)
            self.assertEqual((m['revision'], m['status']), (revision+1, status))
            self.assertEqual(self.store().transition('alice', m['id'], revision, action, src), m)
            if status == 'paused':
                with self.assertRaises(MeetingError):
                    self.store().append('bob', m['id'], m['revision'], 'summary', 'blocked', self.receipt('20'))
        with self.assertRaises(MeetingError):
            self.store().transition('alice', m['id'], 4, 'resume', self.receipt('9'))
        with self.assertRaises(MeetingError):
            self.store().append('alice', m['id'], 4, 'summary', 'blocked', self.receipt('9'))
        self.data['archive'] = self.data.pop('teams')
        self.data['teams'] = []
        self.save()
        self.assertEqual(self.store().get_meeting(m['id']), m)
        self.assertEqual(self.store().open_for_team('team-1'), [])
        with self.assertRaises(MeetingError):
            self.store().transition('alice', m['id'], 3, 'end', self.receipt('4'))

    def test_mutations_require_current_active_instance(self):
        m = self.start()
        for changes in [dict(status='disbanding'), dict(office_id='replacement'), dict(members=['bob'])]:
            original = self.data['teams'][0].copy()
            self.data['teams'][0].update(changes)
            self.save()
            with self.assertRaises(MeetingError):
                self.store().append('alice', m['id'], 1, 'decision', 'No', self.receipt())
            self.data['teams'][0] = original
        self.save()

    def test_registry_lock_is_reentrant_and_serialises_threads_and_processes(self):
        import subprocess
        import threading
        entered = threading.Event()
        attempted = threading.Event()
        errors = []
        def worker():
            attempted.set()
            try:
                with registry_lock(self.registry):
                    entered.set()
            except Exception as exc:
                errors.append(exc)
        with registry_lock(self.registry):
            with registry_lock(self.registry):
                t = threading.Thread(target=worker)
                t.start()
                self.assertTrue(attempted.wait(1))
                self.assertFalse(entered.wait(.1), 'Lock did not exclude another thread')
                code = ('import fcntl,sys; from pathlib import Path; '
                        'f=open(Path(sys.argv[1]).with_name(".office-meetings.lock"),"a"); '
                        'fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)')
                child = subprocess.run(['/usr/bin/python3', '-c', code, str(self.registry)], capture_output=True, timeout=5)
                self.assertNotEqual(child.returncode, 0, 'Lock did not exclude another process')
        t.join(2)
        self.assertFalse(t.is_alive())
        self.assertTrue(entered.is_set())
        self.assertEqual(errors, [])
        with registry_lock(self.registry):
            self.start()

    def test_missing_schema_corrupt_record_and_database_fail_closed(self):
        path = self.registry.with_name('meetings.sqlite3')
        path.write_bytes(b'')
        with self.assertRaises(MeetingError):
            self.start()
        path.unlink()
        m = self.start()
        self.assertEqual(self.store().list_meetings("ops' OR 1=1 --"), [])
        for bad in ['{broken', '{}', json.dumps({**m, 'id': {}}), json.dumps({**m, 'actor': 'mallory'}), json.dumps({**m, 'revision': True}), json.dumps({**m, 'status': 'impossible'}), json.dumps({**m, 'events': [{}]}), json.dumps({**m, 'source': {**self.source, 'message_id': 1}})]:
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('UPDATE meetings SET record=?', (bad,))
            with self.subTest(bad=bad), self.assertRaises(MeetingError):
                self.store().list_meetings()
            with self.assertRaises(MeetingError):
                self.start(source={**self.source, 'thread_id': 'new'})
        path.write_bytes(b'not sqlite')
        with self.assertRaises(MeetingError):
            self.store().list_meetings()
        with self.assertRaises(MeetingError):
            self.start()


if __name__ == '__main__':
    unittest.main()
