# Working on Office World

## Scope and authorization

- Treat this repository as the source of truth for public application code. Never work from a private live installation or copy its runtime state into Git.
- The current authorized phase is **repository setup only**. Office design, feature implementation, live agent integration, worker dispatch, and deployment wait for the owner's start authorization.
- Visual changes require an explicit request; the approved draft is not an invitation to redesign it.
- Do not dispatch temporary helpers or start real team workers without explicit approval.

## Agent settings contract

Read `docs/AGENT_SETTINGS_CONTRACT.md` before touching onboarding or lifecycle code. Office must not modify an existing agent's model/provider, credentials, base instructions, memory, personal skills, tool configuration, gateway settings or schedule. Required access must be checked, not enabled silently. **The current lifecycle implementation does not yet fully meet this contract**: it can enable/disable lead Kanban access. Do not describe that path as non-mutating.

## Data boundaries

No real team/member records, messages, meetings, databases, sessions, authentication files, keys, logs, browser profiles, HAR captures or screenshots go into commits, issues, PRs or CI artifacts. Tests must use explicitly synthetic fixtures and isolated temporary directories. Never bypass authentication to populate the office. Keep backend listeners loopback-only.

## Change process

1. State the task's acceptance criteria and scope.
2. Use a focused branch and PR; avoid unrelated edits.
3. Read source and tests before changing behavior. Add a regression test for fixes.
4. Run the applicable checks in CONTRIBUTING.md. A build is not evidence of an authenticated workflow or live agent activity.
5. Review the exact staged diff/file list and run secret/privacy checks before pushing.
6. Report verified results and limitations. Never invent another agent's work or claim untested production readiness.

## Architecture invariants

- Team membership/identity is real when loaded through an authenticated API; animation previews are not live activity.
- Missing activity information is unknown, not automatically idle/working.
- Keep every unique member accounted for in desk and avatar capacity; do not silently hide overflow.
- Preserve existing agent identities. Team-owned resources and guidance are separate, removable and explicit.
- Keep the teams UI at `/` and the draft at `/design/` behind one gateway. Do not rewrite API requests into frontend HTML.
- Do not deploy automatically from CI or modify another profile's configuration.
