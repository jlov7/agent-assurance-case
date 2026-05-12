# Publication Checklist

This checklist is for publishing an Agent Assurance Case (AAC) draft candidate as a citable artifact.

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
7. Push the commit and wait for GitHub Actions to pass on that exact SHA.

## GitHub Release

Do not make the repository public, push a public tag, or publish a GitHub Release until the maintainer explicitly approves that exact publication action.

1. Create a new tag for the final checked commit. Do not move old candidate tags.
2. Create a GitHub Release from that tag.
3. Include concise release notes covering verifier semantics, schema changes, threat model, examples, and known draft limitations.
4. Confirm the schema URI and demo public key URL resolve from the public tag.

## Zenodo DOI

1. Connect the GitHub repository to Zenodo.
2. Archive the GitHub Release.
3. Copy the version DOI from Zenodo.
4. Add the DOI to `CITATION.cff`, README, and the GitHub Release notes.
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
