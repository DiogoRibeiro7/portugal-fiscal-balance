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

3. Rebuild both documents and verify they are still byte-reproducible:

   ```bash
   make docs-check
   ```

   This is a release gate rather than a CI gate. CI does not compile LaTeX: doing so
   required a full texlive install on every push, which is slow, depends on an apt
   mirror outside our control, and once hung for twenty-three minutes. The check itself
   is real — it hashes the committed PDFs, rebuilds from scratch and fails if either
   moved — so it is run here, where the compile was happening anyway.

4. Confirm the metadata files are current:

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
git tag -a v0.3.0 -m "Portugal Fiscal Balance 0.3.0"
git push origin v0.3.0
```

Then create the GitHub release from the tag. Do not hard-code a release DOI before Zenodo has minted it.
