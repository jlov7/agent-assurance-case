# Agent Assurance Case (AAC) Specification

**Version:** 0.2-candidate.4 (Draft)
**Date:** 2026-05-12
**Status:** Pre-public candidate after adversarial review and profile-verifier hardening
**Initial maintainer:** Jason Lovell (intended to transfer to a neutral standards body once at least two independent implementations exist)
**Schema URI:** `https://raw.githubusercontent.com/jlov7/agent-assurance-case/v0.2-candidate.4/schemas/agent-assurance-case-v0.2.schema.json`
**Specification license:** CC BY 4.0
**Reference verifier license:** Apache 2.0

## Status of This Document

This is a draft pre-public specification, version 0.2-candidate.4. It supersedes the internal v0.1 draft, which contained trust-critical defects in evidence binding and signature verification. This document is prepared for public comment but SHOULD remain private until the maintainer explicitly approves publication. Implementations conforming to this draft MUST NOT claim conformance to a stable AAC standard until v1.0.

The schema URI is pinned to the candidate Git tag so reviewers can resolve the exact draft being cited. Later candidates or stable releases MUST publish their own immutable schema URI.

## Abstract

This specification defines the Agent Assurance Case (AAC): a portable, signed, deterministically-verifiable JSON object that captures the evidence and verdict for a single release of an agentic AI workflow. An AAC is produced by a release gate or assurance system, signed by its issuer, and is verifiable offline by any consumer using only the AAC document and the issuer's public key. The AAC is designed to support audit-evidence workflows under regimes such as the EU AI Act, ISO/IEC 42001, NIST AI RMF, and equivalent regimes. AAC verification is not, by itself, a legal compliance certification.

## 1. Introduction

### 1.1 Motivation

Agentic AI systems combine multiple asset types — skills, tools (commonly via Model Context Protocol), inter-agent contracts (commonly via Agent-to-Agent protocols), prompts, memory stores, models, datasets, and policies — into workflows that can execute consequential actions on behalf of users or organizations. Each asset type introduces distinct risks: skill poisoning, tool poisoning, prompt injection, memory leakage, model drift, dataset contamination, delegation abuse, and others.

Existing standards address adjacent concerns. CycloneDX ML-BOM and SPDX 3.0 with AI profiles enumerate components. OpenTelemetry GenAI semantic conventions standardize traces. Sigstore, in-toto, and SLSA provide build provenance. NIST AI RMF, ISO/IEC 42001, and the EU AI Act define obligations. What is missing is a standard, signed, portable evidence object that ties these together for a single release decision and produces a deterministic verdict an auditor or release reviewer can rely on. The AAC fills that gap.

### 1.2 Scope

This specification defines:

- the structure of an AAC;
- the meaning of each required and optional field;
- the deterministic computation of its verdict;
- the canonicalization, hashing, and signing procedures;
- the offline verification procedure;
- the alignment with named external standards;
- the profile mechanism that defines minimum evidence expectations per use case.

### 1.3 Out of Scope

This specification does not define:

- specific detection rules, eval rubrics, or policy contents (those live in profiles and implementations);
- the trace or telemetry format itself (implementations SHOULD use OpenTelemetry GenAI semantic conventions);
- the AIBOM format itself (implementations SHOULD use CycloneDX ML-BOM or SPDX 3.0 AI profiles);
- the user interface for reviewing AACs;
- the storage or distribution system for AACs;
- key management, key rotation, or revocation policies (issuers SHOULD publish key transparency information).

### 1.4 Relationship to Other Standards

- **CycloneDX ML-BOM / SPDX 3.0 AI profiles** — Referenced by URI in `aibom_ref`. The AIBOM enumerates components; the AAC records and signs the issuer's release-readiness decision.
- **OpenTelemetry GenAI semantic conventions** — Runtime events SHOULD use OTel GenAI span shapes where applicable.
- **Sigstore / in-toto / SLSA** — AAC signatures use Ed25519 by default and are compatible with Sigstore key formats. The AAC complements rather than replaces SLSA provenance: SLSA attests how an artifact was built; the AAC records the issuer's deterministic release verdict and supporting evidence.
- **OWASP MCP Top 10** — Finding `category` values for MCP-related risks SHOULD use identifiers `MCP01` through `MCP10`.
- **NIST AI RMF** — Compliance mappings SHOULD reference GOVERN, MAP, MEASURE, and MANAGE function categories.
- **ISO/IEC 42001** — Compliance mappings SHOULD reference clause numbers and Annex A controls.
- **EU AI Act** — Compliance mappings SHOULD reference Article numbers and Annex IV documentation categories.
- **W3C Verifiable Credentials** — A future minor version of this specification MAY define an optional VC wrapper for cross-organization portability.

