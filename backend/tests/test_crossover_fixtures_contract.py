"""BUILD-60 — the owner guard of the `crossover-fixtures` contract (board PROD-29).

`contracts/crossover-fixtures/crossover_fixtures.json` is the single source of truth for
the Irene ↔ bridge crossover suite — `{utterance → expected canonical command}` — owned by
this repo and pinned by locveil-commons (and by the bridge once VWB-16 lands). The fixtures
are meaningful against exactly ONE bridge catalog, identified by the golden's content hash;
this repo holds that catalog as a pin (`contracts/pins/catalog/`), so the fixtures are a
pin-of-a-pin. This test makes the chain explicit and checks it on every push:

1. the document parses and its `catalog_version` binding equals the STAMP's `catalog_version`
   AND the catalog pin's (owner STAMP + PIN.json) AND the pinned golden's own `version`; the
   STAMP's `catalog_tag` is the pin's tag;
2. every fixture binds to entities that exist in the pinned golden — device ids, capabilities,
   actions, params (required / enum / range), context rooms, room groups, read fields,
   clarification candidates (the TEST-18 Slice A rules, now run by the owner);
3. the STAMP enumerates exactly the one artifact and names this test as its guard.

A catalog re-pin that moves the golden's hash fails (1) until the fixtures are re-bound and a
fixtures MINOR is cut — the accepted one-extra-hop cost (owner, 2026-10-12).
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OWNED = ROOT / "contracts" / "crossover-fixtures"
CATALOG_PIN = ROOT / "contracts" / "pins" / "catalog"

FIXTURES_PATH = OWNED / "crossover_fixtures.json"
STAMP = json.loads((OWNED / "STAMP.json").read_text(encoding="utf-8"))
CATALOG_STAMP = json.loads((CATALOG_PIN / "STAMP.json").read_text(encoding="utf-8"))
CATALOG_PIN_META = json.loads((CATALOG_PIN / "PIN.json").read_text(encoding="utf-8"))
GOLDEN = json.loads((CATALOG_PIN / "catalog.golden.json").read_text(encoding="utf-8"))

EXPECT_KINDS = {"actuate", "room-group", "read", "clarify"}
FANOUT_ALLOW_LIST = {"light", "cover"}  # the bridge allow-lists fan-out to these groups (VWB-23)
SCOPES = {"auto", "all", "one"}


@pytest.fixture(scope="module")
def fixtures_doc() -> dict:
    return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fixtures(fixtures_doc) -> list[dict]:
    return fixtures_doc["fixtures"]


@pytest.fixture(scope="module")
def devices() -> dict[str, dict]:
    return {d["id"]: d for d in GOLDEN["devices"]}


@pytest.fixture(scope="module")
def rooms() -> dict[str, dict]:
    return {r["id"]: r for r in GOLDEN["rooms"]}


def _capability(device: dict, name: str) -> dict | None:
    for cap in device.get("capabilities") or []:
        if cap["name"] == name:
            return cap
    return None


def _action(cap: dict, name: str) -> dict | None:
    for act in cap.get("actions") or []:
        if act["name"] == name:
            return act
    return None


# ------------------------------------------------------------------ (1) the binding chain


def test_stamp_core_and_family():
    assert STAMP["contract"] == "crossover-fixtures"
    assert STAMP["owner_repo"] == "locveil-voice"
    assert STAMP["tag"] == f"crossover-fixtures-v{STAMP['version']}"
    assert len(STAMP["version"].split(".")) == 3, "three-level version (contracts.md §3)"


def test_fixtures_bind_to_the_stamped_catalog(fixtures_doc):
    """The document's binding == the STAMP's == the catalog pin's == the golden's own hash."""
    binding = fixtures_doc["catalog_version"]
    assert binding == STAMP["catalog_version"], (
        "fixtures were authored against a different catalog than the STAMP records — "
        "re-bind and cut a fixtures minor"
    )
    assert STAMP["catalog_version"] == CATALOG_STAMP["catalog_version"] == CATALOG_PIN_META["catalog_version"], (
        "the catalog pin moved under the fixtures — re-author where the binding tests below "
        "point, then re-bind catalog_version/catalog_tag and cut a fixtures minor (the accepted cost)"
    )
    assert binding == GOLDEN["version"], "the pinned golden's own version is the hash the fixtures bind to"


def test_stamp_catalog_tag_is_the_pinned_tag():
    assert STAMP["catalog_tag"] == CATALOG_STAMP["tag"] == CATALOG_PIN_META["tag"]


# ------------------------------------------------------------------ (3) the enumerated set


def test_stamp_enumerates_exactly_the_fixtures_file():
    assert STAMP["artifacts"] == ["contracts/crossover-fixtures/crossover_fixtures.json"]
    assert (ROOT / STAMP["artifacts"][0]) == FIXTURES_PATH
    assert FIXTURES_PATH.is_file()


def test_stamp_guard_is_this_test():
    assert STAMP["guard"] == "backend/tests/test_crossover_fixtures_contract.py"
    assert (ROOT / STAMP["guard"]).resolve() == Path(__file__).resolve()


def test_owned_folder_holds_only_the_contract_files():
    """README + STAMP + the enumerated artifact — nothing a consumer's pin would not carry."""
    names = sorted(p.name for p in OWNED.iterdir())
    assert names == ["README.md", "STAMP.json", "crossover_fixtures.json"]


