# Security and data handling

This repository is a prototype, not a hardened public service. Do not expose the Python backend directly to a LAN or the internet. The supplied gateway example is loopback-only HTTP for local development, not a TLS deployment configuration.

- Store actual credentials, password hashes, sessions, registry records, meetings, profile configuration, secrets, and deployment state outside version control.
- Do not upload screenshots, logs, database files, HAR captures, or browser state containing real users or team information.
- Authentication is enforced by the backend; never bypass it to populate the draft. A 401 response means the browser needs to sign in.
- Movement previews do not establish true working/idle/offline state. Treat missing runtime information as unknown.
- Team activation can change the local Hermes installation after an explicit preview/confirmation. Membership guidance is not a sandbox or hostile-agent security boundary.
- Review any real deployment separately for TLS, cookies, CSRF/origin policy, rate limits, backups and rollback. Never forward the example HTTP port to the internet.
- Before committing: inspect the exact staged file list and run a secret scanner. An ignore file is not a guarantee that an already-tracked file is safe.

If you find a vulnerability, do not post secrets, exploit payloads with private data, or private infrastructure details in a public issue. No dedicated private reporting channel is configured yet; arrange a private channel with the repository owner.
