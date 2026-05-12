# Changelog

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