# ------------------------------------------------------------------ (2) shape + bindings


def test_document_shape(fixtures_doc, fixtures):
    assert set(fixtures_doc["expect_kinds"]) == EXPECT_KINDS, "a kind change is a MAJOR cut"
    assert set(fixtures_doc["tiers"]) == {"1", "2"}
    ids = [f["id"] for f in fixtures]
    assert len(ids) == len(set(ids)), "duplicate fixture ids"
    for f in fixtures:
        assert f["tier"] in (1, 2), f["id"]
        assert f["utterance"]["ru"].strip(), f["id"]
        assert f["expect"]["kind"] in EXPECT_KINDS, f["id"]


def test_all_expect_kinds_covered(fixtures):
    assert {f["expect"]["kind"] for f in fixtures} == EXPECT_KINDS


def test_context_rooms_exist(fixtures, rooms):
    for f in fixtures:
        room = (f.get("context") or {}).get("room")
        if room is not None:
            assert room in rooms, f"{f['id']}: unknown context room {room}"


def _validate_params(fid: str, action: dict, params: dict | None) -> None:
    specs = {p["name"]: p for p in action.get("params") or []}
    for name, spec in specs.items():
        if spec.get("required"):
            assert params and name in params, f"{fid}: required param {name} missing"
    if not params:
        return
    for name, value in params.items():
        assert name in specs, f"{fid}: param {name} not in the contract"
        spec = specs[name]
        if spec.get("values"):
            # voice sends the CANONICAL token; the bridge maps canonical → wire
            allowed = {v["canonical"] for v in spec["values"]}
            assert value in allowed, f"{fid}: enum value {value!r} not in {sorted(allowed)}"
        else:
            if spec.get("min") is not None:
                assert value >= spec["min"], f"{fid}: {name}={value} below min {spec['min']}"
            if spec.get("max") is not None:
                assert value <= spec["max"], f"{fid}: {name}={value} above max {spec['max']}"


def test_actuate_fixtures_bind(fixtures, devices):
    for f in fixtures:
        e = f["expect"]
        if e["kind"] != "actuate":
            continue
        assert e["device_id"] in devices, f"{f['id']}: unknown device {e['device_id']}"
        cap = _capability(devices[e["device_id"]], e["capability"])
        assert cap, f"{f['id']}: {e['device_id']} has no capability {e['capability']}"
        action = _action(cap, e["action"])
        assert action, f"{f['id']}: no action {e['capability']}.{e['action']} on {e['device_id']}"
        _validate_params(f["id"], action, e.get("params"))


def test_room_group_fixtures_bind(fixtures, rooms, devices):
    for f in fixtures:
        e = f["expect"]
        if e["kind"] != "room-group":
            continue
        fid = f["id"]
        assert e["room_id"] in rooms, f"{fid}: unknown room {e['room_id']}"
        assert e["group"] in FANOUT_ALLOW_LIST, f"{fid}: group {e['group']} outside the allow-list"
        assert e["scope"] in SCOPES, fid
        member_actions: set[str] = set()
        for d in devices.values():
            if d["room"] != e["room_id"]:
                continue
            for cap in d.get("capabilities") or []:
                if cap.get("group") == e["group"]:
                    member_actions.update(a["name"] for a in cap.get("actions") or [])
        assert member_actions, f"{fid}: room {e['room_id']} has no {e['group']}-group members"
        assert e["action"] in member_actions, (
            f"{fid}: action {e['action']} not offered by any {e['group']} member "
            f"of {e['room_id']} (has: {sorted(member_actions)})"
        )


def _validate_read_target(fid: str, devices: dict, target: dict) -> None:
    assert target["device_id"] in devices, f"{fid}: unknown device {target['device_id']}"
    cap = _capability(devices[target["device_id"]], target["capability"])
    assert cap, f"{fid}: {target['device_id']} has no capability {target['capability']}"
    fields = {fld["name"] for fld in cap.get("fields") or []}
    assert target["field"] in fields, (
        f"{fid}: field {target['field']} not on {target['device_id']}.{target['capability']} "
        f"(has: {sorted(fields)})"
    )


def test_read_fixtures_bind(fixtures, devices):
    for f in fixtures:
        e = f["expect"]
        if e["kind"] != "read":
            continue
        targets = e["any_of"] if "any_of" in e else [e]
        assert targets, f["id"]
        for target in targets:
            _validate_read_target(f["id"], devices, target)


def test_clarify_fixtures_bind(fixtures, devices):
    for f in fixtures:
        e = f["expect"]
        if e["kind"] != "clarify":
            continue
        fid = f["id"]
        assert len(e["candidates"]) >= 2, f"{fid}: a clarification needs >=2 candidates"
        wanted = e["capability"] if isinstance(e["capability"], list) else [e["capability"]]
        for dev_id in e["candidates"]:
            assert dev_id in devices, f"{fid}: unknown candidate {dev_id}"
            assert any(_capability(devices[dev_id], c) for c in wanted), (
                f"{fid}: candidate {dev_id} lacks all of {wanted} — the ambiguity would not arise"
            )
        candidate_rooms = {devices[d]["room"] for d in e["candidates"]}
        assert len(candidate_rooms) == 1, f"{fid}: candidates span rooms {candidate_rooms}"
