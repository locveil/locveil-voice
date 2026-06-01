"""ARCH-5 — enforce the Hexagonal import contracts in the test suite.

Runs import-linter against the `[tool.importlinter]` contracts in pyproject.toml
and asserts every contract holds, so the directional rules established by
ARCH-1..4 (domain depends on nothing outward; config has no upward imports;
components don't import delivery; adapters don't import application; provider
categories are independent) cannot silently regress.

Also runnable directly from the repo root: ``lint-imports``.
"""

import pytest


def test_hexagon_import_contracts_hold():
    """Every contract in pyproject [tool.importlinter] must pass."""
    pytest.importorskip("importlinter")
    from importlinter.api import use_cases

    assert use_cases.lint_imports() is True, (
        "Hexagonal import contracts are broken — the architecture regressed.\n"
        "Run `lint-imports` from the repo root to see which contract(s) and the "
        "offending import chain(s)."
    )
