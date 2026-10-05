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

BUILD-57: the pinned `contract.ts` is also the file config-ui COMPILES against. The plugin
imports its contract types from `locveil-workbench/contract`; TypeScript resolves that
specifier through a `paths` mapping in `config-ui/tsconfig.json` to the pinned file, and no
`locveil-workbench` package is installed at all. The tests at the bottom hold that
arrangement in place from the configuration side — the mapping exists and points at the pin
and nowhere else, the dependency is gone from `package.json` and the lockfile, the type-check
runs on the mapped config, and every plugin import of the contract is type-only (erased at
build, so nothing needs the package at runtime either). The `frontend-health` CI job proves
the same from the compiler's side: it asks `tsc --listFilesOnly` which files were compiled.
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

_CONTRACT_PACKAGE = "locveil-workbench"
_CONTRACT_SPECIFIER = "locveil-workbench/contract"


def _load_jsonc(path: Path) -> dict:
    """tsconfig.json is JSON with comments and optional trailing commas. Strings are matched
    first so that a `/*` inside one (the `"@/*"` path key) is left alone."""
    token = re.compile(r'''"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*|,(?=\s*[}\]])''', re.DOTALL)
    text = token.sub(lambda m: m.group(0) if m.group(0).startswith('"') else "",
                     path.read_text(encoding="utf-8"))
    return json.loads(text)


TSCONFIG = _load_jsonc(_UI / "tsconfig.json")

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


# --- BUILD-57: the pinned contract.ts is what config-ui compiles against ---------------


def _tsconfig_path_target(specifier: str) -> Path:
    """Where config-ui's tsconfig sends `specifier` — exactly one target, no fallback."""
    options = TSCONFIG["compilerOptions"]
    targets = options.get("paths", {}).get(specifier)
    assert targets, f"config-ui/tsconfig.json has no `paths` entry for {specifier!r}"
    assert len(targets) == 1, f"{specifier!r} must map to ONE file, got {targets}"
    return (_UI / options.get("baseUrl", ".") / targets[0]).resolve()


def test_jsonc_loader_keeps_strings_and_drops_comments(tmp_path):
    sample = tmp_path / "tsconfig.json"
    sample.write_text(
        '{ /* block */ "paths": { "@/*": ["./src/*"], // line\n "a": ["b"], }, }',
        encoding="utf-8",
    )
    assert _load_jsonc(sample) == {"paths": {"@/*": ["./src/*"], "a": ["b"]}}


def test_contract_import_resolves_to_the_pinned_file():
    assert _tsconfig_path_target(_CONTRACT_SPECIFIER) == (_PIN_DIR / "contract.ts").resolve()
    # no second route: a wildcard or sibling key for the package would be a way around
    routes = [k for k in TSCONFIG["compilerOptions"]["paths"] if _CONTRACT_PACKAGE in k]
    assert routes == [_CONTRACT_SPECIFIER]
    # one tsconfig for the sources, nothing inherited — the mapping read here is the whole
    # story (tsconfig.node.json covers vite.config.ts only and must not name the package)
    assert "extends" not in TSCONFIG
    assert TSCONFIG["include"] == ["src"]
    assert _CONTRACT_PACKAGE not in (_UI / "tsconfig.node.json").read_text(encoding="utf-8")


def test_pinned_file_gets_react_types_from_config_ui_itself():
    """The pinned contract.ts imports React types and lives outside any node_modules.
    Without this entry the import would resolve from whatever sits above the repo on the
    machine at hand (or not at all — TS2307); with it, from config-ui's own declared types."""
    assert 'import type * as React from "react"' in (_PIN_DIR / "contract.ts").read_text(
        encoding="utf-8")
    assert _tsconfig_path_target("react") == (_UI / "node_modules" / "@types" / "react").resolve()
    assert "@types/react" in PACKAGE["devDependencies"]


def test_type_check_runs_on_the_mapped_tsconfig():
    """`tsc` with no `-p` reads config-ui/tsconfig.json — the file checked above. A script
    pointing the compiler at another project file would bypass the mapping."""
    assert PACKAGE["scripts"]["type-check"] == "tsc --noEmit"
    assert PACKAGE["scripts"]["build"].startswith("tsc && ")
    assert PACKAGE["scripts"]["check"].startswith("npm run type-check")


def test_no_dependency_on_the_live_contract_package():
    """The contract reaches config-ui as pinned bytes only. A `locveil-workbench` dependency
    (until BUILD-57 a `file:` link into the commons checkout) would put a second, unpinned
    copy of the types within the compiler's reach."""
    for section in ("dependencies", "devDependencies", "peerDependencies",
                    "optionalDependencies"):
        for name, spec in PACKAGE.get(section, {}).items():
            assert name != _CONTRACT_PACKAGE, f"{_CONTRACT_PACKAGE} is back in {section}"
            assert "packages/workbench" not in spec, f"{name} in {section} links to {spec}"
    lock = (_UI / "package-lock.json").read_text(encoding="utf-8")
    assert _CONTRACT_PACKAGE not in lock
    assert "packages/workbench" not in lock
    # nor a bundler alias that would resolve the specifier at build time
    assert _CONTRACT_PACKAGE not in VITE_CONFIG


def test_plugin_sources_import_only_types_and_only_from_the_contract_entry():
    """Every mention of the package in config-ui's sources is
    `import type … from 'locveil-workbench/contract'`. Type-only imports are erased by the
    build, which is why no installed package is needed; a value import, a deeper path, or a
    dynamic import would need one."""
    statement = re.compile(
        r"""\bimport\s+type\b[^;'"`]*?\bfrom\s*(['"])(?P<spec>[^'"]+)\1""", re.DOTALL)
    mention = re.compile(r"""(['"`])[^'"`\n]*locveil-workbench[^'"`\n]*\1""")
    total = 0
    for source in sorted((_UI / "src").rglob("*.ts*")):
        text = source.read_text(encoding="utf-8")
        typed = [m for m in statement.finditer(text) if _CONTRACT_PACKAGE in m.group("spec")]
        for m in typed:
            assert m.group("spec") == _CONTRACT_SPECIFIER, f"{source.name}: {m.group('spec')}"
        mentions = mention.findall(text)
        assert len(mentions) == len(typed), (
            f"{source.relative_to(_REPO_ROOT)}: a reference to {_CONTRACT_PACKAGE} that is not "
            f"`import type … from '{_CONTRACT_SPECIFIER}'`")
        assert "locveil-commons" not in text, f"{source.relative_to(_REPO_ROOT)} reaches into commons"
        total += len(typed)
    assert total > 0, "config-ui no longer imports the contract — this guard is vacuous"
