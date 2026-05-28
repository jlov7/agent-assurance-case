# What This Is / What This Is Not

A one-page statement of scope and claims for the Agent Assurance Case (AAC).
If you are quoting this project in a post, article, review, or decision, quote
from here.

## What AAC is

- A **draft specification** (`SPEC.md`) for a portable JSON evidence object that
  records what was checked before an agentic AI workflow is released: inventory,
  detector coverage, findings, policy decisions, release conditions, a
  deterministic verdict, and an Ed25519 signature.
- A **reference verifier** (`verifier/verify.py`) that recomputes the verdict
  offline — no network, no LLM — and refuses to trust the issuer's declared
  result.
- **Signed, reproducible examples** and byte-level test vectors that pin
  canonicalization and sign/verify behavior.
- **Personal, independent research and development**, published openly and
  invited for adversarial review.

## What AAC is not

- **Not a certification or compliance attestation.** A `VERIFIED` result means
  the evidence object is internally consistent, correctly signed, and the
  verdict was recomputed deterministically — not that the underlying system is
  safe, compliant, or fit for any purpose.
- **Not proof that detectors are complete.** AAC records *which* checks ran and
  passed; it cannot prove a weak detector caught every real defect. Weak inputs
  produce weak — but honestly signed — evidence.
- **Not independently validated yet.** No external cryptographic review, no
  independent verifier implementation, and no third-party audit has been
  accepted into this repository. Current status is tracked in
  [EXTERNAL_REVIEW_LEDGER.md](EXTERNAL_REVIEW_LEDGER.md).
- **Not a full RFC 8785 implementation.** Canonicalization covers a constrained
  subset of the JCS value domain; see
  [LIMITATIONS.md](LIMITATIONS.md#canonicalization-is-a-constrained-rfc-8785-subset).
- **Not an employer or institutional work product.** See the Independence
  Notice in [README.md](README.md#independence-notice).

## The verification boundary

| Property | Status | Evidence |
| --- | --- | --- |
| Schema + verdict + signature checks run deterministically offline | Self-verified | `tests/`, `VERIFY-PUBLICATION-READY.sh` |
| Canonicalization / sign-verify pinned to published vectors | Self-verified | `test-vectors/` |
| Release tag is signed and DOI-archived | Self-verified | `RELEASE_FINGERPRINTS.md`, Zenodo |
| Independent cryptographic / implementation review | **Not yet done** | `EXTERNAL_REVIEW_LEDGER.md` |
| Real-world detector adequacy | **Out of scope** | `LIMITATIONS.md` |

## How to help

The most useful contributions are adversarial: an independent verifier
implementation, a canonicalization counter-example, a verdict-semantics
challenge, or a privacy-leakage scenario. Start from
[REVIEW_GUIDE.md](REVIEW_GUIDE.md#review-recipes) and file findings through the
external review issue form.
