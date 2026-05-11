# Profile: `aac.core` v0.2

**Profile ID:** `aac.core`
**Profile version:** `0.2.0`
**Purpose:** Define the minimum structural requirements every AAC must satisfy, regardless of vendor or use case.

This is the only profile defined within the core specification. All other profiles (including vendor-specific profiles such as `runwright.skills.release` and `runwright.mcp.release`) are published as separate documents and MUST NOT relax the requirements in this profile.

## 1. Scope

The `aac.core` profile applies to any agentic AI release that uses the AAC format. It establishes the minimum bar for structural integrity, signing, and coverage that every AAC must meet.

## 2. Assurance Levels

A `profile.assurance_level` value when declaring `aac.core` MUST be one of:

- `structural` — the AAC is well-formed, signed, and verifiable, but no inventory or detector commitments are claimed.
- `basic` — the AAC additionally declares `coverage.inventory_status == complete` and at least one required detector run.
- `standard` — the AAC additionally references an AIBOM, declares runtime coverage of at least `summary`, and includes at least one compliance mapping.
- `strict` — the AAC additionally requires `runtime_coverage.status == full` and at least one signed approval for any HOLD resolution.

## 3. Required Fields Beyond the Schema

When declaring `aac.core` at any assurance level, an AAC MUST include:

- `subject.subject_type` populated (not absent);
- `coverage.inventory_methods` non-empty;
- `evidence.signature_algorithm` set to `Ed25519-JCS-SHA256-v1`;
- `evidence.canonicalization` set to `RFC8785-JCS`.

## 4. Verifier Behavior

A verifier processing an AAC declaring `aac.core` MUST:

- apply all FAIL and HOLD rules defined in SPEC §5;
- recompute the verdict deterministically per SPEC §6.5;
- reject any AAC whose declared `verdict` does not match the recomputed verdict;
- reject any AAC whose `assurance_level` requirements are not satisfied by the contents.

A verifier MAY apply additional rules from higher-level profiles or from organizational policy, provided those rules only strengthen the core rules.

## 5. Conformance

An implementation conforms to the `aac.core` profile if it can:

- emit AACs that pass an independent verifier;
- verify AACs emitted by any other conforming implementation;
- correctly recompute verdicts for the bundled example set in the reference repository.

The reference repository's test suite is the minimum conformance test. Additional profile-specific test suites apply when claiming higher profiles.
