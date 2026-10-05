"""DOC-12 — docs-manifest coherence (HK-6/PROD-17; the drift-guard pattern for docs).

`docs/manifest.json` is the machine-readable registry of every user-facing doc
(`../locveil-commons/process/user-docs.md` §4). This test makes it load-bearing in the
normal suite: a doc committed under a manifest root without a node fails (registration IS
the manifest edit), a node whose file vanished fails (removal is by tombstone or a filed
supersession), the floor classes can't silently empty, and the docs-verdict lines the DONE
ledger records must name real nodes.

The manifest is INSTANCE DATA (HK-13 / BUILD-52); the contract is the commons-owned schema,
family `docs-manifest-schema`, PINNED at `contracts/pins/docs-manifest-schema/`. This file is
that pin's conformance test: schema validation reads the pinned copy — fully hermetic, no
sibling checkout, never skipped.

Diagram rule: a node's path is the `.dot` source; the same-basename render is the same
unit — both must exist, and neither may exist without the node.
"""
import json
import re
from pathlib import Path

import jsonschema

_REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((_REPO_ROOT / "docs" / "manifest.json").read_text(encoding="utf-8"))
NODES = MANIFEST["nodes"]
_PIN_DIR = _REPO_ROOT / "contracts" / "pins" / "docs-manifest-schema"

FLOOR_CLASSES = ("front-door", "quickstart", "contributor")


def test_manifest_validates_against_pinned_schema():
    schema = json.loads((_PIN_DIR / "manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(MANIFEST, schema)


def test_schema_pin_is_the_stamped_family():
    pin = json.loads((_PIN_DIR / "PIN.json").read_text(encoding="utf-8"))
    stamp = json.loads((_PIN_DIR / "STAMP.json").read_text(encoding="utf-8"))
    assert pin["contract"] == stamp["contract"] == "docs-manifest-schema"
    assert pin["owner_repo"] == stamp["owner_repo"] == "locveil-commons"
    assert pin["tag"] == stamp["tag"]
    assert "manifest.schema.json" in pin["files"]


def test_surface_globs_match_real_files():
    """A surface is a trigger map (glob → "a doc covering this may be stale"); a glob that
    matches nothing triggers nothing. The whole map named pre-layout-move paths for three
    months unnoticed (BUILD-52)."""
    def _matches(pattern: str) -> bool:
        # pathlib's trailing `**` yields directories only — `dir/**` means "anything under dir"
        walk = pattern + "/*" if pattern.endswith("**") else pattern
        return any(p.is_file() for p in _REPO_ROOT.glob(walk))

    dead = [f"{surface}: {pattern}"
            for surface, patterns in MANIFEST["surfaces"].items()
            for pattern in patterns if not _matches(pattern)]
    assert not dead, f"manifest surface globs that match no file: {dead}"


def test_ids_and_paths_unique():
    ids = [n["id"] for n in NODES]
    paths = [n["path"] for n in NODES]
    assert len(ids) == len(set(ids)), "duplicate node ids"
    assert len(paths) == len(set(paths)), "duplicate node paths"


def test_node_paths_exist():
    missing = [n["id"] for n in NODES
               if n["status"] != "pending-gate" and not (_REPO_ROOT / n["path"]).is_file()]
    assert not missing, f"manifest nodes whose file is gone (tombstone or supersession required): {missing}"


def test_every_file_under_roots_has_a_node():
    registered = {n["path"] for n in NODES}
    unregistered = []
    for root in MANIFEST["roots"]:
        rp = _REPO_ROOT / root
        files = [rp] if rp.is_file() else sorted(p for p in rp.rglob("*") if p.is_file())
        for f in files:
            rel = f.relative_to(_REPO_ROOT).as_posix()
            if rel in registered:
                continue
            # a diagram render rides its .dot node
            if f.suffix != ".dot" and (f.with_suffix(".dot").relative_to(_REPO_ROOT).as_posix()
                                       in registered):
                continue
            unregistered.append(rel)
    assert not unregistered, (
        f"user-facing files without a manifest node (registration rides the causing task): {unregistered}")


def test_diagram_pairs_complete():
    for n in NODES:
        if n["class"] != "diagram":
            continue
        dot = _REPO_ROOT / n["path"]
        render = dot.with_suffix(".png")
        assert dot.is_file() and render.is_file(), (
            f"{n['id']}: .dot source and its render are one unit — both must exist")


def test_covers_reference_declared_surfaces():
    surfaces = set(MANIFEST["surfaces"])
    for n in NODES:
        unknown = set(n.get("covers", [])) - surfaces
        assert not unknown, f"{n['id']} covers undeclared surfaces {unknown}"


def test_floor_classes_stay_populated():
    for cls in FLOOR_CLASSES:
        assert any(n["class"] == cls for n in NODES), (
            f"floor: the last '{cls}' node left without a same-change replacement")


def test_done_ledger_verdict_node_ids_exist():
    ids = {n["id"] for n in NODES}
    done = (_REPO_ROOT / "docs" / "RELEASE_PLAN_DONE.md").read_text(encoding="utf-8")
    bad = []
    for m in re.finditer(r"^[ \t]*docs:[ \t]*([^\n]+)", done, re.MULTILINE):
        body = m.group(1).strip()
        if body.startswith("none"):
            continue  # explicit dismissal — nothing to resolve
        body = re.sub(r"\([^)]*\)", "", body)  # annotations like "(retro-verdict, …)"
        for ref in (x.strip().rstrip(".") for x in body.split(",")):
            if ref and ref not in ids:
                bad.append(ref)
    assert not bad, f"docs-verdict lines reference unknown manifest nodes: {bad}"


def test_canonical_pointers_resolve():
    """A `canonical` carve-out names the STAMP and the guard test that make the node a
    contract — both are repo-root-relative paths and must resolve to files (BUILD-47: the
    ws-protocol guard pointer named a pre-BUILD-36 `irene/tests/…` path for three months
    with every check green)."""
    rotted = []
    for n in NODES:
        for key in ("stamp", "guard"):
            pointer = n.get("canonical", {}).get(key)
            if pointer and not (_REPO_ROOT / pointer.split("::")[0]).is_file():
                rotted.append(f"{n['id']}.canonical.{key} -> {pointer}")
    assert not rotted, f"manifest canonical pointers that resolve to no file: {rotted}"
