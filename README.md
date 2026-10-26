# Office World

An approved visual draft and local Office team-management prototype for Hermes Agent. The 3D frontend uses React, React Three Fiber, TypeScript, Vite, and Zustand; the backend uses Python's standard library.

## Current scope

- Authenticated, read-only team membership populates unique avatars and assigned desks.
- Compact, stacked two-storey office with opaque white tiles, two back walls, grass and daylight.
- Automatic capacity growth for incoming team members, browser-local design dimensions, and manual expansion controls.
- Work, leisure, walking and stair-traversal **previews**. These animations do not report real agent activity or dispatch work.
- Team creation, activation/disband previews and confirmation, and scoped meeting records in the backend prototype.

This is **not a production-ready service**. Design approval does not imply security approval or verified live-agent state integration. No production rollout is scheduled here.

**Agent-settings caveat:** the current lifecycle prototype can change the lead's Kanban toolset configuration. It does not yet meet the required zero-agent-settings-change contract. Read [the contract](docs/AGENT_SETTINGS_CONTRACT.md) before activation; replacing this behavior is a future release blocker, not part of repository setup.

## Repository status

Repository setup is the current phase. See [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), the [roadmap](docs/ROADMAP.md), and the [repository setup report](docs/REPOSITORY_SETUP.md). The primary product goal is a safe, reproducible install around an existing Hermes installation—not just the visualization. Installation automation and fresh-install compatibility verification remain unfinished.

To obtain the source:

```sh
git clone https://github.com/shingchan95/office-world.git
cd office-world
```

The local commands below are manual prototype setup, not a claim of one-click onboarding. Nothing in repository maintenance starts real agents or changes the running installation.

## Requirements

- Python 3.10+.
- Node.js 26.x, pinned in `.node-version`. Both builds and direct-TypeScript-import tests use this runtime.
- A local Hermes installation for actual profile discovery and team lifecycle operations.
- Chrome/Chromium for optional browser checks. Set `CHROME_PATH` if Chrome is not at the harness default path.

## Local backend

Create a private local Office login:

```sh
python3 scripts/initialize_auth.py
```

The script prompts locally for a username/password without storing either in source. It refuses to replace an existing auth file. By default, private authentication state is stored under your home directory in `.local/state/office/`; override with `OFFICE_AUTH_FILE` if needed. Do not commit that file.

Start the backend from this repository:

```sh
python3 server.py
```

Open `http://127.0.0.1:8765/`. The default registry lives in ignored `data/office.json`; set `OFFICE_DATA` to use a different private location. Session cookies are local to the browser and backend process. A phone login does not authenticate a desktop browser, and a backend restart invalidates in-memory sessions.

## Frontend

```sh
cd frontend
npm ci
npm test
npm run build
```

The build goes to `frontend/dist/` with base `/design/`. Use one gateway to serve the teams UI at `/` and the draft at `/design/`; see `examples/Caddyfile.local`. Do not rewrite `/api/*` into frontend HTML.

For that local gateway example, run the backend with the matching origin:

```sh
OFFICE_ALLOWED_ORIGIN=http://localhost:8443 python3 server.py
caddy run --config examples/Caddyfile.local --adapter caddyfile
```

Open `http://localhost:8443/` to sign in, then `http://localhost:8443/design/` in the **same browser**. The example binds only to loopback. It is not a public-internet deployment recipe. Real LAN/public deployment needs a separately reviewed TLS, authentication, network and recovery configuration; no installed machine configuration is included here.

## Verification

```sh
python3 -m unittest discover -s tests -v
cd frontend
npm test
npm run build
npm run test:mobile
```

Browser tests use explicitly synthetic team fixtures, an ephemeral loopback server, and a disposable Chrome profile. They verify layout, roster growth, work/leisure/walking previews, up/down stair traversal, pause, and sign-in recovery. They do **not** establish that a real user account or real agent activity has been verified.

## Privacy and publication

This repository is a new source-only snapshot, not a dump of the running server or its history. It excludes real team registries, profile data, meetings, credentials, sessions, logs, screenshots, installed dependencies, build output, certificates, and deployment-specific configuration. See [SECURITY.md](SECURITY.md) and the [publication report](docs/PUBLICATION_REPORT.md).

No open-source license has been selected yet; public visibility alone is not an unrestricted reuse grant.
