<div align="center">

```text
   /$$$$$$   /$$$$$$   /$$$$$$
  /$$__  $$ /$$__  $$ /$$__  $$
 | $$  \ $$| $$  \ $$| $$  \__/
 | $$$$$$$$| $$$$$$$$| $$
 | $$__  $$| $$__  $$| $$
 | $$  | $$| $$  | $$| $$    $$
 | $$  | $$| $$  | $$|  $$$$$$/
 |__/  |__/|__/  |__/ \______/
```

# Agent Assurance Case

**A portable, signed, audit-grade evidence object for agentic AI release assurance.**

[![CI](https://github.com/jlov7/agent-assurance-case/actions/workflows/ci.yml/badge.svg)](https://github.com/jlov7/agent-assurance-case/actions/workflows/ci.yml)
![Status](https://img.shields.io/badge/status-draft%20v0.2--candidate.3-2f6f9f)
![Verifier](https://img.shields.io/badge/verifier-deterministic-0f766e)
![Signature](https://img.shields.io/badge/signature-Ed25519--JCS-111827)
![License](https://img.shields.io/badge/license-CC--BY--4.0%20%2B%20Apache--2.0-blue)

</div>

Agent Assurance Case (AAC) is a draft specification and reference verifier for one release-critical question:

> Can this agentic AI workflow be released, and can an auditor verify the evidence offline?

An AAC is a JSON object that binds inventory, detector coverage, findings, policy decisions, release conditions, compliance evidence candidates, a deterministic verdict, and an Ed25519 signature. A verifier recomputes the verdict without network calls, without an LLM, and without trusting the issuer's declared result.

## Why It Exists

Agentic systems are assembled from workflows, tools, skills, prompts, memory stores, models, datasets, credentials, policies, and runtime environments. Existing standards cover important adjacent layers: SBOMs and AI BOMs enumerate components, provenance frameworks describe how artifacts were built, and governance frameworks describe organizational obligations.

AAC fills the release-decision gap: a small, portable assurance record that says what was checked, what failed, what is held, what passed, who signed it, and whether the evidence still verifies.

AAC is not a legal compliance certification. It is a signed evidence object that can support release review, audit preparation, and independent verification.

## Quick Start

Verify the bundled examples with the demo key:

```bash
pip install -r verifier/requirements.txt
python verifier/verify.py examples/pass-with-coverage.json --allow-demo-key
python verifier/verify.py examples/skill-poisoning-hold.json --allow-demo-key
python verifier/verify.py examples/critical-exfiltration-fail.json --allow-demo-key
```

`--allow-demo-key` is only for the bundled examples. It is not a production trust mode. The demo public key is published at `keys/demo-issuer-v0.2.pub` so reviewers can inspect the exact key used by the examples.

Verify a production case with an issuer key:

```bash
python verifier/verify.py case.json --public-key issuer.pub
```

Run the conformance tests:

```bash
pip install -r verifier/requirements-dev.txt
python -m pytest tests/ -q
```

Run the publication gate:

```bash
./VERIFY-PUBLICATION-READY.sh
```

## What The Verifier Checks

- JSON Schema conformance with format checks enabled.
- Duplicate JSON object keys, `NaN`, `Infinity`, floats, and unsafe integers are rejected.
- All timestamps must be UTC RFC 3339 strings ending in `Z`.
- `evidence.content_hash` is recomputed over the signed payload.
- `evidence.signature` is verified with Ed25519.
- Unsupported profiles return `NOT VERIFIED`.
- PASS/HOLD/FAIL is recomputed deterministically from the case contents.
- A verifier never silently skips signature verification.

## Repository Layout

```text
.
├── README.md
├── SPEC.md
├── CITATION.cff
├── CHANGELOG.md
├── PUBLICATION.md
├── keys/
│   └── demo-issuer-v0.2.pub
├── schemas/
│   └── agent-assurance-case-v0.2.schema.json
├── profiles/
│   ├── aac.core.md
│   ├── runwright.skills.release.md
│   └── runwright.mcp.release.md
├── examples/
│   ├── pass-with-coverage.json
│   ├── skill-poisoning-hold.json
│   └── critical-exfiltration-fail.json
├── verifier/
│   ├── verify.py
│   ├── requirements.txt
│   └── requirements-dev.txt
└── tests/
    └── test_verifier.py
```

## Profiles

The schema defines shape. A profile defines the evidence bar.

`aac.core` is the portable baseline. It is the part intended to stand independently of any one product, vendor, or implementation.

`runwright.skills.release` and `runwright.mcp.release` are vendor profiles included as reference examples. They build on `aac.core`; they do not define AAC itself and they may not relax the core rules. Other organizations can define their own profiles for their own assurance surfaces.

This separation is deliberate: AAC can be cited, implemented, archived, and discussed as a standalone assurance format even if Runwright evolves separately or is built by someone else.

## Status

Current draft: `v0.2-candidate.3`.

The draft schema identifier is pinned to the candidate tag:

```text
https://raw.githubusercontent.com/jlov7/agent-assurance-case/v0.2-candidate.3/schemas/agent-assurance-case-v0.2.schema.json
```

This draft supersedes an unpublished v0.1 design that had trust-critical defects around signature verification and evidence metadata binding. Those bug classes now have regression tests.

Do not claim AAC v1.0 conformance yet. This repository is open for implementation feedback on:

- verdict semantics;
- evidence binding and canonicalization;
- profile boundaries;
- privacy posture for external evidence artifacts;
- compatibility with audit and release-review workflows.

## Standards Alignment

AAC is designed to sit beside, not replace:

- CycloneDX ML-BOM and SPDX AI profiles for component inventory;
- OpenTelemetry GenAI conventions for runtime evidence;
- Sigstore, in-toto, and SLSA for provenance;
- NIST AI RMF, ISO/IEC 42001, and EU AI Act documentation workflows;
- W3C Verifiable Credentials for future portability wrappers.

## Citation

This repository includes `CITATION.cff` so GitHub and archival systems can generate software citations.

After the first public GitHub release is archived by Zenodo, add the Zenodo DOI to `CITATION.cff`, this README, and the release notes. If you want the work to appear on an ORCID record, add the DOI as a work item through ORCID or authorize the relevant DOI provider integration when available. See `PUBLICATION.md` for the release checklist.

## Contributing

Issues and pull requests are welcome while the draft is under review. Please keep proposals scoped, include a concrete example, and explain how the change affects deterministic verification.

Specification text, profiles, examples, and documentation are licensed under CC BY 4.0. Code, schemas, keys, tests, and CI are licensed under Apache 2.0.

Security-sensitive reports should follow `SECURITY.md`.

## Independence Notice

This is personal, independent work by Jason Lovell. It is not authored, sponsored, endorsed, or reviewed by, and does not represent the views of, any employer, client, or affiliated organization.
