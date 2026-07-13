"""ARCH-5 — enforce the Hexagonal import contracts in the test suite.

Runs import-linter against the `[tool.importlinter]` contracts in pyproject.toml
and asserts every contract holds, so the directional rules established by
ARCH-1..4 (domain depends on nothing outward; config has no upward imports;
components don't import delivery; adapters don't import application; provider
categories are independent), ARCH-6/SCC-2 (the input port doesn't import its
adapters), and ARCH-11 (core depends only on its own ports, never outward on the
inputs/workflows/components layers) cannot silently regress.

Also runnable directly: ``lint-imports`` from the backend/ directory.
"""

from pathlib import Path

import pytest

# [tool.importlinter] lives in backend/pyproject.toml (src-layout, BUILD-36); point
# import-linter at it explicitly so the test passes regardless of the pytest cwd.
_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_hexagon_import_contracts_hold():
    """Every contract in backend/pyproject.toml [tool.importlinter] must pass."""
    pytest.importorskip("importlinter")
    from importlinter.api import use_cases

    assert use_cases.lint_imports(config_filename=str(_PYPROJECT)) is True, (
        "Hexagonal import contracts are broken — the architecture regressed.\n"
        "Run `lint-imports` from the backend/ directory to see which contract(s) "
        "and the offending import chain(s)."
    )