## 2. Conventions

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL in this document are to be interpreted as described in RFC 2119 and RFC 8174.

All AAC documents MUST be valid UTF-8-encoded JSON conforming to RFC 8259.

All timestamps MUST be RFC 3339 strings in UTC (suffix `Z`).

All hashes MUST be lowercase hexadecimal SHA-256, prefixed with `sha256:`.

All signatures MUST be base64-encoded ed25519 signatures (standard alphabet, with padding), prefixed with `ed25519:`.

Implementations MUST reject AACs whose `schema_version` they do not understand. Implementations SHOULD support reading the immediately prior minor version.

## 3. The Core Object

An AAC is a JSON object. The following top-level fields are REQUIRED:

```
schema_version
case_id
created_at
profile
subject
verdict
coverage
assets
findings
policy_decisions
evidence
```

The following top-level fields are OPTIONAL:

```
verdict_reasons
release_conditions
eval_results
aibom_ref
graph_snapshot_ref
evidence_artifacts
runtime_events
approvals
compliance_mappings
```

Each field is defined in the JSON Schema at the canonical URI listed at the top of this document. The schema is normative; this text is informative where it overlaps.

### 3.1 Subject

The `subject` MUST identify the release being assured by at least `name`, `release_ref`, and `environment`. Implementations SHOULD include `repo`, `commit`, `pull_request`, and `owner` when available.

The `subject.subject_type` SHOULD be one of `agent`, `workflow`, `skill`, `skill_bundle`, `mcp_server`, `a2a_agent`, or `application`.

## 4. Profiles

The schema defines object shape. A **profile** defines the minimum evidence expected for a use case.

A schema without profiles is insufficient for enterprise assurance because a weak issuer could produce a structurally valid PASS with no meaningful inventory, no required detector coverage, and no runtime evidence. To prevent this, every AAC MUST declare a `profile` object containing `profile_id`, `profile_version`, and OPTIONAL `assurance_level`.

The reference profile in this specification is `aac.core`. Implementations MAY define additional profiles. Profile definitions are published as separate documents alongside this specification; see `profiles/` in the reference repository for the core profile and any vendor profiles.

A verifier MUST recompute the verdict using the deterministic rules in §5 of this specification. A verifier MUST apply any profile-specific rules it claims to support. A verifier that does not support the declared profile MUST return `NOT VERIFIED` rather than silently falling back to core-only verification. A profile MUST NOT relax §5 conditions; it MAY only add conditions.

## 5. Verdict Semantics

The `verdict` field MUST be exactly one of `pass`, `hold`, or `fail`.

### 5.1 FAIL

A verifier MUST return FAIL if any of the following conditions hold:

- a finding references an asset not present in `assets`, except the reserved literal `subject`;
- any unresolved finding has severity `critical`;
- any policy decision has outcome `deny`;
- the AAC content hash cannot be reproduced;
- the AAC signature cannot be verified against an accepted key.

### 5.2 HOLD

A verifier MUST return HOLD if FAIL conditions do not apply and any of the following conditions hold:

- `coverage.inventory_status` is `partial` or `unknown`;
- any required detector run has `status` in `{skipped, error}`;
- any unresolved finding has severity `high`;
- any policy decision has outcome `hold`;
- any required eval result has `status` in `{fail, error, skipped}`;
- any release condition has `status` other than `satisfied`;
- any high or critical finding has status `suppressed` or `accepted_risk`, even where a structurally valid approval exists. Such cases represent documented exception releases and MUST NOT be reported as clean PASS by a core verifier.

### 5.3 PASS

A verifier MAY return PASS only if no FAIL or HOLD condition applies.

### 5.4 Determinism Requirement

The verdict MUST be deterministically computable from the contents of the AAC by any compliant verifier. Verdict computation MUST NOT depend on a large language model, a non-deterministic risk model, or any network call. An offline verifier and an online verifier MUST arrive at the same verdict.

### 5.5 Policy Outcomes

Policy decisions are distinct from finding severity. The `outcome` value `deny` represents a non-remediable policy violation. The value `hold` represents a remediable policy violation (for example, a required approval is pending). Issuers SHOULD prefer `hold` over `deny` when a documented path exists to satisfy the policy.

