# AAC External Review Ledger

This ledger records independent review signals for Agent Assurance Case (AAC). It is intentionally separate from local CI and release evidence.

## Current Target

- Release: `v0.2-candidate.7`
- Release commit: the Git tag target for `v0.2-candidate.7`
- DOI: <https://doi.org/10.5281/zenodo.20379393>
- Public review issue: <https://github.com/jlov7/agent-assurance-case/issues/2>

## Current External Review Status

No independent verifier implementation, cryptographic review, schema/profile review, or deployment review has been accepted into this repository yet.

| Date | Source | Review type | Target | Status | Evidence |
|---|---|---|---|---|---|
| none yet | none yet | none yet | none yet | no accepted external review | n/a |

This is not a negative result. It is the current claim boundary: AAC is signed, CI-green, DOI-archived, and open for public review; it is not yet independently validated.

## What Counts As Accepted External Review

An entry can be added here when it has:

- a public issue, pull request, paper, blog post, or implementation repository;
- an exact AAC release tag or commit under review;
- enough method detail for another reviewer to reproduce the result;
- a clear outcome, such as confirmation, defect, limitation, incompatible interpretation, or implementation divergence;
- maintainer disposition in a linked issue or pull request.

Private comments, social-media reactions, stars, and informal praise do not count as accepted external review.

## Local Evidence That Does Not Count As External Review

The following are useful release evidence, but they are self-validation:

- GitHub Actions on `main`;
- `./VERIFY-PUBLICATION-READY.sh`;
- bundled examples and test vectors;
- the signed GitHub release;
- the Zenodo DOI.

These artifacts make AAC reviewable. They do not replace independent review.
