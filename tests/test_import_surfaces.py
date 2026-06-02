from __future__ import annotations


def test_thin_package_import_surfaces_do_not_raise() -> None:
    import keywharf.domain
    import keywharf.runtime
    import keywharf.services
    import keywharf.storage  # noqa: F401
