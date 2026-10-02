"""Confirm the installed package exposes a version."""

import mcp_vedanti


def test_package_imports() -> None:
    """The package import succeeds and __version__ is set."""
    assert mcp_vedanti.__version__
