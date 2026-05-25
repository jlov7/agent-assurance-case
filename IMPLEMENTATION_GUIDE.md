# AAC Implementation Guide

This guide is for people building an independent AAC parser, verifier, or
profile checker. It is not a replacement for [SPEC.md](SPEC.md). The spec is
normative; this file is a practical map from the spec to runnable conformance
evidence.

AAC `v0.2-candidate.7` is a public draft candidate. Implementations should say
they target this candidate, not a stable AAC standard.

## Target

- Release: `v0.2-candidate.7`
- Release commit: `689198d9c249a966a0abab6415ae8668efb512d9`
- Schema: [`schemas/agent-assurance-case-v0.2.schema.json`](schemas/agent-assurance-case-v0.2.schema.json)
- Core profile: [`profiles/aac.core.md`](profiles/aac.core.md)
- Canonicalization vectors: [`test-vectors/canonicalization-v0.2.json`](test-vectors/canonicalization-v0.2.json)
- Sign/verify vector: [`test-vectors/sign-verify-v0.2.json`](test-vectors/sign-verify-v0.2.json)

## Minimum Verifier Pipeline

A verifier that claims support for AAC v0.2-candidate.7 should do these steps in
this order:

1. Parse JSON as UTF-8 and reject duplicate object member names.
2. Reject unsupported JSON values before canonicalization: floats, `NaN`,
   `Infinity`, unsafe integers outside the JSON safe-integer range, and lone
   UTF-16 surrogate code points.
3. Validate the document against the v0.2 JSON Schema with format checks.
4. Reject unknown `schema_version` values.
5. Reject unsupported `canonicalization` or `signature_algorithm` values.
6. Recompute each policy decision `inputs_hash`.
7. Recompute `evidence.content_hash` over the canonical signed payload.
8. Verify the Ed25519 signature over the same canonical signed payload bytes.
9. Enforce the declared profile if the verifier claims to support it.
10. Recompute the deterministic `pass`, `hold`, or `fail` verdict.
11. Return `NOT VERIFIED` for any failed structural, hash, signature, profile, or
    verdict check.

Signature verification must happen before profile-conformance reporting can
create a confusing success path. A verifier must never silently skip signature
verification.

## Canonicalization Scope

AAC v0.2-candidate.7 uses an RFC 8785/JCS-style canonical JSON byte format over a
deliberately constrained JSON value domain:

- objects are sorted by member name;
- strings are emitted as JSON strings without lone surrogates;
- integers must be in the JSON safe-integer range;
- floats and nonstandard numbers are rejected;
- arrays preserve order;
- booleans and null use JSON spellings.

Production implementations should use a vetted canonicalization library where
one is available and configure it to match the AAC-supported value domain. If a
library accepts values outside that domain, reject those values before
canonicalization.

## Required Vector Checks

Run the reference vector checker:

```bash
python verifier/check_vectors.py
```

Expected output:

```text
AAC vectors: canonicalization accept=6 reject=5
AAC vectors: sign_verify=aac-v0.2-demo-sign-verify-pass-with-coverage
AAC vectors: valid
```

An independent implementation should publish equivalent evidence:

- accepted canonicalization vector IDs and canonical bytes;
- rejected canonicalization vector IDs and rejection reasons;
- sign/verify vector ID;
- computed `content_hash`;
- signature verification result;
- implementation language, library versions, and commit or release tag.

## Profile Behavior

`aac.core` is the portable baseline. Vendor profiles, including `runwright.*`,
are opt-in overlays. An implementation must not treat a structurally valid AAC as
satisfying a stronger profile unless it explicitly supports and enforces that
profile.

Required behavior:

- unsupported `profile_id` returns `NOT VERIFIED`;
- unsupported profile version returns `NOT VERIFIED`;
- a supported profile may add checks;
- a supported profile must not relax core PASS/HOLD/FAIL conditions.

## Trust Boundary

The signed `public_key_ref` is metadata, not a trust root. Consumers must obtain
trusted issuer keys from an out-of-band trust store, transparency log, Sigstore
identity, DID resolver, or equivalent organizational key-management process.

The verifier proves only that the AAC bytes are structurally valid, signed by a
trusted key supplied by the consumer, and internally consistent under the
implemented profile rules. It does not prove detector semantics, organizational
authority, legal compliance, or production key rotation.

## Useful Independent Evidence

The most useful external implementation report includes:

- repository URL or archived source bundle;
- implementation commit;
- target AAC release and commit;
- commands used to run vector checks;
- exact vector output;
- any divergences from the reference verifier;
- whether the implementation supports only `aac.core` or also `runwright.*`
  profiles;
- a filled [`review-report-template.json`](review-report-template.json) validated
  with `python verifier/validate_review_report.py`.

Accepted independent implementation signals are tracked only after maintainer
review in [EXTERNAL_REVIEW_LEDGER.md](EXTERNAL_REVIEW_LEDGER.md). A private note,
star, or informal "looks good" does not count.

Implementation authors can submit focused public evidence through the
[implementation report issue form](https://github.com/jlov7/agent-assurance-case/issues/new?template=implementation-report.yml).
