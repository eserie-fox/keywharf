from __future__ import annotations


def test_thin_package_import_surfaces_do_not_raise() -> None:
    import keywharf.domain  # noqa: F401
    import keywharf.runtime  # noqa: F401
    import keywharf.services  # noqa: F401
    import keywharf.storage  # noqa: F401

