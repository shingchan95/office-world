"""Local receipt-led meetings. Use --help for exact JSON contracts.

Co-operative same-UNIX-user enforcement, not a hardened ACL for shell users.
Reads config.yaml existence only, never contents or credentials. No registry,
profile, auth, scheduling, chat-ingestion, dispatch or network changes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from meetings import MeetingError, MeetingStore


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise MeetingError('Invalid command arguments; use --help.')


def actor_from_home():
    """Derive identity from HERMES_HOME only; require an actual config file."""
    value = os.environ.get('HERMES_HOME')
    if not value or len(value) > 4096 or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value):
        raise MeetingError('HERMES_HOME must identify an existing Hermes profile.')
    home = Path(value).expanduser()
    if not home.is_absolute():
        raise MeetingError('HERMES_HOME must be absolute.')
    home = home.resolve()
    if not (home / 'config.yaml').is_file():
        raise MeetingError('HERMES_HOME must contain an actual config.yaml file.')
    if home == (Path.home() / '.hermes').resolve():
        return 'default'
    if home.parent.name == 'profiles' and home.name != 'default':
        return home.name
    raise MeetingError('HERMES_HOME is not a named profile or the native default home.')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MeetingError('Duplicate JSON fields are not permitted.')
        result[key] = value
    return result


def _constant(value):
    raise MeetingError('Non-finite JSON values are not permitted.')


def payload_for(action):
    # Bound raw input before decoding; values are passed directly, never via shell.
    raw = sys.stdin.buffer.read(262145)
    if len(raw) > 262144:
        raise MeetingError('JSON payload exceeds 262144 bytes.')
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise MeetingError('Payload must be valid JSON without duplicate fields.') from exc
    fields = {
        'start': {'team_slug', 'title', 'agenda', 'participants', 'source', 'explicit_start'},
        'append': {'meeting_id', 'expected_revision', 'kind', 'text', 'source'},
        'transition': {'meeting_id', 'expected_revision', 'action', 'source'},
    }[action]
    required = fields - ({'explicit_start'} if action == 'start' else set())
    if not isinstance(value, dict) or set(value) - fields or required - set(value):
        raise MeetingError('Payload fields do not match the action contract; use --help. Actor overrides are forbidden.')
    return value


def main(argv=None):
    parser = Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, epilog='''
Mutation payloads are JSON objects on stdin, never shell-interpolated arguments:
  start: team_slug, title (1..160), agenda (<=20 strings, 1..500 each),
         participants (1..50 unique team members, including actor), source,
         explicit_start=true after explicit intent, agenda/invitee confirmation.
  append: meeting_id, expected_revision (positive integer), kind, text (1..8000), source.
          kind: contribution | agenda | decision | question | summary.
  transition: meeting_id, expected_revision, action, source.
              action: pause | resume | end | cancel.
Every source must have exactly these fields, preserving identifier strings:
  {"platform":"telegram","chat_id":"-001","thread_id":null,
   "message_id":"0001","reply_to":null}
thread_id/reply_to are strings or null; other fields are nonempty strings.
Route is immutable (platform/chat_id/thread_id). Unthreaded later receipts must
reply directly to the start message or the actor's own accepted message.
Threaded receipts must match the exact topic. No implicit chat scan occurs.
Participants are invitations, NOT proof anyone replied or attended.
Start is idempotent for identical team-instance/start-message/payload. Repeated
identical event receipts are idempotent even with a stale positive revision.
Changed reuse conflicts. One active/paused meeting per exact route across teams.
Closed records cannot change. All mutations require current active membership;
append/transition actors must also be in the confirmed invitation list.
Actor comes ONLY from HERMES_HOME (named profiles/<name> or native ~/.hermes
for default), with an existing config.yaml; no --actor or actor payload field.
Output: JSON record; list: JSON array. Failures: {"error":"safe message"}, exit 2.
Co-operative local same-UNIX-user checks; not hardened against shell access.
No tokens, credentials, scheduling, dispatch, auth or profile/registry writes.
''')
    try:
        parser.add_argument('--registry', required=True, type=Path, help='Absolute Office registry JSON path (read-only).')
        commands = parser.add_subparsers(dest='action', required=True)
        for name in ('start', 'append', 'transition'):
            commands.add_parser(name, help='Read exact action JSON from stdin.')
        read = commands.add_parser('read', help='Read one record by stable meeting UUID.')
        read.add_argument('id')
        listing = commands.add_parser('list', help='Read records, optionally filtered by team slug.')
        listing.add_argument('--team')
        args = parser.parse_args(argv)
        if not args.registry.is_absolute():
            raise MeetingError('--registry must be an absolute path.')
        actor = actor_from_home()
        store = MeetingStore(args.registry)
        if args.action == 'read':
            result = store.get_meeting(args.id)
            if result is None:
                raise MeetingError('Meeting not found.')
        elif args.action == 'list':
            result = store.list_meetings(args.team)
        else:
            result = getattr(store, args.action)(actor=actor, **payload_for(args.action))
        print(json.dumps(result))
        return 0
    except MeetingError as exc:
        print(json.dumps({'error': str(exc)}))
        return 2
    except (OSError, ValueError, TypeError, RecursionError):
        print(json.dumps({'error': 'Cannot process meeting operation safely.'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
