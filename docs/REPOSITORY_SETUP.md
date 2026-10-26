# Repository setup report

## Scope

This change establishes repository rules, setup documentation, check definitions and privacy guards. It does not implement onboarding changes, alter Office visuals, deploy code, dispatch workers or change any existing agent settings.

## Added foundation

- `AGENTS.md`: authorization boundaries, source/runtime separation, honest verification and no private data in public artifacts.
- `CONTRIBUTING.md`: local commands, pinned Node runtime, PR process and non-deploying CI policy.
- `docs/AGENT_SETTINGS_CONTRACT.md`: release-blocking requirement to preserve existing agent settings; current lifecycle mutation is explicitly disclosed, not silently declared fixed.
- `docs/ROADMAP.md`: repository setup before onboarding, task execution, live activity and production work.
- `.node-version` / package engines: Node 26.x for both build and direct-TypeScript tests.
- Corrected Python minimum to 3.11 after hosted tests exposed the meeting store's use of `sqlite3.Connection.setlimit`, which is absent in Python 3.10. No application behavior was changed to conceal the incompatibility.
- Privacy guard and regression tests: inspect the exact tracked index for forbidden runtime artifacts and high-confidence leak patterns; findings never echo matching values.
- Public-safe bug report and pull-request templates.
- GitHub Actions check definition: read-only repository permission, SHA-pinned actions, full-history secret scanning with a checksum-verified scanner, backend tests and frontend/browser tests. It contains no deployment or real-agent execution step.

## Verification status

Local checks and the exact remote PR/check state are recorded in the repository-setup pull request. A workflow definition is not evidence that hosted CI ran; any GitHub authorization or hosted-run blocker must be reported explicitly before claiming CI is enabled or green.

The original publication report remains a historical account of the initial source snapshot, not a statement that future release gates have passed.

## Deferred decisions/work

- The owner must choose a license before this is presented as a generally reusable open-source release.
- Existing activation may still change the lead's Kanban toolset; fixing it is the first future functional milestone, not part of this maintenance change.
- Guided installation, supported-version validation, real activity integration and production readiness remain unfinished.
- No team development start is scheduled. Feature work and dispatch wait for the owner's authorization.
