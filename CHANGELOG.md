# Changelog

## v0.2-candidate.4

- Supersedes the private `v0.2-candidate.3` release candidate before public publication.
- Adds the personal-work independence notice.
- Removes demo-case resigning from the public verifier CLI while keeping internal test signing helpers.
- Tightens Runwright release profiles so they require `aac.core` assurance level `basic` or higher.
- Aligns `skill` subject-type handling across the schema, specification, profile, and verifier tests.
- Adds explicit JCS surrogate rejection coverage and replaces non-official EU AI Act references with EUR-Lex.
- Aligns verifier execution order with the specification's hash/signature-before-profile procedure.
- Adds a standalone threat model and publication-gate checks for candidate version drift.

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
