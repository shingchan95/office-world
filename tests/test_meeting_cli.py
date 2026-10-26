"""Real subprocess CLI tests, synthetic homes/registries only."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


CLI = Path(__file__).resolve().parents[1] / 'meeting_cli.py'


class MeetingCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'profiles' / 'alice'
        self.home.mkdir(parents=True)
        (self.home / 'config.yaml').write_text('# synthetic config, no credentials\n')
        self.registry = self.root / 'office.json'
        self.registry.write_text(json.dumps({'version': 1, 'teams': [{'slug': 'ops', 'office_id': 'instance-1', 'status': 'active', 'members': ['alice', 'bob', 'default']}], 'archive': []}))
        self.source = dict(platform='telegram', chat_id='-001', thread_id=None, message_id='0001', reply_to=None)
        self.start_payload = dict(team_slug='ops', title='Review $(not-a-shell)', agenda=['Risks'], participants=['alice', 'bob'], source=self.source, explicit_start=True)

    def run_cli(self, action, payload=None, args=(), env=None, raw=None):
        environment = {**os.environ, 'HERMES_HOME': str(self.home), 'HOME': str(self.root), 'PYTHONDONTWRITEBYTECODE': '1'}
        if env:
            environment.update(env)
        result = subprocess.run(['/usr/bin/python3', str(CLI), '--registry', str(self.registry), action, *args], input=raw if raw is not None else json.dumps(payload) if payload is not None else '', text=True, capture_output=True, env=environment, timeout=8)
        self.assertTrue(CLI.exists(), 'meeting_cli.py implementation missing')
        try:
            data = json.loads(result.stdout)
        except ValueError:
            self.fail(f'CLI must return JSON, got stdout={result.stdout!r}, stderr={result.stderr!r}')
        return result, data

    def assert_error(self, *args, **kwargs):
        result, data = self.run_cli(*args, **kwargs)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(set(data), {'error'})
        self.assertIsInstance(data['error'], str)
        self.assertNotIn('Traceback', result.stderr)

    def test_real_start_append_transition_read_and_list(self):
        before = self.registry.read_bytes()
        result, m = self.run_cli('start', self.start_payload)
        self.assertEqual(result.returncode, 0, m)
        self.assertEqual(m['actor'], 'alice')
        self.assertEqual(m['source']['message_id'], '0001')
        receipt = {**self.source, 'message_id': '2', 'reply_to': '0001'}
        result, m = self.run_cli('append', dict(meeting_id=m['id'], expected_revision=1, kind='contribution', text='Actual received contribution', source=receipt))
        self.assertEqual(result.returncode, 0, m)
        self.assertEqual(m['events'][0]['actor'], 'alice')
        result, m = self.run_cli('transition', dict(meeting_id=m['id'], expected_revision=2, action='end', source={**receipt, 'message_id': '3'}))
        self.assertEqual(result.returncode, 0, m)
        self.assertEqual(m['status'], 'ended')
        self.assertEqual(self.run_cli('read', args=(m['id'],))[1], m)
        self.assertEqual(self.run_cli('list', args=('--team', 'ops'))[1], [m])
        self.assertEqual(self.run_cli('list', args=('--team', 'other'))[1], [])
        self.assertEqual(self.registry.read_bytes(), before)

    def test_payload_actor_unknown_fields_and_bad_json_are_rejected(self):
        for raw in ['{}', '[]', '{broken', '{"team_slug":"ops","team_slug":"ops"}', 'x'*262145]:
            self.assert_error('start', raw=raw)
        for changes in [dict(actor='bob'), dict(extra='ignored?'), dict(explicit_start=False), dict(source={**self.source, 'message_id': 1})]:
            self.assert_error('start', {**self.start_payload, **changes})
        self.assert_error('start', self.start_payload, args=('--actor', 'bob'))
        self.assert_error('append', dict(actor='bob'))
        self.assert_error('transition', dict(actor='bob'))
        self.assert_error('not-an-action')
        self.assert_error('read', args=('missing',))
        self.assertFalse(self.registry.with_name('meetings.sqlite3').exists())

    def test_actor_requires_actual_profile_config_and_native_default(self):
        self.assert_error('start', self.start_payload, env={'HERMES_HOME': ''})
        self.assert_error('start', self.start_payload, env={'HERMES_HOME': str(self.root)})
        (self.home / 'config.yaml').unlink()
        self.assert_error('start', self.start_payload)
        other = self.root / 'profiles' / 'default'
        other.mkdir()
        (other / 'config.yaml').write_text('# fixture')
        payload = {**self.start_payload, 'participants': ['default']}
        self.assert_error('start', payload, env={'HERMES_HOME': str(other)})
        native = self.root / '.hermes'
        native.mkdir()
        (native / 'config.yaml').write_text('# fixture')
        result, m = self.run_cli('start', payload, env={'HERMES_HOME': str(native)})
        self.assertEqual(result.returncode, 0, m)
        self.assertEqual(m['actor'], 'default')


if __name__ == '__main__':
    unittest.main()
