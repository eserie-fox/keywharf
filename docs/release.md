# Release Docs

- [`CHANGELOG.md`](../CHANGELOG.md): canonical change ledger
- Latest prepared release note: [`1.0.6`](release-notes/1.0.6.md)
- Release note archive: [`docs/release-notes/`](release-notes/)

## Publishing

After the version and release notes are prepared, reviewed, and merged to `main`, the resulting
push builds and publishes the package to TestPyPI. Check that package, then create and push the
version tag:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

The `v*` tag push builds the package again and publishes it to PyPI. Manual workflow runs build
and publish to TestPyPI. Both indexes use Trusted Publishing through their matching GitHub
environments.
