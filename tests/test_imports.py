"""Test package imports and module discovery across all 6 developer domains."""

import importlib
import pytest


MODULE_NAMES = [
    "src",
    "src.contracts",
    "src.preprocessing",
    "src.preprocessing.synthetic",
    "src.perception",
    "src.foveated_grid",
    "src.mapping",
    "src.integration",
    "src.visualization",
    "src.evaluation",
]


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_module_can_be_imported(module_name: str) -> None:
    """Ensure that every team module package can be cleanly imported."""
    module = importlib.import_module(module_name)
    assert module is not None, f"Failed to import {module_name}"


def test_package_version_defined() -> None:
    """Ensure root package exports a standard __version__ string."""
    import src

    assert hasattr(src, "__version__"), "src.__version__ must be defined"
    assert isinstance(src.__version__, str)
    assert len(src.__version__) > 0
