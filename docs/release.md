# Release Docs

- [`CHANGELOG.md`](../CHANGELOG.md): canonical change ledger
- Latest prepared release note: [`1.0.6`](release-notes/1.0.6.md)
- Release note archive: [`docs/release-notes/`](release-notes/)

## Publishing

After the version and release notes are prepared, reviewed, and merged to `main`, wait for normal
CI. Explicitly dispatch the `Publish Python package` workflow to build once and publish to
TestPyPI. Check that package, then create and push the version tag:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

A newly created `v*` tag builds once and publishes to PyPI. Pull requests and ordinary `main`
pushes run CI only, while manual workflow dispatch publishes to TestPyPI. Deleting a tag does not
build or publish. Both indexes use Trusted Publishing through their matching GitHub environments.
