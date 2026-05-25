# Security Policy

AAC is a draft specification and reference verifier. Please do not report suspected vulnerabilities by opening a public issue if the report contains exploit details, private keys, credentials, or non-public evidence.

The reviewer-facing trust boundary is summarized in `THREAT_MODEL.md`.

Repository-level security posture and unresolved automated supply-chain signals are summarized in `SECURITY_POSTURE.md`.

## Reporting

Use GitHub private vulnerability reporting for this repository when available:
<https://github.com/jlov7/agent-assurance-case/security/advisories/new>.

If that is unavailable, contact the maintainer privately through the GitHub account that owns the repository.

## Disclosure

The target disclosure window is 90 days after acknowledgement, unless active exploitation or ecosystem risk requires a shorter coordinated timeline.

## Scope

In scope:

- Signature verification bypasses.
- Hash/canonicalization confusion.
- Duplicate-key or JSON parser ambiguity.
- Profile enforcement bypasses.
- Evidence reference binding failures.

Out of scope:

- Detector correctness claims outside the reference verifier.
- Legal compliance certification.
- Production key management, revocation, and enterprise trust-store policy, which are intentionally deferred from v0.2.