The `outcome` value `warn` is informational. It MUST NOT, by itself, change the verdict. Consumers MAY surface warnings to reviewers but a verifier that recomputes the verdict treats `warn` as it treats `allow`.

## 6. Evidence Model

The `evidence` object binds the AAC to its issuer through a content hash and a signature.

### 6.1 Required Evidence Fields

```
content_hash
signature
signed_by
signed_at
signature_algorithm
canonicalization
```

`signature_algorithm` and `canonicalization` are REQUIRED because §6.4 fixes their permitted values and a verifier MUST be able to reject an AAC that names a scheme it does not implement. They are signed alongside the rest of the payload.

### 6.2 Recommended Evidence Fields

```
key_id
public_key_ref
offline_verifier
```

### 6.3 Hashing Procedure

To compute `content_hash`, an implementation MUST:

1. deep-copy the AAC;
2. set `evidence.content_hash = null`;
3. set `evidence.signature = null`;
4. canonicalize the resulting object using JSON Canonicalization Scheme (RFC 8785);
5. compute SHA-256 over the canonical bytes;
6. encode as `sha256:<lowercase hex>`.

This procedure protects evidence metadata (`signed_by`, `signed_at`, `key_id`, `public_key_ref`, algorithm identifiers) by including those fields in the signed payload, while excluding only the self-referential hash and signature fields.

An implementation MUST NOT remove the entire `evidence` object before hashing. Doing so leaves signer metadata mutable and breaks the trust model.

### 6.4 Signing Procedure

The signature MUST be an ed25519 signature over the same canonical payload bytes used to compute `content_hash`. The `signature_algorithm` field MUST be set to `Ed25519-JCS-SHA256-v1` to identify this scheme.

### 6.5 Verification Procedure

A compliant verifier MUST:

1. parse the AAC as UTF-8 JSON, rejecting duplicate object member names, `NaN`, `Infinity`, and `-Infinity`;
2. validate the AAC against the schema, with JSON Schema `format` checks enabled;
3. reproduce `content_hash` per §6.3 and confirm it matches `evidence.content_hash`;
4. verify `evidence.signature` against the issuer's public key per §6.4;
5. apply the declared profile rules if the verifier claims support for that profile;
6. recompute the verdict per §5 and confirm it matches `verdict`;
7. return `VERIFIED` only if all checks succeed.

A verifier MUST NOT silently skip signature verification. It MUST verify against a supplied public key, OR verify against an explicitly enabled demo key for bundled examples (using an opt-in flag), OR return `NOT VERIFIED`.

### 6.6 Evidence Artifact Manifest

The optional `evidence_artifacts` array lists externally stored evidence referenced by the AAC. Each entry SHOULD include `artifact_id`, `uri`, `digest`, `role`, and `media_type` where available.

Profiles MAY require that every `evidence://` URI appearing in `findings[*].evidence_refs`, `coverage.detector_runs[*].evidence_ref`, `eval_results[*].evidence_ref`, `runtime_events[*].trace_ref`, `coverage.runtime_coverage.trace_refs`, `aibom_ref`, or `graph_snapshot_ref` appears in `evidence_artifacts` with a `sha256:` digest.

This manifest does not require raw evidence to be embedded in the AAC. It provides immutable binding for external evidence vault objects.

## 7. Canonicalization and Numbers

The reference verifier rejects duplicate JSON object member names, `NaN`, `Infinity`, floating-point numbers, and integers outside the JSON safe-integer range `[-9007199254740991, 9007199254740991]`. Numeric metrics SHOULD be represented as safe integers or as decimal strings.

This restriction exists because RFC 8785 number canonicalization is non-trivial and incorrect canonicalization in the trust-critical path is worse than slightly inconvenient metric encoding. Implementations MAY support floats only if they use a vetted RFC 8785/JCS library and preserve cross-language canonicalization compatibility.

## 8. Coverage

The `coverage` object is REQUIRED. A PASS without coverage is not meaningful.

The `coverage` object MUST include:

- `inventory_status` — one of `complete`, `partial`, or `unknown`;
- `inventory_methods` — a non-empty array of strings describing how assets were discovered;
- `detector_runs` — an array of detector identity, scope, categories, status, required flag, and evidence reference.

The `coverage` object SHOULD include:

