"""Portable, removable meeting instructions generated at team activation."""
from pathlib import Path
import shlex
import sys


def meeting_guidance(team: dict, registry: Path) -> str:
    helper = Path(__file__).resolve().with_name("meeting_cli.py")
    command = " ".join(shlex.quote(str(p)) for p in (sys.executable, helper, "--registry", registry.resolve()))
    return f'''
## Conversation-led meetings
Use this skill when the user explicitly starts, resumes or ends a meeting for this team, including a one-to-one discussion with you. Office reflects the conversation; the user need not open Office or type a special command. Merely mentioning a future meeting is not a start. If team, intent, participants or agenda is unclear, ask one short question; do not silently record normal chat.

### Start and identity
- Confirm/propose the agenda and invited participants from this team's members. One specialist is sufficient; neither the lead nor a Telegram group is required. Invitations are not proof of participation: only a member's own recorded receipt establishes that they replied. Never manufacture another agent's contribution.
- Obtain the exact platform, chat ID, topic/thread ID (null if absent), and start-message ID from trusted incoming message metadata. Do not guess missing identifiers or substitute the current agent-session ID. Ask for the missing context if needed. Never copy unrelated chat history; include earlier context only when the user explicitly selects it.
- Run the local helper below with action `start`, supplying a JSON object on stdin (use a file/argv-safe subprocess; never interpolate conversation text into a shell command). Set `explicit_start` to true only for an actual explicit user request. Use team_slug `{team['slug']}`, a title, agenda array, participant profile array and source object. The source schema is platform, chat_id, thread_id, message_id, reply_to; IDs are exact strings or null where permitted. The current member profile is inferred from HERMES_HOME; there is no actor override.
- Read the returned record and acknowledge “Meeting started”, its stable ID, agenda and actual status only after success. If the helper fails, explain that Office has not recorded the meeting; do not claim it has started there.

### Updates and boundaries
- `read MEETING_ID` recovers the same record across agent-session replacements; `list --team {team['slug']}` finds its history. Keep the returned meeting ID and revision, not a session ID.
- `append` accepts meeting_id, expected_revision, kind, text and source on stdin. Kinds: contribution, agenda, decision, question, summary. Record your own contribution or an explicitly identified user decision/question in your own attributed receipt, not somebody else's invented speech. Include only relevant content deliberately contributed to the meeting. Never paste secrets or bulk transcripts. Agenda/decision entries record progress and agreed outcomes; they do not execute work or create approved tasks.
- Every update must match the exact platform/chat/thread. In unthreaded chats it must be a direct reply to the start message or your own accepted meeting event. Ordinary messages, a shared group, or an agent being online are not meeting attribution. If routing is ambiguous, ask the user to reply to a meeting message. A dedicated topic is preferable for team meetings.
- `transition` accepts meeting_id, expected_revision, action and source. Actions: pause, resume, end, cancel. Pause stops contributions; ending/cancelling retains immutable history and returns to ordinary conversation. Close or cancel all open/paused meetings before disbanding. Do not move a meeting to another chat implicitly; explicit relocation is not supported in this version.
- One open meeting (active or paused) per exact conversation route. On conflict, show the existing meeting rather than silently merging/starting another. On stale revision, re-read before continuing; do not overwrite other contributions. Retrying an identical source message is idempotent; do not reuse a message ID for different content/actions.

### Local integration contract
Command prefix (append the action above):
```sh
{command}
```
Example start JSON shape (replace all placeholders with confirmed metadata):
```json
{{"team_slug":"{team['slug']}","title":"Confirmed topic","agenda":["Confirmed agenda item"],"participants":["YOUR_MEMBER_PROFILE"],"explicit_start":true,"source":{{"platform":"telegram","chat_id":"EXACT_CHAT_ID","thread_id":null,"message_id":"EXACT_START_MESSAGE_ID","reply_to":null}}}}
```
Append shape:
```json
{{"meeting_id":"RETURNED_ID","expected_revision":1,"kind":"contribution","text":"Your actual contribution","source":{{"platform":"telegram","chat_id":"EXACT_CHAT_ID","thread_id":null,"message_id":"EXACT_NEW_MESSAGE_ID","reply_to":"EXACT_START_MESSAGE_ID"}}}}
```
Use actual incoming message identifiers; do not execute the illustrative placeholders. The authenticated Office Meetings view reads this same local store; it does not dispatch agents. Other installations generate their own registry/helper paths at onboarding. Remote/non-local agents need a separately approved adapter, not shared tokens or public exposure.

### Scope and removal
This is on-demand behavioural guidance plus a local record helper, not an always-on chat listener or hard security boundary. Profile membership, open/closed state, route, source receipts and revisions are checked by the helper. Agents running as the same operating-system user can access the same files; this is not an isolation/authorisation boundary between hostile agents. No credentials, base identity, model, working windows, A2A, scheduler, rendering or publishing permissions are changed. A meeting cannot grant approval for consequential work. Actual participant invocation/delivery uses only an existing authorised route and is not implemented by this recorder. If no such route exists, record missing replies honestly.

Activation installs only this team's on-demand skill. Disband archives only that exact team skill and revokes writes by inactive membership; meeting history remains in Office. Do not change another team's guidance or an agent's personal/base skills. Existing chats may need to load this skill explicitly; do not promise automatic recognition in a session that has not discovered it.
'''
