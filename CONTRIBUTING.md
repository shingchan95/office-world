# Contributing

Read [AGENTS.md](AGENTS.md) and [the agent-settings contract](docs/AGENT_SETTINGS_CONTRACT.md) first. Repository maintenance is authorized; feature implementation and worker dispatch require the owner's start approval.

## Toolchain

- Python 3.11+; the CI definition tests 3.11 and 3.14 on Ubuntu. Python 3.10 is unsupported because its SQLite connection lacks the limits API used by the meeting store.
- Node.js 26.x (see `.node-version`). Direct TypeScript imports in tests require the supported Node runtime, not just Vite's minimum Node version.
- npm using the committed lockfile (`npm ci`).
- Chrome/Chromium for browser checks; set `CHROME_PATH` when needed.

Do not use real Hermes profiles, team records or credentials in automated checks. Backend tests provide isolated fixtures and do not need a real Hermes account. A successful fixture test is not proof of fresh-install/live-team compatibility.

## Local verification

From the repository root:

```sh
python3 scripts/check_repository.py
python3 -m unittest discover -s tests -v
cd frontend
npm ci --ignore-scripts
npm test
npm run build
npm run test:mobile
```

The browser harness creates an ephemeral loopback server and synthetic roster. It intentionally tests a 401 response and recovery; the expected unauthorized console message is not a failing test.

For secrets, run Gitleaks 8.30.1 or a reviewed newer version against the exact staged snapshot and Git history with redacted output. `scripts/check_repository.py` is an additional privacy/file-boundary guard, **not** a substitute for a full secret scanner or review. Do not print candidate secret values in logs.

## Pull requests

- Use a focused branch (`chore/`, `docs/`, `fix/`, `feat/`) and the PR template.
- Include scope, acceptance criteria, exact tests and known limitations.
- No real user data, screenshots of live teams, deployment secrets or private host details in public PRs/issues.
- Do not claim live work-state integration or zero settings changes until those paths are implemented and independently verified.
- Do not change architecture/appearance while performing repository maintenance.
- CI must only test/build/scan; no deployment, credentials or real agent execution.
- Public-repository setup does not authorize spending on additional agents or starting scheduled work.

The owner approved the [MIT license](LICENSE). Preserve the license notice and respect third-party licenses. Any change of license requires separate owner approval.
