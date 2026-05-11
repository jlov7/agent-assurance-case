# Agent Assurance Case (AAC) Specification

> A portable, signed, audit-grade evidence object for proving that an agentic AI workflow is safe enough to release.

**Status:** Draft v0.2-candidate. Open for comment.
**Initial steward:** Runwright (intended transfer to a neutral standards body once at least two independent implementations exist).
**License:** CC BY 4.0 for the specification text and examples; Apache 2.0 for the reference verifier.

---

## What this is

The Agent Assurance Case (AAC) is a signed JSON object that captures the evidence and verdict for a single release of an agentic AI workflow. The verdict — PASS, HOLD, or FAIL — is deterministically computable from the AAC's contents and is verifiable offline by any consumer using only the AAC document and the issuer's public key. The AAC is designed to function as audit evidence under regimes like the EU AI Act, ISO/IEC 42001, and NIST AI RMF.

## Repository layout

```
.
├── README.md                                          this file
├── SPEC.md                                            the formal draft specification
├── schemas/
│   └── agent-assurance-case-v0.2.schema.json          self-contained JSON Schema (draft 2020-12)
├── profiles/
│   ├── aac.core.md                                    the core profile — every AAC must satisfy this
│   ├── runwright.skills.release.md                    vendor profile for skill-bundle releases
│   └── runwright.mcp.release.md                       vendor profile for MCP-server releases
├── examples/
│   ├── pass-with-coverage.json                        PASS verdict with complete coverage
│   ├── skill-poisoning-hold.json                      HOLD verdict — DDIPE + missing approval
│   └── critical-exfiltration-fail.json                FAIL verdict — credential exfiltration policy deny
├── verifier/
│   ├── verify.py                                      Python reference verifier
│   ├── requirements.txt                               runtime deps
│   └── requirements-dev.txt                           test deps
└── tests/
    └── test_verifier.py                               regression tests against known bug classes
```

## Quick start

Verify the bundled examples (uses the demo key included in the verifier):

```bash
cd verifier
pip install -r requirements.txt
python verify.py ../examples/pass-with-coverage.json --allow-demo-key
python verify.py ../examples/skill-poisoning-hold.json --allow-demo-key
python verify.py ../examples/critical-exfiltration-fail.json --allow-demo-key
```

Production verification (use the issuer's real ed25519 public key):

```bash
python verify.py case.json --public-key issuer.pub
```

Note: without either `--public-key` or `--allow-demo-key`, the verifier returns `NOT VERIFIED`. The verifier does not silently skip signature verification.

## Run the test suite

```bash
pip install -r verifier/requirements-dev.txt
python -m pytest -q
```

The test suite includes regression tests for two trust-critical bug classes caught during adversarial review of v0.1: silent signature skip, and evidence metadata tampering. Both tests fail loudly if either bug regresses.

## Profiles

The schema defines object shape; a profile defines the minimum evidence expected for a use case. Every AAC must declare a profile.

- `aac.core` is the only profile defined in this core specification. It establishes the baseline every AAC must meet.
- `runwright.skills.release` and `runwright.mcp.release` are vendor profiles published by Runwright and stewarded separately. They build on `aac.core` and may not relax core rules.

Other organizations may define alternative profiles. A conforming verifier must not misreport the verdict; it may refuse to accept profiles whose required detector sets it does not implement.

## Relationship to other standards

- CycloneDX ML-BOM and SPDX 3.0 AI profiles — referenced by URI in `aibom_ref`. The AIBOM enumerates components; the AAC certifies release readiness.
- OpenTelemetry GenAI semantic conventions — runtime events should use OTel GenAI span shapes where applicable.
- Sigstore, in-toto, SLSA — AAC signatures use ed25519 by default and are compatible. The AAC complements rather than replaces SLSA provenance.
- W3C Verifiable Credentials — a future minor version may define an optional VC wrapper for cross-organization portability.
- OWASP MCP Top 10 — finding `category` values for MCP-related risks align with MCP01–MCP10 identifiers.

## How to contribute

Specific feedback wanted on whether the verdict semantics, asset model, compliance mapping language, hash-chain and signing model, and privacy posture are correct. Open an issue or pull request on the public repository. Contributions are accepted under CC BY 4.0 (specification text) and Apache 2.0 (verifier code).

## What changed from the unpublished v0.1 draft

- Signature verification is mandatory. No silent `VERIFIED` on missing public key.
- Evidence metadata (`signed_by`, `signed_at`, `public_key_ref`, algorithm identifiers) is now protected by the signature.
- Coverage is required. A no-assets / no-findings PASS is no longer structurally possible.
- Profiles are introduced. The schema alone cannot certify assurance level.
- Asset types expanded to include `agent`, `workflow`, `skill_bundle`, `identity`, `credential_ref`, `runtime`, `connector`, and `environment`.
- Verdict recomputation now checks inventory coverage, required detector runs, required evals, open release conditions, and undeclared asset references.
- Floats are rejected by the reference verifier to avoid incomplete RFC 8785 numeric canonicalization.
- Compliance-mapping language downgraded to "evidence candidate" rather than "satisfies control."
