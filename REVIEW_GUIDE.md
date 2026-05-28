# AAC External Review Guide

This guide is for independent reviewers who want to challenge the Agent Assurance Case (AAC) draft before relying on it or building against it.

## Release Under Review

- Repository: <https://github.com/jlov7/agent-assurance-case>
- Release: `v0.2-candidate.8`
- Release commit: `689198d9c249a966a0abab6415ae8668efb512d9`
- DOI: <https://doi.org/10.5281/zenodo.20379393>
- Status: public draft candidate, not v1.0

This file is a living review guide on `main`. For an immutable review target, use the release tag and DOI above. The `v0.2-candidate.8` release includes the standalone vector checker and the checked-in vector files; current `main` may include later documentation clarifications. Public release fingerprints, signed-tag checks, CI run links, and claim boundaries are recorded in [RELEASE_FINGERPRINTS.md](RELEASE_FINGERPRINTS.md).

## Fast Verification Path

```bash
git clone --branch v0.2-candidate.8 --depth 1 https://github.com/jlov7/agent-assurance-case
cd agent-assurance-case
./VERIFY-PUBLICATION-READY.sh
python3 verifier/verify.py examples/pass-with-coverage.json --allow-demo-key
python3 verifier/verify.py examples/skill-poisoning-hold.json --allow-demo-key
python3 verifier/verify.py examples/critical-exfiltration-fail.json --allow-demo-key
```

Expected final verifier line for each example:

```text
VERIFIED
```

Reviewers can also run the standalone vector checker from the `v0.2-candidate.8` release tag:

```bash
git clone --branch v0.2-candidate.8 --depth 1 https://github.com/jlov7/agent-assurance-case
cd agent-assurance-case
python3 verifier/check_vectors.py
```

Expected output:

```text
AAC vectors: canonicalization accept=6 reject=5
AAC vectors: sign_verify=aac-v0.2-demo-sign-verify-pass-with-coverage
AAC vectors: valid
```

The demo key path is only for bundled examples. A production review should supply an issuer public key with `--public-key`.

## Review Recipes

Use one of these small paths if you want to contribute a focused review without
reading the whole repository first.

### 10-Minute Vector Check

Run the release-pinned vector checker and paste the command/output into the
public review thread or a structured report:

```bash
git clone --branch v0.2-candidate.8 --depth 1 https://github.com/jlov7/agent-assurance-case
cd agent-assurance-case
python3 verifier/check_vectors.py
```

Useful result: the output matches the expected three lines above, or you can
explain exactly where an independent implementation disagrees.

### 30-Minute Contract Drift Check

Pick one normative `MUST` from `SPEC.md` or `profiles/aac.core.md` and trace it
to one of:

- JSON Schema enforcement;
- verifier logic;
- a regression test;
- an explicit human gate or profile requirement.

Useful result: a field path, spec section, and the missing enforcement point, or
a note that the selected `MUST` is covered.

### Evidence-Binding Check

Try to find an `evidence://` reference that affects release meaning but is not
covered by `evidence_artifacts` digest binding. Include the field path and the
smallest AAC case if you find one.

Useful result: a minimal failing case, or a review note that the checked paths
are bound as expected.

### Ledger-Ready Report

For a report that can be considered for [EXTERNAL_REVIEW_LEDGER.md](EXTERNAL_REVIEW_LEDGER.md),
fill [`review-report-template.json`](review-report-template.json) and validate it
from current `main`:

```bash
python3 verifier/validate_review_report.py path/to/review-report.json
```

Useful result: `AAC review report: valid submission.` plus the filled JSON or a
public artifact link. Validator success proves report shape and target identity,
not that the review conclusion is true.

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
- `python3 verifier/check_vectors.py` exposes those vectors as a standalone conformance gate in the `v0.2-candidate.8` release and on `main`;
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
- output from `python3 verifier/check_vectors.py`, or equivalent byte-level output from an independent implementation;
- a minimal failing AAC case;
- an implementation report using [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md);
- a profile proposal with machine-checkable requirements;
- a privacy or evidence-binding critique tied to a field path;
- a verifier patch with a regression test;
- a spec issue that maps a normative `MUST` to a missing schema, verifier, or test counterpart.

## Structured Review Reports

Reviewers who want their result considered for the external review ledger can submit a machine-checkable report using [`review-report-template.json`](review-report-template.json) and [`review-report.schema.json`](review-report.schema.json).

Validate a filled report before submitting:

```bash
python3 verifier/validate_review_report.py path/to/review-report.json
```

Expected output for a structurally valid submission:

```text
AAC review report: valid submission.
```

The validator checks schema conformance, target release identity, populated reviewer and reproduction fields, duplicate JSON member rejection, duplicate finding IDs, claim-boundary fields, public artifact presence for independent-review claims, and exact AAC v0.2 vector output for parser or vector-focused reviews. Reports that claim independent review must not be marked security-sensitive. Validation does not make the report true; maintainers still inspect the evidence before adding anything to [EXTERNAL_REVIEW_LEDGER.md](EXTERNAL_REVIEW_LEDGER.md).

The current public review thread is [RFC: external review for AAC v0.2-candidate.8](https://github.com/jlov7/agent-assurance-case/issues/2). Focused new reports can use the [external review issue form](https://github.com/jlov7/agent-assurance-case/issues/new?template=external-review.yml), and independent parser/verifier authors can use the [implementation report issue form](https://github.com/jlov7/agent-assurance-case/issues/new?template=implementation-report.yml). Use private vulnerability reporting for bypasses, parser ambiguity, signature confusion, or anything involving non-public evidence or keys.
