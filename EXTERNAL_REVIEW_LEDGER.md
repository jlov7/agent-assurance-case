# AAC External Review Ledger

This ledger records independent review signals for Agent Assurance Case (AAC). It is intentionally separate from local CI and release evidence.

## Current Target

- Release: `v0.2-candidate.7`
- Release commit: `689198d9c249a966a0abab6415ae8668efb512d9`
- DOI: <https://doi.org/10.5281/zenodo.20379393>
- Public review issue: <https://github.com/jlov7/agent-assurance-case/issues/2>

## Current External Review Status

No independent verifier implementation, cryptographic review, schema/profile review, or deployment review has been accepted into this repository yet.

| Date | Source | Review type | Target | Status | Evidence |
|---|---|---|---|---|---|
| none yet | none yet | none yet | none yet | no accepted external review | n/a |

This is not a negative result. It is the current claim boundary: AAC is signed, CI-green, DOI-archived, and open for public review; it is not yet independently validated.

This boundary is machine-checked against release evidence and reviewer-facing docs by [`scripts/validate_external_review_status.py`](scripts/validate_external_review_status.py).

## What Counts As Accepted External Review

An entry can be added here when it has:

- a public issue, pull request, paper, blog post, or implementation repository;
- an exact AAC release tag or commit under review;
- enough method detail for another reviewer to reproduce the result;
- a clear outcome, such as confirmation, defect, limitation, incompatible interpretation, or implementation divergence;
- maintainer disposition in a linked issue or pull request.

Ledger candidates should include a filled structured report based on
[`review-report-template.json`](review-report-template.json), validated with:

```bash
python verifier/validate_review_report.py path/to/review-report.json
```

The validator checks the report shape, release identity, populated reviewer and
reproduction fields, duplicate JSON members, duplicate finding IDs, claim
boundaries, public artifact presence for independent-review claims, and exact
vector output for parser/vector-focused reviews. A report that claims
independent review must not be marked security-sensitive. Passing validation
does not make the report true; it only makes the review easier to inspect
reproducibly.

Independent verifier/parser authors can use the
[implementation report issue form](https://github.com/jlov7/agent-assurance-case/issues/new?template=implementation-report.yml)
to submit vector output, implementation scope, divergences, and a structured
report for ledger consideration.

Private comments, social-media reactions, stars, and informal praise do not count as accepted external review.

## Local Evidence That Does Not Count As External Review

The following are useful release evidence, but they are self-validation:

- GitHub Actions on `main`;
- `./VERIFY-PUBLICATION-READY.sh`;
- bundled examples and test vectors;
- the signed GitHub release;
- the Zenodo DOI.

These artifacts make AAC reviewable. They do not replace independent review.
