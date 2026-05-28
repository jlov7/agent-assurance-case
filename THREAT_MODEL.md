# Threat Model

This document summarizes the security assumptions for AAC v0.2-candidate.8.
The normative security rules remain in `SPEC.md`; this file is a reviewer-facing
map of the trust boundary.

## Assets Protected

- The integrity of the AAC document and its deterministic PASS/HOLD/FAIL verdict.
- The binding between a release subject, its evidence metadata, and the signing identity.
- The binding between material `evidence://` references and immutable evidence artifact digests.
- The distinction between a verified release case and an unverified or unsupported one.

## Attacker Model

AAC assumes an attacker may:

- edit any unsigned AAC field before verification;
- mutate `evidence.signed_by`, `signed_at`, `key_id`, or `public_key_ref`;
- provide duplicate JSON object members that different parsers might interpret differently;
- exploit JSON number, Unicode, or canonicalization edge cases;
- claim a stronger profile than the verifier actually supports;
- omit detector coverage, inventory, AIBOM, or evidence artifacts while still declaring PASS;
- point `public_key_ref` at an attacker-controlled key;
- reuse an old AAC for a different release.

AAC v0.2 does not assume the reference verifier can:

- detect compromised detectors;
- validate production key rotation or revocation;
- prove external evidence-vault availability;
- validate organizational approval authority chains;
- certify legal compliance.

## Required Fail-Closed Behavior

A verifier must return `NOT VERIFIED` unless all of the following hold:

- JSON parsing rejects duplicate object members and non-standard numeric constants.
- Schema validation passes with format checks enabled.
- Timestamps are UTC RFC3339 strings ending in `Z`.
- The content hash recomputes exactly over the payload with only
  `evidence.content_hash` and `evidence.signature` nulled.
- The Ed25519 signature verifies against a trusted supplied key, or against the
  explicitly enabled bundled demo key for bundled examples only.
- The declared profile and profile version are supported.
- Profile rules are enforced without weakening `aac.core`.
- The deterministic verdict recomputes to the declared verdict.

## Trust Boundaries

`public_key_ref` is signed metadata, not a trust root. Consumers must obtain
trusted public keys out of band through a keyring, transparency log, DID
resolver, Sigstore identity, or equivalent organizational process.

`evidence://` references are pointers into an issuer-controlled evidence vault.
They must be bound through `evidence_artifacts` with immutable digests when a
profile treats them as material evidence.

The reference verifier is intentionally small and readable. High-stakes
deployments should use vetted cryptographic and canonicalization libraries and
should add organization-specific key, revocation, approval, and evidence-vault
policy checks.

The reference verifier's canonicalizer is restricted to the AAC v0.2 supported
JSON value domain. The repository publishes byte-level fixtures in
`test-vectors/canonicalization-v0.2.json` for strings, literals, safe integers,
nested sorting, UTF-16 property ordering, and rejection of floats, unsafe
integers, and lone surrogates. Full RFC 8785 number support for arbitrary
floating-point JSON values is a non-goal for this reference verifier.

## Non-Goals

- AAC is not an SBOM, AIBOM, trace format, policy engine, detector engine, or
  legal compliance certification.
- AAC does not judge whether a detector is semantically correct.
- AAC does not make unsupported profiles safe by falling back to core-only
  verification.
- AAC does not make demo keys production-safe.
- The v0.2 reference verifier does not accept arbitrary RFC 8785 numeric input;
  floats must be encoded as strings or safe integers.

## Residual Risks

- A compromised but trusted issuer key can sign misleading AACs.
- A complete-looking detector set can still miss a real vulnerability.
- A signed AAC can become stale after a release changes.
- Evidence artifacts can become unavailable even when their digests remain
  verifiable.
- Organizational policies may require stricter approval and retention controls
  than AAC v0.2 encodes.
