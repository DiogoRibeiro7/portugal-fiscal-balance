# Release and Zenodo Archiving

Use this checklist when publishing an archival release.

## Before Release

1. Run the full validation suite:

   ```bash
   poetry check
   poetry run ruff check .
   poetry run mypy src
   poetry run pytest
   ```

2. Rebuild the deterministic research outputs when source code or source data changed:

   ```bash
   make all
   ```

3. Confirm the metadata files are current:

   - `CITATION.cff` for GitHub citation display;
   - `.zenodo.json` for Zenodo's GitHub archive metadata;
   - `CHANGELOG.md` for release notes.

## Zenodo Setup

Zenodo must be enabled from the Zenodo account before the first DOI can be minted:

1. connect the GitHub account in Zenodo;
2. sync repositories;
3. enable `DiogoRibeiro7/portugal-fiscal-balance`;
4. publish a GitHub release.

Zenodo will archive the GitHub release and assign a DOI. After the first DOI exists, add the DOI badge to `README.md` and, if needed, add the concept DOI as a related identifier in `.zenodo.json`.

## Versioning

Use GitHub release tags for version-specific Zenodo records, for example:

```bash
git tag -a v0.2.0 -m "Portugal Fiscal Balance 0.2.0"
git push origin v0.2.0
```

Then create the GitHub release from the tag. Do not hard-code a release DOI before Zenodo has minted it.
