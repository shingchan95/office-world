import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('repository_guard', Path(__file__).resolve().parents[1] / 'scripts/check_repository.py')
assert spec is not None and spec.loader is not None
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class RepositoryGuardTests(unittest.TestCase):
    def test_rejects_runtime_data_and_binary_files(self):
        for path in ['data/office.json', 'profiles/example/config.yaml', '.env', 'auth.json', 'capture.png', 'meeting.sqlite3']:
            self.assertTrue(guard.check(path, b'{}'), path)
        self.assertTrue(guard.check('unexpected.bin', bytes([255, 254])))

    def test_allows_source_and_explicit_example_environment(self):
        self.assertEqual(guard.check('server.py', b'print("hello")'), [])
        self.assertEqual(guard.check('.env.example', b'EXAMPLE_SETTING=example'), [])

    def test_reports_rule_without_echoing_the_value(self):
        token = 'ghp' + '_' + 'a' * 36
        result = guard.check('example.py', token.encode())
        self.assertEqual(result, [{'file': 'example.py', 'line': 1, 'rule': 'github-token'}])
        self.assertNotIn(token, str(result))


if __name__ == '__main__':
    unittest.main()