- `scanned_refs` — paths, repositories, manifests, or trace scopes scanned;
- `excluded_refs` — explicit exclusions with reasons;
- `runtime_coverage` — whether runtime evidence is `none`, `summary`, or `full`.

## 9. Agent Assets

Each item in `assets` is a typed reference to a component the release depends on.

The supported `asset_type` values in v0.2 are:

```
agent, workflow, skill, skill_bundle, mcp_server, mcp_tool, a2a_agent,
prompt, memory_store, model, dataset, policy, eval, identity,
credential_ref, runtime, connector, environment
```

Every asset MUST have an `asset_id`, `asset_type`, and `name`. Each asset SHOULD include `version`, `source_uri`, `digest`, `provenance`, and type-specific `metadata`.

The `digest` field, when present, MUST be a lowercase hex SHA-256 with the `sha256:` prefix.

## 10. Findings and Resolution

Each finding MUST include `finding_id`, `category`, `severity`, `subject_asset_id`, `title`, `status`, and `created_at`.

The `subject_asset_id` MUST refer to a declared asset's `asset_id`, OR the reserved literal `subject`.

The `severity` MUST be one of `critical`, `high`, `medium`, `low`, or `info`.

The `status` MUST be one of `open`, `resolved`, `suppressed`, or `accepted_risk`.

A finding is considered unresolved unless:

- `status == resolved`; OR
- `status` is `suppressed` or `accepted_risk`, AND the finding links to a valid approval via `resolution.approval_id`, AND the linked approval has the appropriate decision, AND the resolution or approval has not expired as of `evidence.signed_at`.

Even when a suppression or accepted-risk resolution is structurally effective, high and critical findings MUST still produce HOLD under the core verifier. They are documented exceptions, not clean passes.

A v0.2 reference verifier MUST validate structural linkage and expiry. A v0.2 reference verifier MAY NOT validate approval signatures against an organizational authority keyring; that validation is RECOMMENDED in profile-specific enterprise verifiers.

## 11. Privacy and Data Minimization

An AAC MUST NOT embed raw prompts, raw completions, raw user inputs, source code, or secrets by default. Implementations MUST treat fields like `evidence_refs` as URIs into the issuer's evidence vault, not as inline evidence payloads. Where external evidence is referenced, profiles SHOULD require those references to be listed in `evidence_artifacts` with immutable digests so vault mutation does not silently change what an AAC means.

`runtime_events` summaries MAY include hashes, counts, durations, and policy outcomes. They MUST NOT include prompt or completion content unless an explicit opt-in policy is recorded in the issuer's profile.

Profiles SHOULD define additional privacy metadata: redaction policy identifier, evidence residency, retention class, DLP scan attestation, and sensitive-data classification for evidence references.

## 12. Security Considerations

### 12.1 Replay

An AAC is bound to a specific `case_id`, `subject.release_ref`, and `created_at`. Consumers MUST check freshness and uniqueness as appropriate for their use case. An AAC issued for one release MUST NOT be accepted as evidence for another.

### 12.2 Key Compromise

This specification does not define key rotation or revocation policies. Issuers SHOULD publish key transparency information and signed key-rotation events. Consumers SHOULD reject signatures from keys known to be revoked.

### 12.3 Detector Coverage

The AAC does not certify the correctness of detectors. A clean AAC with an incomplete or compromised detector set may still be vulnerable to undetected risks. Consumers SHOULD verify detector coverage via the `coverage.detector_runs` field and require a baseline detector set per profile.

### 12.4 Suppression Abuse

Unsigned, unlinked, or stale suppressions MUST be treated as unresolved findings. Approval signatures used in suppressions SHOULD be validated against an organizational authority keyring; this validation is profile-specific in v0.2.

### 12.5 Schema Drift

Verifiers MUST reject AACs claiming a `schema_version` they do not implement. Adding OPTIONAL fields is a minor change; changing the meaning of existing fields requires a major version increment.

### 12.6 Trust Boundary of the Verifier

The reference verifier in this specification is intended to be readable end-to-end. It is NOT intended to be the trust root for high-stakes deployments. Production deployments SHOULD use vetted cryptographic and canonicalization libraries.

### 12.7 Cross-Tenant Leakage in Derived Signals

If an issuer publishes a derived-signal version of an AAC for ecosystem learning, that version MUST set `evidence.signed_by` to a derived-signal identity distinct from the original issuer, and MUST strip all evidence references that point at tenant-controlled vaults.

