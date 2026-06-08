#!/usr/bin/env python3
"""Build-time gate: forbid ``TYPE_CHECKING`` import guards in ``irene/`` (Invariant #9 / QUAL-32).

A ``if TYPE_CHECKING:`` block is a band-aid for an import cycle, and a cycle is an architecture smell —
dependencies must point inward (Invariant #3). Imports are honest: if a type is importable at runtime,
import it at module top and annotate with the real symbol. Hard third-party deps (e.g. ``pydantic``) are
never optional, so guarding their imports is pure ceremony.

This mirrors the hexagon's ``lint-imports`` gate: CI fails if a guard reappears. Detection is AST-based,
so comments/strings that merely mention TYPE_CHECKING (e.g. "no TYPE_CHECKING band-aid") are not flagged.

Usage:
    python scripts/check_no_type_checking.py
Exits non-zero (listing offenders) if any ``import TYPE_CHECKING`` or ``if TYPE_CHECKING:`` is found.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "irene"


def find_guards():
    """Return [(path, lineno, what)] for every real TYPE_CHECKING usage under irene/."""
    hits = []
    for py in sorted(PKG.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except SyntaxError as exc:
            hits.append((py, exc.lineno or 0, f"syntax error: {exc.msg}"))
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if any(alias.name == "TYPE_CHECKING" for alias in node.names):
                    hits.append((py, node.lineno, "imports TYPE_CHECKING"))
            elif isinstance(node, ast.If):
                test = node.test
                if (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or \
                   (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"):
                    hits.append((py, node.lineno, "`if TYPE_CHECKING:` guard"))
    return hits


def main() -> int:
    hits = find_guards()
    if hits:
        print("❌ TYPE_CHECKING import guards are forbidden (Invariant #9 / QUAL-32):")
        for path, line, what in hits:
            print(f"  {path.relative_to(ROOT)}:{line}  {what}")
        print(f"\n{len(hits)} occurrence(s). Hoist the import to module top, or break the import cycle "
              "(move the shared type to a lower layer / use a port) — don't hide it from the runtime.")
        return 1
    print("✅ No TYPE_CHECKING import guards in irene/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
