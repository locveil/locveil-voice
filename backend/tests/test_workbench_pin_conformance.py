"""BUILD-53 — workbench pin conformance (contracts convention, layer 2).

config-ui is the Voice Workbench PLUGIN: it builds against the commons-owned plugin contract
(family `workbench` — `contract.ts` + the manifest-fragment and runtime-config JSON Schemas),
pinned at `contracts/pins/workbench/`. The build emits `dist/manifest.json`, the fragment the
shell reads to load the plugin; a fragment the shell's schema rejects is a plugin that
silently never mounts.

This test proves the fragment THIS repo emits validates against the PINNED schema — at the
fragment's SOURCE, hermetically (no build, no Node, no sibling checkout): the fragment is
assembled exactly the way `config-ui/vite.config.ts` assembles it, from
`config-ui/manifest.fragment.json` plus the `version` of `config-ui/package.json`. A textual
tripwire keeps that claim honest: the vite config must take every fragment field from the
source file and may not grow an inline literal the test cannot see.
"""
import json
import re
from pathlib import Path

import jsonschema

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PIN_DIR = _REPO_ROOT / "contracts" / "pins" / "workbench"
_UI = _REPO_ROOT / "config-ui"

PIN = json.loads((_PIN_DIR / "PIN.json").read_text(encoding="utf-8"))
STAMP = json.loads((_PIN_DIR / "STAMP.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((_PIN_DIR / "manifest-fragment.schema.json").read_text(encoding="utf-8"))
SOURCE = json.loads((_UI / "manifest.fragment.json").read_text(encoding="utf-8"))
PACKAGE = json.loads((_UI / "package.json").read_text(encoding="utf-8"))
VITE_CONFIG = (_UI / "vite.config.ts").read_text(encoding="utf-8")

# The singleton set the shell serves through its import map — the libraries a plugin must
# NOT bundle and must declare a peer major for (the pinned schema's `peers` description).
_SHELL_SINGLETONS = ("react", "react-dom", "react-router-dom", "locveil-ui-kit")


def _emitted_fragment() -> dict:
    """The fragment as vite.config.ts::emitManifestFragment writes it."""
    return {
        "id": SOURCE["id"],
        "version": PACKAGE["version"],
        "entry": SOURCE["entry"],
        "styles": SOURCE["styles"],
        "peers": SOURCE["peers"],
    }


def test_pin_is_the_stamped_family():
    assert PIN["contract"] == STAMP["contract"] == "workbench"
    assert PIN["owner_repo"] == STAMP["owner_repo"] == "locveil-commons"
    assert PIN["tag"] == STAMP["tag"]
    # the pin is the owner's whole enumerated set, flat
    assert {Path(a).name for a in STAMP["artifacts"]} <= set(PIN["files"])


def test_pinned_schema_is_a_valid_schema():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


def test_emitted_manifest_fragment_validates_against_the_pinned_schema():
    jsonschema.validate(_emitted_fragment(), SCHEMA,
                        cls=jsonschema.Draft202012Validator)


def test_schema_rejects_a_fragment_without_peers():
    # proves the validation above has teeth against this schema (required: peers)
    broken = {k: v for k, v in _emitted_fragment().items() if k != "peers"}
    assert not jsonschema.Draft202012Validator(SCHEMA).is_valid(broken)


def test_fragment_declares_a_peer_major_for_every_shell_singleton():
    missing = [name for name in _SHELL_SINGLETONS if name not in SOURCE["peers"]]
    assert not missing, f"no peer major declared for shell singleton(s): {missing}"


def test_vite_config_emits_the_fragment_from_its_source_file():
    """The tripwire: what this test validates is what the build emits only while the vite
    config takes every field from manifest.fragment.json (+ version from package.json)."""
    assert "from './manifest.fragment.json'" in VITE_CONFIG
    body = VITE_CONFIG[VITE_CONFIG.index("const fragment = {"):]
    body = body[:body.index("}") + 1]
    fields = dict(re.findall(r"(\w+):\s*([\w.]+),", body))
    assert fields == {
        "id": "fragmentSource.id",
        "version": "pkg.version",
        "entry": "fragmentSource.entry",
        "styles": "fragmentSource.styles",
        "peers": "fragmentSource.peers",
    }, f"vite.config.ts assembles the fragment differently than this test does: {fields}"
