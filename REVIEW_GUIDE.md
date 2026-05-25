# AAC External Review Guide

This guide is for independent reviewers who want to challenge the Agent Assurance Case (AAC) draft before relying on it or building against it.

## Release Under Review

- Repository: <https://github.com/jlov7/agent-assurance-case>
- Release: `v0.2-candidate.7`
- Release commit: the Git tag target for `v0.2-candidate.7`
- DOI: pending Zenodo archival
- Status: public draft candidate, not v1.0

This file is a living review guide on `main`. For an immutable review target, use the release tag above; the DOI is added after Zenodo archives the GitHub Release. Commands marked `main` use review tooling added after `v0.2-candidate.7`; the underlying vector files already exist in the release.

## Fast Verification Path

```bash
git clone --branch v0.2-candidate.7 --depth 1 https://github.com/jlov7/agent-assurance-case
cd agent-assurance-case
./VERIFY-PUBLICATION-READY.sh
python verifier/verify.py examples/pass-with-coverage.json --allow-demo-key
python verifier/verify.py examples/skill-poisoning-hold.json --allow-demo-key
python verifier/verify.py examples/critical-exfiltration-fail.json --allow-demo-key
```

Expected final verifier line for each example:

```text
VERIFIED
```

On `main`, reviewers can also run the standalone vector checker:

```bash
git clone --depth 1 https://github.com/jlov7/agent-assurance-case
cd agent-assurance-case
python verifier/check_vectors.py
```

Expected output:

```text
AAC vectors: canonicalization accept=6 reject=5
AAC vectors: sign_verify=aac-v0.2-demo-sign-verify-pass-with-coverage
AAC vectors: valid
```

The demo key path is only for bundled examples. A production review should supply an issuer public key with `--public-key`.

## What To Challenge

High-value review areas:

- **Canonicalization:** do the published byte vectors fully constrain the JSON subset AAC accepts?
- **Signature and hash binding:** can any mutable field affect the verdict without being covered by `evidence.content_hash` and the Ed25519 signature?
- **Schema/profile/verifier drift:** can the JSON Schema accept a case that the profile or verifier later rejects for a required field?
- **Verdict recomputation:** can a declared `pass`, `hold`, or `fail` disagree with the recomputed verdict?
- **Evidence binding:** can an `evidence://` reference that matters to the release decision escape `evidence_artifacts` digest binding?
- **Profile separation:** does `aac.core` remain the portable baseline while `runwright.*` profiles remain opt-in overlays?
- **Key trust:** does the verifier avoid trusting `public_key_ref` just because the AAC names it?
- **Freshness and replay:** are expiry and issued-at semantics explicit enough for a consumer to reject stale cases?
- **Privacy:** could AAC fields leak tenant, project, prompt, or evidence-vault topology when shared externally?

## Expected Failure Handling

Useful findings should include the smallest AAC example that demonstrates the issue and the expected disposition:

- schema issue: the case is accepted or rejected incorrectly before verifier logic;
- canonicalization issue: two semantically identical payloads produce unexpected bytes or hashes;
- signature issue: verification succeeds when any signed field has changed;
- verdict issue: the verifier prints `VERIFIED` while the recomputed verdict is wrong;
- profile issue: `aac.core` and a vendor profile disagree about a field without saying so;
- privacy issue: a required field forces disclosure that should be reference-only or redacted.

Security-sensitive reports should follow `SECURITY.md` instead of a public issue.

## Current Validation Boundary

What is true today:

- the release is signed and archived;
- the reference verifier has regression tests for previously identified trust-critical bug classes;
- canonicalization and sign/verify behavior are pinned by checked-in test vectors;
- `python verifier/check_vectors.py` exposes those vectors as a standalone conformance gate on `main`;
- GitHub Actions run the repository conformance gate on `main`.

What is not claimed:

- no legal, regulatory, or compliance certification;
- no employer, client, vendor, standards-body, or lab endorsement;
- no proof that a detector's semantic findings are correct;
- no production key rotation, revocation, or enterprise trust-store policy;
- no recorded independent verifier implementation in this repository yet.

Accepted external review signals are tracked in [EXTERNAL_REVIEW_LEDGER.md](EXTERNAL_REVIEW_LEDGER.md).

## Good Review Contributions

The most useful contributions are concrete and runnable:

- an independent verifier or parser that agrees or disagrees with the vectors;
- output from `python verifier/check_vectors.py`, or equivalent byte-level output from an independent implementation;
- a minimal failing AAC case;
- a profile proposal with machine-checkable requirements;
- a privacy or evidence-binding critique tied to a field path;
- a verifier patch with a regression test;
- a spec issue that maps a normative `MUST` to a missing schema, verifier, or test counterpart.

The current public review thread is [RFC: external review for AAC v0.2-candidate.7](https://github.com/jlov7/agent-assurance-case/issues/2). Focused new reports can use the [external review issue form](https://github.com/jlov7/agent-assurance-case/issues/new?template=external-review.yml). Use private vulnerability reporting for bypasses, parser ambiguity, signature confusion, or anything involving non-public evidence or keys.