### 12.8 Evidence Vault Mutation

If an AAC references external evidence without binding that evidence to a digest, a verifier can prove only that the AAC text was signed, not that the external evidence later reviewed by an auditor is the same evidence considered at signing time. Profiles SHOULD require `evidence_artifacts` for every material evidence URI.

### 12.9 Duplicate JSON Member Names

AAC parsers MUST reject duplicate JSON object member names. Different parsers may otherwise interpret the same byte sequence differently, which is unacceptable for signed release evidence.

### 12.10 Profile Downgrade and Unsupported Profiles

Consumers MUST NOT treat a structurally valid AAC as satisfying a stronger profile unless the verifier explicitly supports and enforces that profile. Unsupported profiles MUST result in `NOT VERIFIED`, not a weaker verification result.

### 12.11 Key Discovery and Trust Roots

The `public_key_ref` field is signed metadata, not a trust root. Consumers MUST obtain trusted keys from an out-of-band trust store, transparency log, Sigstore identity, DID resolver, or equivalent organizational key-management process. A verifier MUST NOT trust a key merely because the AAC points to it.

### 12.12 Time-of-Check / Time-of-Use

Consumers SHOULD verify that `subject.release_ref`, `subject.commit`, AIBOM artifacts, and referenced evidence all correspond to the artifact actually being released. An AAC for a pull request or commit MUST NOT be reused for a different release artifact.

## 13. Versioning

This specification follows semantic versioning at the major.minor level. Within a minor version, additions are non-breaking (new OPTIONAL fields). Major version increments are reserved for breaking changes.

Implementations MUST reject AACs whose `schema_version` they do not understand. Implementations SHOULD support reading the immediately prior minor version. Major version transitions MUST be announced at least 90 days in advance with a migration guide.

## 14. Stewardship and Contact

Initial maintainer: Jason Lovell.

The maintainer commits to:

- transferring stewardship to a neutral standards body once at least two independent implementations exist;
- accepting and reviewing public comment on this specification;
- publishing breaking changes only with at least 90 days of notice and a migration guide;
- not making conformance claims about specific organizations or vendor products without their consent.

The `runwright.*` profiles in this repository are vendor profile examples. They are intentionally separate from `aac.core` and do not define the AAC format itself.

After publication, the public comment channel is the repository issue tracker. Contributions are accepted under CC BY 4.0 for specification text and Apache 2.0 for the reference verifier.

## 15. References

### 15.1 Normative References

- RFC 2119 — Key words for use in RFCs to Indicate Requirement Levels — https://www.rfc-editor.org/rfc/rfc2119
- RFC 3339 — Date and Time on the Internet: Timestamps — https://www.rfc-editor.org/rfc/rfc3339
- RFC 8174 — Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words — https://www.rfc-editor.org/rfc/rfc8174
- RFC 8259 — The JavaScript Object Notation (JSON) Data Interchange Format — https://www.rfc-editor.org/rfc/rfc8259
- RFC 8785 — JSON Canonicalization Scheme (JCS) — https://www.rfc-editor.org/rfc/rfc8785

### 15.2 Informative References

- CycloneDX Machine Learning Bill of Materials — https://www.cyclonedx.org/capabilities/mlbom
- SPDX Specification 3.0.1 — https://spdx.github.io/spdx-spec/v3.0.1/
- OpenTelemetry GenAI semantic conventions — https://opentelemetry.io/docs/specs/semconv/gen-ai/
- Model Context Protocol specification — https://modelcontextprotocol.io/specification
- Sigstore — https://www.sigstore.dev/
- in-toto Attestation Framework — https://in-toto.io/
- SLSA Supply-chain Levels for Software Artifacts — https://slsa.dev/
- OWASP MCP Top 10 — https://owasp.org/www-project-mcp-top-10/
- NIST AI Risk Management Framework — https://www.nist.gov/itl/ai-risk-management-framework
- NIST CAISI AI Agent Standards Initiative — https://www.nist.gov/caisi/ai-agent-standards-initiative
- ISO/IEC 42001:2023 — Artificial Intelligence Management System — https://www.iso.org/standard/81230.html
- EU AI Act, Regulation (EU) 2024/1689 — https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng
- A2A Protocol — https://github.com/a2aproject/A2A
- W3C Verifiable Credentials — https://www.w3.org/TR/vc-data-model/

---

*End of specification v0.2-candidate.4.*
