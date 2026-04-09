from __future__ import annotations


def test_thin_package_import_surfaces_do_not_raise() -> None:
    import ssh_manager.domain  # noqa: F401
    import ssh_manager.runtime  # noqa: F401
    import ssh_manager.services  # noqa: F401
    import ssh_manager.storage  # noqa: F401

