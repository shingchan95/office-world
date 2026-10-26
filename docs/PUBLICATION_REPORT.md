# Initial publication report

## Published scope

A fresh, source-only snapshot of the approved Office World draft and Office team-management prototype. It includes application source, explicitly synthetic test fixtures, dependency lockfiles, local setup documentation, a local-only gateway example, and a private-auth initialization helper.

The running installation was not turned into a Git checkout or replaced. Its runtime data and deployment configuration were not copied into this repository. There is no prior server history in the new repository.

## Excluded from publication

- Real team/member registries, profile configurations, meeting histories and databases.
- Passwords, password hashes, tokens, session stores, browser profiles and authentication files.
- Local secrets/environment files, private keys, certificates and installed service configuration.
- Logs, screenshots, recordings, HAR exports, backups and caches.
- Installed dependencies and compiled build output.
- Old standalone design experiments and vendored third-party scripts.
- Machine-specific home-directory paths and private LAN addresses.

The public server default uses the current user's home directory rather than the original machine's absolute home path. Historical deployment notes were replaced with portable local instructions. Git commits use a GitHub no-reply identity rather than a personal email address.

## Checks performed

- Gitleaks 8.30.1 source scan, with redacted output: no findings. The scanner release archive's SHA-256 was checked against its published checksums.
- Review of the selected source-file allowlist and privacy-pattern checks for original machine paths, LAN addresses and local profile labels.
- Backend: `python3 -m unittest discover -s tests -v` — 53 tests passed.
- Frontend: clean `npm ci --ignore-scripts`, `npm test` — 8 tests passed; `npm run build` passed.
- `npm run test:mobile` passed with explicit synthetic fixtures, including dynamic roster growth, collision clearance, mixed previews, stair ascent/descent, desktop/mobile layout and simulated sign-in recovery.
- Local Caddy example validated successfully.
- Auth initialization and refusal to overwrite an existing auth file exercised with a random throwaway credential in an isolated temporary directory.
- npm install audit reported zero vulnerabilities for the locked dependency set at verification time.

Secret scanning and file review reduce publication risk but are not a guarantee of complete security. Browser fixture results do not establish a real signed-in session or live-agent activity. A large frontend bundle warning remains; performance work belongs to the next implementation phase.

## Status and next steps

The visual draft is approved. Real agent work-state integration, broader movement/planning, production hardening, deployment automation and independent release review remain future work. No scheduled development start, worker dispatch or production rollout is authorized by this publication. Work remains paused pending the owner's start time.

Suggested next phase: preserve a reproducible baseline, define authoritative activity-state contracts, then implement and review small end-to-end increments. The existing frontend/backend/operations team is sufficient initially; request more specialists only for a concrete gap.

No open-source license has been selected. Public availability does not itself grant an unrestricted license.
