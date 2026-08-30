# Release Docs

- [`CHANGELOG.md`](../CHANGELOG.md): canonical change ledger
- Latest prepared release note: [`1.0.6`](release-notes/1.0.6.md)
- Release note archive: [`docs/release-notes/`](release-notes/)

## Publication authority

Creation of a `v*` tag is the sole PyPI publication authority. Tag deletions and
tag moves do not build or publish. For a newly created tag, the GitHub workflow
checks tag/package-version equality, derives and validates `SOURCE_DATE_EPOCH`,
builds and validates once, records hashes, and uploads one artifact bundle. The
PyPI job downloads and hash-checks that bundle and publishes the exact files
without rebuilding. Main pushes and `workflow_dispatch` never publish to PyPI
or TestPyPI; manual dispatch is build-and-validate only.

Before tagging, perform two isolated `python -m build` runs with the same epoch
and run `python scripts/release/compare_artifacts.py <build-1-dist>
<build-2-dist>`. Wheel bytes must be identical. Extracted sdist paths,
contents, normalized modes, entry types, and symlink targets must be identical;
raw sdist hashes may differ only because of archive/gzip container metadata.
