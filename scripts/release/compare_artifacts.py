"""Compare repeat-build wheel bytes and normalized sdist contents."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import tarfile
import tempfile
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _one_artifact(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(
            f"{directory} must contain exactly one {pattern} artifact; found {len(matches)}"
        )
    return matches[0]


def _logical_root(extracted: Path) -> Path:
    children = list(extracted.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extracted


def _normalized_mode(path: Path, kind: str) -> str:
    if kind == "directory":
        return "0755"
    if kind == "symlink":
        return "0777"
    executable = bool(path.lstat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    return "0755" if executable else "0644"


def _normalized_manifest(archive: Path) -> tuple[tuple[str, str, str, str], ...]:
    with tempfile.TemporaryDirectory(prefix="release-sdist-") as temp_dir:
        destination = Path(temp_dir)
        with tarfile.open(archive, "r:*") as source:
            source.extractall(destination, filter="data")

        root = _logical_root(destination)
        entries: list[tuple[str, str, str, str]] = []
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                kind = "symlink"
                identity = os.readlink(path)
            elif path.is_dir():
                kind = "directory"
                identity = "-"
            elif path.is_file():
                kind = "file"
                identity = _sha256(path)
            else:
                raise SystemExit(f"unsupported sdist entry type: {relative}")
            entries.append((relative, kind, _normalized_mode(path, kind), identity))
        return tuple(entries)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("build_one", type=Path)
    parser.add_argument("build_two", type=Path)
    args = parser.parse_args()

    wheel_one = _one_artifact(args.build_one, "*.whl")
    wheel_two = _one_artifact(args.build_two, "*.whl")
    sdist_one = _one_artifact(args.build_one, "*.tar.gz")
    sdist_two = _one_artifact(args.build_two, "*.tar.gz")

    wheel_one_hash = _sha256(wheel_one)
    wheel_two_hash = _sha256(wheel_two)
    sdist_one_hash = _sha256(sdist_one)
    sdist_two_hash = _sha256(sdist_two)
    manifest_one = _normalized_manifest(sdist_one)
    manifest_two = _normalized_manifest(sdist_two)

    print(f"wheel_1_sha256={wheel_one_hash}")
    print(f"wheel_2_sha256={wheel_two_hash}")
    print(f"wheel_bytes_identical={'yes' if wheel_one_hash == wheel_two_hash else 'no'}")
    print(f"sdist_1_sha256={sdist_one_hash}")
    print(f"sdist_2_sha256={sdist_two_hash}")
    print(f"sdist_normalized_entries={len(manifest_one)}")
    print(f"sdist_normalized_equivalent={'yes' if manifest_one == manifest_two else 'no'}")

    if wheel_one.name != wheel_two.name or wheel_one_hash != wheel_two_hash:
        return 1
    if sdist_one.name != sdist_two.name or manifest_one != manifest_two:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
