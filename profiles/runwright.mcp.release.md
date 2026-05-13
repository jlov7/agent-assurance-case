# Profile: `runwright.mcp.release` v0.1

**Profile ID:** `runwright.mcp.release`  
**Profile version:** `0.1.0`  
**Builds on:** `aac.core` v0.2 at assurance level `basic` or higher.  
**Purpose:** Define the minimum evidence expected for an AAC issued against an agentic AI release whose primary surface is MCP (Model Context Protocol) servers and tools.

This is a vendor profile for Runwright-style MCP releases. Independent vendors MAY define alternative MCP profiles. This profile is intentionally implementable with deterministic inventory, approval, scope, and provenance checks before broader runtime/cross-origin analysis.

## 1. Scope

This profile applies when `subject.subject_type` is `mcp_server`, `agent`, or `workflow` and the release contains at least one asset of type `mcp_server` or `mcp_tool`.

## 2. Required Assets

An AAC declaring this profile MUST include at least one asset of type `mcp_server` or `mcp_tool` in `assets`.

Each `mcp_server` asset SHOULD include `metadata` with:

- `transport` — one of `stdio`, `http`, `sse`, `websocket`;
- `tools_exposed` — array of `asset_id` of tools served;
- `auth_scheme` — string identifying the authentication scheme;
- `tbom_ref` — URI of the Tool Bill of Materials, if available.

Each `mcp_tool` asset SHOULD include `metadata` with:

- `irreversible` — boolean indicating whether the tool has irreversible side effects;
- `scopes` — array of capability scopes the tool requires;
- `required_approval` — one of `not_required`, `present`, or `missing`.

## 3. Required Detector Coverage

`coverage.detector_runs` MUST include at least one run for each of the following categories, with `required: true` and `status` not in `{skipped, error}`:

- `mcp-tool-definition-risk` — validate tool definitions, schemas, names, and descriptions for poisoning or dangerous semantic mismatch;
- `mcp-approval-gate` — detect irreversible or privileged tools that lack a human approval gate;
- `mcp-scope-creep` — detect permissions or scopes that exceed declared need;
- `mcp-tbom-presence` — verify TBOM/provenance presence for MCP servers or tools when available.

The following detector classes are RECOMMENDED but are not required for v0.1 conformance because they generally need runtime telemetry, tenant topology, or deeper dependency analysis:

- `cross-origin-escalation`;
- `runtime-tool-poisoning`;
- `supply-chain-compromise-deep`;
- `intent-flow-subversion`.

Under core verdict semantics, a required detector with `status` in `{skipped, error}` causes HOLD. Under this stricter release profile, that same case is not profile-conformant because the required detector category was not successfully executed.

## 4. Required Policy Decisions

For any `mcp_tool` asset with `metadata.irreversible == true`, the AAC MUST include a policy decision with `subject_asset_id` equal to that asset's `asset_id` evaluating whether a human approval gate is present. If the approval gate is missing, the policy decision outcome MUST be `hold` or `deny`.

## 5. Required Evidence Linkage

For any finding tied to an MCP asset, `evidence_refs` MUST resolve to at least one entry in `evidence_artifacts`. For policy decisions, `inputs_hash` MUST be a SHA-256 of the canonical inputs the policy evaluated.

## 6. Required AIBOM

This profile REQUIRES `aibom_ref`. The referenced AIBOM MUST enumerate every MCP server and tool in `assets`. The `aibom_ref` URI MUST also appear in `evidence_artifacts` with role `aibom`.

## 7. Recommended Runtime Coverage

`coverage.runtime_coverage.status` SHOULD be at least `summary`. Tool-call patterns observed in production often surface scope or approval gaps invisible to static analysis.

## 8. Verifier Behavior

A verifier processing an AAC declaring this profile MUST:

- apply all `aac.core` rules;
- reject the AAC if `profile.assurance_level` is below `basic`;
- reject the AAC if no `mcp_server` or `mcp_tool` asset is present;
- reject the AAC if any required detector category from §3 is absent or has `status` in `{skipped, error}`;
- reject the AAC if any irreversible MCP tool lacks an explicit asset-linked policy decision per §4;
- reject the AAC if `aibom_ref` is absent or absent from `evidence_artifacts`;
- reject the AAC if any `evidence://` reference in findings, detector runs, eval results, runtime trace refs, `release_conditions`, `compliance_mappings`, `aibom_ref`, or `graph_snapshot_ref` is absent from `evidence_artifacts`;
- recompute the verdict and reject if it does not match `verdict`.
