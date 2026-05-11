# Profile: `runwright.skills.release` v0.1

**Profile ID:** `runwright.skills.release`  
**Profile version:** `0.1.0`  
**Builds on:** `aac.core` v0.2 at assurance level `basic` or higher.  
**Purpose:** Define the minimum evidence expected for an AAC issued against an agentic AI release whose primary surface is skills (Anthropic SKILL.md, OpenAI Codex skills, or equivalent skill formats).

This is a vendor profile published by Runwright. Independent vendors MAY define alternative skill profiles. This profile is intentionally 60-day-shippable: it requires detector classes that can be implemented with deterministic static analysis, bundle attestation, and simple scope checks. More research-heavy behavioral detectors are recommended but not required in v0.1.

## 1. Scope

This profile applies when `subject.subject_type` is `skill_bundle`, `skill`, `agent`, or `workflow` and the release contains at least one asset of type `skill` or `skill_bundle`.

## 2. Required Assets

An AAC declaring this profile MUST include at least one asset of type `skill` or `skill_bundle` in `assets`.

Every `skill` and `skill_bundle` asset MUST include a `digest`.

Each skill asset SHOULD include `metadata` with:

- `skill_format` — one of `anthropic`, `openai_codex`, `custom`;
- `manifest_path` — relative path to `SKILL.md` or equivalent;
- `bundled_scripts` — array of paths to executables bundled with the skill;
- `bundled_test_files` — array of paths to test files bundled with the skill, which may execute with local permissions through standard test runners.

## 3. Required Detector Coverage

`coverage.detector_runs` MUST include at least one run for each of the following categories, with `required: true` and `status` not in `{skipped, error}`:

- `skill-manifest-integrity` — parse and validate SKILL.md or equivalent, referenced assets, and bundle structure;
- `skill-secret-exposure` — detect hard-coded credentials, environment-variable scraping, or obvious exfiltration paths;
- `skill-executable-surface` — inventory scripts, test files, hooks, shell invocations, and other executable surfaces bundled with the skill;
- `skill-tool-scope` — detect bundled tools/scripts or requested scopes that exceed declared skill intent or manifest metadata.

The following detector classes are RECOMMENDED but are not required for v0.1 conformance because they need additional corpus quality, runtime traces, or research validation:

- `ddipe` — Document-Driven Implicit Payload Execution patterns;
- `shadow-skill` — trace-inferred skill behavior without a declared skill;
- `skill-drift` — runtime behavior divergence from declared or baseline skill behavior;
- `prompt-instruction-smuggling` — malicious natural-language instruction patterns that are not tied to an executable surface.

A required detector that has `status` in `{skipped, error}` MUST cause HOLD per SPEC §5.2. A required detector with `status: findings_present` does not automatically fail the case; the finding severities and policy decisions determine the verdict.

## 4. Required Evidence Linkage

For any finding with `category` containing `SKILL` or matching one of the above detector categories, `evidence_refs` MUST resolve to at least one entry in `evidence_artifacts`.

For any HOLD verdict caused by a high-severity skill finding, the AAC SHOULD include at least one `release_conditions` entry describing the remediation that would unblock the release.

## 5. Required AIBOM

This profile REQUIRES `aibom_ref`. The referenced AIBOM MUST enumerate every skill, skill bundle, and bundled script in `assets`. The `aibom_ref` URI MUST also appear in `evidence_artifacts` with role `aibom`.

## 6. Recommended Runtime Coverage

`coverage.runtime_coverage.status` SHOULD be at least `summary`. Skill behavior in production frequently diverges from declared behavior, and runtime evidence materially strengthens the assurance claim.

## 7. Verifier Behavior

A verifier processing an AAC declaring this profile MUST:

- apply all `aac.core` rules;
- reject the AAC if no `skill` or `skill_bundle` asset is present;
- reject the AAC if any skill asset lacks a `digest`;
- reject the AAC if any required detector category from §3 is absent or has `status` in `{skipped, error}`;
- reject the AAC if `aibom_ref` is absent or absent from `evidence_artifacts`;
- reject the AAC if any `evidence://` reference in findings, detector runs, eval results, runtime trace refs, `aibom_ref`, or `graph_snapshot_ref` is absent from `evidence_artifacts`;
- recompute the verdict and reject if it does not match `verdict`.
