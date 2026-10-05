"""BUILD-26 — the committed OpenAPI artifact must match what the code serves (ui-openapi contract).

`config-ui/openapi.json` is a repo-internal GENERATED contract (`../locveil-commons/
process/contracts.md` — same mechanics in-repo): config-ui's TypeScript types are generated
from the committed file (`npm run gen:api-types`), so a schema change that isn't re-dumped
leaves the editor type-checking against a stale view of the backend (REL-4 found four whole
config sections missing that way). This test rebuilds the schema exactly the way
`scripts/dump_openapi.py` does and fails on ANY drift.

On failure:  uv run python scripts/dump_openapi.py   (then `cd config-ui && npm run
gen:api-types` if the delta touches types), and commit the regenerated artifacts.
"""
import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="webapi extra required to build the schema")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMITTED = _REPO_ROOT / "config-ui" / "openapi.json"


def _load_dump_module():
    spec = importlib.util.spec_from_file_location(
        "dump_openapi", _REPO_ROOT / "scripts" / "dump_openapi.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_openapi_matches_served_schema():
    app, mounted = _load_dump_module().build_app()
    assert "main_router" in mounted, "main router failed to mount — schema build is broken"
    served = json.loads(json.dumps(app.openapi(), ensure_ascii=False))
    committed = json.loads(_COMMITTED.read_text(encoding="utf-8"))
    assert served == committed, (
        "config-ui/openapi.json drifted from the schema the backend serves — "
        "regenerate: uv run python scripts/dump_openapi.py (+ config-ui gen:api-types)")


def test_ui_openapi_stamp_declares_empty_artifacts_with_this_guard():
    """BUILD-50 (HK-13): a repo-internal GENERATED contract declares `artifacts: []` — legal
    only with a `guard` pointer that resolves. The pointer must name THIS drift test, and
    the informational `artifact`/`generator` pointers must name the real files."""
    stamp = json.loads(
        (_REPO_ROOT / "contracts" / "ui-openapi" / "STAMP.json").read_text(encoding="utf-8"))
    assert stamp["artifacts"] == []
    assert (_REPO_ROOT / stamp["guard"]).resolve() == Path(__file__).resolve()
    assert (_REPO_ROOT / stamp["artifact"]).resolve() == _COMMITTED.resolve()
    assert (_REPO_ROOT / stamp["generator"]).is_file()
    assert stamp["tag"] == f"ui-openapi-v{stamp['version']}"
    assert len(stamp["version"].split(".")) == 3, "STAMP version must be three-part"
