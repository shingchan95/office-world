# Roadmap and release gates

## Phase 0 — Repository foundation (current authorization)

- Source-only public repository with privacy exclusions and a recoverable baseline.
- Accurate setup requirements, contributor instructions and automated check definitions.
- Explicit no-agent-settings-change contract and honest known limitations.
- Focused pull-request process; CI may test/build/scan but may not deploy or execute real agents.

This phase does not authorize the feature work below. The owner will provide a start time. No extra agents are required for repository setup.

## Phase 1 — Safe onboarding (release blocker)

- Define supported Hermes versions/platforms through actual compatibility checks.
- Read-only prerequisite discovery without changing existing agent settings.
- Remove lifecycle configuration mutations; fail clearly when required access is unavailable.
- Guide local setup, profile discovery, team creation, explicit activation and recovery.
- Prove protected agent configuration/identity is unchanged through success, failure, rollback and disband.
- Demonstrate a clean-install path without this project's original host paths, state or credentials.

## Phase 2 — Authorized team work

- Establish explicit task ownership, handoffs and independent review.
- Prove a real, deliberately authorized end-to-end task flow; team membership alone must not dispatch agents.
- Define authoritative activity states and stale/unknown behavior before connecting the scene.

## Phase 3 — Connected office

- Keep the approved visual baseline; no unsolicited redesign.
- Connect verified activity while retaining a separate preview mode.
- Persist layouts and stable assignments safely; keep roster-driven capacity and movement tested.
- General collision-aware movement and real task behavior are separate from the existing stair/walking previews.

## Phase 4 — Release readiness

- Fresh-install and restart/recovery testing on supported environments.
- Security/privacy review, dependency checks, backup/rollback and deployment guidance.
- Owner approval of release scope, license and deployment—not just a passing build.

No phase is complete merely because a checklist or task was created. Record executable evidence and distinguish synthetic fixtures from real acceptance runs.
