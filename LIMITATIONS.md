# Limitations

- **Issuer trust:** a compromised but trusted issuer key can sign a misleading AAC. Expected failure mode: consumers must reject signatures from revoked or untrusted keys outside the AAC verifier.
- **Detector semantics:** AAC proves which checks were declared, bound, and passed; it does not prove a detector catches every real defect. Expected failure mode: weak detectors produce weak but signed evidence.
- **Canonicalization scope:** the reference verifier accepts only the AAC v0.2 supported JSON value domain: no floats, no unsafe integers, no lone surrogate code points. The `RFC8785-JCS` label is a family identifier, not a claim of full RFC 8785 conformance — see [Canonicalization is a constrained RFC 8785 subset](#canonicalization-is-a-constrained-rfc-8785-subset) below. Expected failure mode: unsupported numeric input returns `NOT VERIFIED`.
- **Replay and freshness:** AAC binds one `case_id`, subject, release reference, and timestamp; consumers must decide freshness for their own release process. Expected failure mode: stale AACs are rejected by policy, not by schema alone.
- **Evidence privacy:** `evidence://` references point to external vault objects and can leak tenant or process topology if published carelessly. Expected failure mode: publish derived or redacted AACs when sharing outside the issuer boundary.

## Canonicalization is a constrained RFC 8785 subset

AAC cases declare `evidence.signature_algorithm = "Ed25519-JCS-SHA256-v1"` and
`evidence.canonicalization = "RFC8785-JCS"`. These identifiers name the
canonicalization *family* the format targets. The reference verifier in
`verifier/verify.py` does **not** implement the full RFC 8785 number grammar.
By deliberate design it canonicalizes only the constrained value domain that AAC
v0.2 cases are allowed to use, and rejects the rest rather than guessing:

- floating-point numbers are rejected (encode decimals as strings);
- integers outside the JSON safe-integer range (±(2^53 − 1)) are rejected;
- lone UTF-16 surrogate code points are rejected;
- object keys are ordered by UTF-16 code-unit comparison, matching RFC 8785 for
  the supported value domain.

Implications for implementers and reviewers:

- A producer that emits floats or large integers and canonicalizes them with a
  full RFC 8785 library will produce bytes this verifier rejects. That is the
  intended failure mode (loud `NOT VERIFIED`), not silent divergence.
- Independent verifier implementations should reproduce this *subset* to stay
  byte-compatible with the published test vectors in
  `test-vectors/canonicalization-v0.2.json`, rather than assuming any RFC
  8785-compliant canonicalizer will interoperate.
- A future revision may widen the supported domain or adopt a vetted full
  RFC 8785 implementation; until then, treat `RFC8785-JCS` as "JCS over the AAC
  v0.2 value domain."
