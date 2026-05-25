# Changelog

## v0.2-candidate.7

- Supersedes `v0.2-candidate.6` without rewriting public history.
- Adds a standalone review guide, external review ledger, and structured external-review intake.
- Adds a standalone conformance-vector checker for canonicalization and sign/verify byte vectors.
- Adds Dependabot coverage, least-privilege workflow permissions, CodeQL scanning, and protected-branch merge-policy documentation.
- Updates verifier dependency floors while preserving verifier, schema, and verdict semantics.
- Zenodo DOI: pending after GitHub Release archival.

## v0.2-candidate.6

- Publishes a signed replacement candidate from current `main` so release provenance no longer depends on the older unsigned `v0.2-candidate.5` tag.
- Aligns public-status wording now that the repository is public.
- Aligns citation and independence metadata with the maintainer's ORCID identity.
- Keeps verifier and schema semantics unchanged from `v0.2-candidate.5`; this is a provenance and metadata release.
- Zenodo DOI: <https://doi.org/10.5281/zenodo.20345018>.

## v0.2-candidate.5

- Recomputes and verifies `policy_decisions[*].inputs_hash` over the canonical policy decision payload with `inputs_hash` removed.
- Refreshes bundled examples and the sign/verify test vector so policy input hashes are real digest bindings, not placeholders.
- Adds regression coverage for mismatched policy input hashes.
- Documents policy input hash verification in `SPEC.md`.

## v0.2-candidate.4

- Requires `subject.subject_type` in the JSON Schema so the normative shape matches `aac.core` and the reference verifier (no optional drift).
- Supersedes the private `v0.2-candidate.3` release candidate before public publication.
- Adds the personal-work independence notice.
- Removes demo-case resigning from the public verifier CLI while keeping internal test signing helpers.
- Tightens Runwright release profiles so they require `aac.core` assurance level `basic` or higher.
- Aligns `skill` subject-type handling across the schema, specification, profile, and verifier tests.
- Adds explicit JCS surrogate rejection coverage and replaces non-official EU AI Act references with EUR-Lex.
- Aligns verifier execution order with the specification's hash/signature-before-profile procedure.
- Adds a standalone threat model and publication-gate checks for candidate version drift.
- Adds maintainer ORCID metadata to `CITATION.cff`.
- Publishes byte-level canonicalization fixtures for the AAC-supported JCS subset.
- Publishes a sign/verify conformance vector and verifier conformance checklist.
- Adds a one-page overview, explicit limitations, and clearer vendor-profile positioning.
- Replaces the README ASCII logo with a tracked SVG wordmark and updates the license map for public-release assets.

## v0.2-candidate.3

- Pins the draft schema URI to the `v0.2-candidate.3` Git tag.
- Moves bundled demo identity and key references from Runwright-owned URLs to repository-scoped AAC demo metadata.
- Adds a demo public key file for offline example verification.
- Hardens the reference verifier against unsupported profile versions, duplicate identifiers, unbound release-profile evidence, incorrect AIBOM artifact roles, unsafe JCS integer values, and empty-asset core cases.
- Adds regression coverage for the verifier hardening cases.
- Updates publication metadata and release checklist for GitHub Release, Zenodo DOI, and ORCID workflows.

## v0.2-candidate.2

- Pre-public candidate with schema, profiles, examples, reference verifier, tests, CI, and citation metadata.
- Superseded before public DOI archival; do not use this tag for publication.
