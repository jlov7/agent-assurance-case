# Limitations

- **Issuer trust:** a compromised but trusted issuer key can sign a misleading AAC. Expected failure mode: consumers must reject signatures from revoked or untrusted keys outside the AAC verifier.
- **Detector semantics:** AAC proves which checks were declared, bound, and passed; it does not prove a detector catches every real defect. Expected failure mode: weak detectors produce weak but signed evidence.
- **Canonicalization scope:** the reference verifier accepts only the AAC v0.2 supported JSON value domain: no floats, no unsafe integers, no lone surrogate code points. Expected failure mode: unsupported numeric input returns `NOT VERIFIED`.
- **Replay and freshness:** AAC binds one `case_id`, subject, release reference, and timestamp; consumers must decide freshness for their own release process. Expected failure mode: stale AACs are rejected by policy, not by schema alone.
- **Evidence privacy:** `evidence://` references point to external vault objects and can leak tenant or process topology if published carelessly. Expected failure mode: publish derived or redacted AACs when sharing outside the issuer boundary.
