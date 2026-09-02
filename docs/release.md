# Release Docs

- [`CHANGELOG.md`](../CHANGELOG.md): canonical change ledger
- Latest prepared release note: [`1.0.6`](release-notes/1.0.6.md)
- Release note archive: [`docs/release-notes/`](release-notes/)

## Publishing

After the version and release notes are prepared, reviewed, and merged to `main`, publish a
normal GitHub Release for the intended version tag. Publishing the release triggers the package
workflow once.

The workflow calls the shared public build workflow to create one sdist and wheel artifact. A
project-local job then downloads that artifact and publishes it to PyPI through Trusted
Publishing, GitHub OIDC, and the `pypi` environment. It does not rebuild, use an API token, or
publish from tag pushes or manual dispatches.
