"""Gate: ``irene/`` must stay free of ``TYPE_CHECKING`` import guards (Invariant #9 / QUAL-32).

Mirrors ``test_import_contracts.py`` for the hexagon: the standalone checker
(``scripts/check_no_type_checking.py``) is the source of truth, run both as a CI step and here so the
suite fails too if a guard reappears.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_no_type_checking_guards():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_no_type_checking.py")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
