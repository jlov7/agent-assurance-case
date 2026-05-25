# Publication Checklist

This checklist is for publishing an Agent Assurance Case (AAC) draft candidate as a citable artifact.

## Current Repository State

This repository is already public. Future releases should preserve the current provenance bar:

- changes land through protected pull requests;
- required checks pass on the exact `main` SHA: `test`, CodeQL `Analyze Python`, `Verify AAC release fingerprint`, `Quality checks`, and `OpenSSF Scorecard`;
- release tags are signed annotated tags and are never moved;
- GitHub Releases are created as drafts from existing tags with `gh release create --verify-tag --draft`;
- release assets are generated from the signed tag checkout, attested with GitHub artifact attestations, attached before publication, and verified again after publication;
- DOI metadata is added only after Zenodo archives the GitHub Release.

## Preflight

1. Update the candidate version everywhere it appears.
2. Pin the schema `$id` and `SPEC.md` schema URI to the exact Git tag.
3. Regenerate bundled examples after any verifier, demo identity, schema, or profile change.
4. Review `THREAT_MODEL.md` for any changed trust-boundary assumptions.
5. Run:

   ```bash
   ./VERIFY-PUBLICATION-READY.sh
   uvx --from cffconvert cffconvert --validate --infile CITATION.cff
   ```

6. Commit the final artifact.
7. Push through a pull request and wait for the protected GitHub Actions checks to pass on the exact merged SHA.
8. Run the release-fingerprint verifier from current `main` after any release-fingerprint updates:

   ```bash
   python3 scripts/verify_release_fingerprints.py
   ```

## GitHub Release

Do not publish a GitHub Release until the maintainer explicitly approves that exact publication action.

1. Create a new tag for the final checked commit. Do not move old candidate tags.
2. Push the signed tag.
3. Create the GitHub Release draft from the existing tag, using `--verify-tag` so `gh` cannot create an unsigned tag implicitly.
4. Run `release-assets.yml` for the signed tag and confirm the attestation is visible with `gh attestation verify`.
5. Publish the release draft.
6. Include concise release notes covering verifier semantics, schema changes, threat model, examples, and known draft limitations.
7. Confirm the schema URI and demo public key URL resolve from the public tag.

Example:

```bash
git tag -s vX.Y-candidate.Z <release-commit-sha> -m "Agent Assurance Case vX.Y-candidate.Z"
git push origin vX.Y-candidate.Z
gh release create vX.Y-candidate.Z --verify-tag --draft --prerelease --title "Agent Assurance Case vX.Y-candidate.Z" --notes-file release-notes.md
gh workflow run release-assets.yml --repo jlov7/agent-assurance-case -f tag=vX.Y-candidate.Z
gh release edit vX.Y-candidate.Z --repo jlov7/agent-assurance-case --draft=false
```

## Zenodo DOI

1. Connect the GitHub repository to Zenodo.
2. Archive the GitHub Release.
3. Copy the version DOI from Zenodo.
4. Add the DOI to `CITATION.cff`, README, release-fingerprint docs, and the GitHub Release notes.
5. Commit the DOI metadata as a follow-up metadata commit.

## ORCID

1. Add the Zenodo DOI as a work item in ORCID.
2. Use the repository title from `CITATION.cff`.
3. Set the work type to software or technical standard, depending on ORCID's available options.
4. Use the version DOI for the specific release; use the concept DOI only when citing the project family.

## Public Positioning

- Call AAC a draft specification and reference verifier, not a legal compliance certification.
- Treat `aac.core` as the portable format.
- Treat `runwright.*` profiles as vendor examples, not as the standard itself.
- Do not claim v1.0 conformance before a stable release exists.
