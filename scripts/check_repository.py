"""Check tracked files for forbidden runtime artifacts and high-confidence privacy leaks.

This is an extra file-boundary guard, not a replacement for Gitleaks or review.
Reports file/line/rule only; never prints matching values.
"""
from pathlib import Path
import json
import re
import subprocess

BANNED_PARTS = {'node_modules', 'dist', 'data', 'logs', 'profiles', 'memories', 'backups', '__pycache__'}
BANNED_NAMES = {'auth.json', 'access.txt', '.env', 'id_rsa', 'id_ed25519'}
BANNED_SUFFIXES = {'.sqlite', '.sqlite3', '.db', '.pem', '.key', '.crt', '.p12', '.pfx', '.png', '.jpg', '.jpeg', '.webp', '.har', '.log'}
PATTERNS = {
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'github-token': re.compile(r'\bgh[pousr]_[A-Za-z0-9]{24,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b'),
    'aws-access-key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'machine-home': re.compile(r'/home/(?!example\b|runner\b)[A-Za-z0-9_-]+'),
    'private-lan-address': re.compile(r'\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'),
}


def check(path: str, data: bytes) -> list[dict]:
    p = Path(path)
    findings = []
    if (any(part in BANNED_PARTS for part in p.parts) or p.name in BANNED_NAMES
            or p.suffix.lower() in BANNED_SUFFIXES
            or (p.name.startswith('.env.') and p.name != '.env.example')):
        findings.append({'file': path, 'line': 0, 'rule': 'runtime-artifact'})
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return findings + [{'file': path, 'line': 0, 'rule': 'unreviewed-binary'}]
    for number, line in enumerate(text.splitlines(), 1):
        for name, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append({'file': path, 'line': number, 'rule': name})
    return findings


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    paths = subprocess.check_output(['git', 'ls-files', '--cached', '-z'], cwd=root).decode().split('\0')
    findings = []
    checked = 0
    for path in filter(None, paths):
        data = subprocess.check_output(['git', 'show', ':' + path], cwd=root)
        findings.extend(check(path, data))
        checked += 1
    print(json.dumps({'tracked_files_checked': checked, 'findings': findings}, indent=2))
    return 1 if findings else 0


if __name__ == '__main__':
    raise SystemExit(main())
