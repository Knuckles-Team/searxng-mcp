"""Verify package initialization and version metadata."""

import importlib

import pytest

PKG_NAME = __name__.rsplit(".", 1)[0] if "." in __name__ else None


def _get_pkg_name():
    """Discover the importable package name from the project layout.

    Prefer the actual package directory (a sibling of ``tests`` that holds an
    ``__init__.py``) over the project directory name, which can differ from the
    package when running inside a git worktree (e.g. ``fix-env-drift``).
    """
    import pathlib

    test_dir = pathlib.Path(__file__).resolve().parent
    project_dir = test_dir.parent
    for child in sorted(project_dir.iterdir()):
        if (
            child.is_dir()
            and child.name not in {"tests", "test"}
            and not child.name.startswith(".")
            and (child / "__init__.py").exists()
        ):
            return child.name
    return project_dir.name.replace("-", "_")


@pytest.fixture
def pkg_name():
    return _get_pkg_name()


def test_package_importable(pkg_name):
    """Package should be importable."""
    mod = importlib.import_module(pkg_name)
    assert mod is not None


def test_version_exists(pkg_name):
    """Package should expose __version__."""
    mod = importlib.import_module(pkg_name)
    version = getattr(mod, "__version__", None)
    # Version may come from importlib.metadata instead
    if version is None:
        from importlib.metadata import version as get_version

        version = get_version(pkg_name.replace("_", "-"))
    assert version is not None, f"{pkg_name} has no __version__"


def test_version_format(pkg_name):
    """Version should follow semver-like format."""
    mod = importlib.import_module(pkg_name)
    version = getattr(mod, "__version__", None)
    if version is None:
        from importlib.metadata import version as get_version

        version = get_version(pkg_name.replace("_", "-"))
    parts = version.split(".")
    assert len(parts) >= 2, f"Version {version} should have at least major.minor"
