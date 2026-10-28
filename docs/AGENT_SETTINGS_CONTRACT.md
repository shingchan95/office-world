# Agent settings contract

## Product requirement

Office is an organizational layer around existing Hermes agents. Joining, leaving or using an Office team must not change those agents' existing settings.

Protected state includes model/provider selection, credentials, base/system instructions, memory, personal skills, toolsets, platform/gateway configuration, schedules and permission policy.

Office may manage only its own registry, team boards, office layout and explicitly installed, removable team guidance. Team guidance must be separate and on-demand; it must not overwrite personal/base skills, become an always-on instruction injection or grant new permissions. Even Office-owned writes require a clear preview and confirmation where consequential.

## Honest current status

The zero-agent-settings-change contract is implemented and covered by regression tests. `lifecycle.py` performs a read-only preflight of the lead's/profile's Kanban capability per platform: if the toolset is missing it raises an actionable error before any board, skill or registry mutation, and never edits configuration, restarts gateways or widens permissions. Activation, rollback, disband and disband-rollback never call enable/disable on the lead's Kanban toolset (including the historical `kanban_added_by_office` marker) and never alter credentials, model/provider, base identity, memory, personal skills, schedules, gateway or platform settings. The owner resolves prerequisites separately through Hermes' supported configuration flows.

## Implemented behavior (read-only preflight)

1. Detect required capabilities using a read-only preflight.
2. If access is missing, explain the prerequisite and stop. Do not edit configuration, restart gateways or widen permissions.
3. Allow the owner to resolve prerequisites separately through Hermes' supported configuration flows.
4. Apply only explicitly approved Office-owned resources; preserve the existing agent state throughout success, failure, recovery and disband.
5. Report what changed and what did not. Membership alone does not start agents or authorize execution.

## Acceptance tests before a release claim

- On an isolated fresh Hermes fixture, snapshot protected configuration and content hashes before onboarding.
- Verify successful activation leaves protected content unchanged.
- Verify missing prerequisites fail without writes or partial resources.
- Exercise failure/rollback, repeated activation, shared memberships, leave/disband and restart recovery.
- Verify base identity, personal skills, models, credentials and scheduling remain unchanged after every path.
- Inspect real installed guidance and board ownership separately from mock-only unit tests.
- Validate supported Hermes versions and operating systems; do not claim universal compatibility from one host.

This is a release-blocking requirement, not an optional enhancement.
