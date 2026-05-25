# Contributing

AAC v0.2-candidate.7 is a draft for review and implementation feedback.

## Feedback Wanted

- Verdict semantics and whether PASS/HOLD/FAIL are deterministic and usable.
- Profile rules, especially `runwright.skills.release` and `runwright.mcp.release`.
- Evidence binding, hashing, signing, and offline verification.
- Privacy posture for evidence references and external evidence vaults.
- Compatibility with audit workflows such as EU AI Act, ISO/IEC 42001, NIST AI RMF, SLSA, Sigstore, SPDX, and CycloneDX.

## How To Contribute

Open an issue or pull request with a clear description of the change and why it matters. Keep proposals scoped and include a concrete example when possible.

## Review And Merge Policy

The `main` branch is protected. Changes should land through pull requests after the required GitHub Actions checks pass: `test` and CodeQL `Analyze Python`.

Release tags are signed, treated as immutable, and superseded by new tags rather than rewritten.

## Developer Certificate of Origin

This project uses the Developer Certificate of Origin. By contributing, you certify that you have the right to submit the contribution under this repository's licenses.

Use `git commit -s` to add a `Signed-off-by` line to commits.

## Licenses

Specification text, profiles, examples, and documentation are contributed under CC BY 4.0. Code, schemas, keys, tests, and CI are contributed under Apache 2.0.
