# AAC Release Fingerprints

This file records public, reproducible fingerprints for the current AAC release candidate. It is release provenance, not independent validation.

## Current Release

- Repository: <https://github.com/jlov7/agent-assurance-case>
- Release: `v0.2-candidate.7`
- Release URL: <https://github.com/jlov7/agent-assurance-case/releases/tag/v0.2-candidate.7>
- Release commit: `689198d9c249a966a0abab6415ae8668efb512d9`
- DOI: <https://doi.org/10.5281/zenodo.20379393>
- Release published: `2026-05-25T12:47:41Z`
- Current public review issue: <https://github.com/jlov7/agent-assurance-case/issues/2>

## Signed Tag Check

```bash
git fetch --tags origin
git rev-list -n 1 v0.2-candidate.7
git tag -v v0.2-candidate.7
```

Expected release commit:

```text
689198d9c249a966a0abab6415ae8668efb512d9
```

Observed tag verification:

```text
Good "git" signature for jase.lovell@me.com with ED25519 key SHA256:WGevS9odnPKBtzTZjoVXSj2aexpZo4k6VL/dHaVaJdY
object 689198d9c249a966a0abab6415ae8668efb512d9
type commit
tag v0.2-candidate.7
```

## Release Verification Commands

From an immutable release checkout:

```bash
git clone --branch v0.2-candidate.7 --depth 1 https://github.com/jlov7/agent-assurance-case
cd agent-assurance-case
test "$(git rev-parse HEAD)" = "689198d9c249a966a0abab6415ae8668efb512d9"
./VERIFY-PUBLICATION-READY.sh
python verifier/check_vectors.py
python verifier/verify.py examples/pass-with-coverage.json --allow-demo-key
python verifier/verify.py examples/skill-poisoning-hold.json --allow-demo-key
python verifier/verify.py examples/critical-exfiltration-fail.json --allow-demo-key
```

Expected vector-checker output:

```text
AAC vectors: canonicalization accept=6 reject=5
AAC vectors: sign_verify=aac-v0.2-demo-sign-verify-pass-with-coverage
AAC vectors: valid
```

Each bundled example verifier command should end with:

```text
VERIFIED
```

From current `main`, reviewers can run the executable release-fingerprint verifier. It clones the immutable release tag into a temporary directory, checks the exact commit, verifies the signed tag with the public release-signing key, runs the publication gate, checks the conformance vectors, and verifies the bundled examples:

```bash
python3 scripts/verify_release_fingerprints.py
```

## Baseline Post-Release Evidence

The release tag is immutable review evidence. `main` may contain later documentation clarifications. This baseline evidence records a green post-release `main` state after the DOI and review-entry updates, without implying it will remain the latest `main` commit:

- Evidence checked: `2026-05-25`
- Workflow commit: `b64901780f3dedbb517161153ccc5ca3cde29a6d`
- AAC verifier workflow: <https://github.com/jlov7/agent-assurance-case/actions/runs/26408137384>
- CodeQL workflow: <https://github.com/jlov7/agent-assurance-case/actions/runs/26408137385>
- Open code-scanning alerts at last check: `0`

## Claim Boundary

These fingerprints make the release easier to verify and cite. They do not claim legal certification, employer endorsement, standards-body endorsement, production key governance, or accepted independent cryptographic review. Accepted independent review signals are tracked separately in [EXTERNAL_REVIEW_LEDGER.md](EXTERNAL_REVIEW_LEDGER.md).
