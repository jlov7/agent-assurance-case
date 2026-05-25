# Security Posture

This note explains the repository-level security posture for reviewers who use automated supply-chain signals such as OpenSSF Scorecard.

## Current Controls

- `main` is protected.
- Required GitHub Actions checks must pass before protected-branch updates: verifier tests, release-fingerprint verification, CodeQL, and quality checks.
- Release tags are signed and treated as immutable.
- The published release has DOI-backed archival metadata.
- The release-fingerprint verifier checks the signed tag, release commit, signing key, DOI, and release-evidence consistency.
- The quality gate checks ruff, pyright, codespell, CFF metadata, shell scripts, local Markdown links, and public-artifact hygiene.
- ClusterFuzzLite PR fuzzing is configured for the reference verifier.
- Dependabot is enabled for GitHub Actions and Python requirements.
- GitHub private vulnerability reporting is enabled through `SECURITY.md`.

## Scorecard Interpretation

OpenSSF Scorecard is intentionally visible in the README. Its remaining findings should be read as follows.

### Maintained

Scorecard reports this while the repository is younger than 90 days. That is an age signal, not a hidden maintenance defect. The repository should not claim that this signal is resolved until Scorecard can evaluate sustained activity over time.

### Code-Review

Scorecard reports this because recent changes do not have independent human approvals. The repository uses protected pull requests and required checks, but it does not yet claim independent human code review.

The correct remediation is accepted review from another qualified human reviewer or a second maintainer. Bot reviews, AI reviews, and self-approval should not be described as resolving this risk.

### CII-Best-Practices

Scorecard reports this because the project is not yet registered in the OpenSSF Best Practices badge program. The repository should not display or imply a badge until the project has actually been registered and assessed by that program.

## Claims Not Made

This repository does not currently claim:

- OpenSSF Best Practices badge status;
- independent third-party security review;
- independent third-party specification review;
- production key-management coverage;
- legal compliance certification.

Those are external or organizational milestones, not properties the reference verifier can prove by itself.

## Reviewer Guidance

Treat green CI and signed release evidence as reproducibility evidence. Treat the unresolved Scorecard items above as explicit maturity boundaries. Reports that improve those boundaries are welcome in the public review thread or through the private security reporting path when appropriate.
