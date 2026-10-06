"""BUILD-34 — catalog contract conformance against the LOCAL complete pin (PROD-16 follow-up).

The hermetic push-time half of the catalog contract check (the crossover suite in
locveil-commons stays the release-cadence deep gate). Voice consumes the bridge's catalog
REST API at runtime — `parse_catalog` reads `CatalogResponse`, the emitted canonical
commands' `request_body()` are `CanonicalActionRequest`/`RoomCanonicalRequest` wire bodies
— and until this pin existed, a bridge schema reshape only surfaced when the cross-suite
ran. Now it fails here, on every push, against `contracts/pins/catalog/` (the owner's FULL
tagged artifact set — a pin is always complete; usage never shapes it, contracts.md §2).

Re-pin: `make -C eval repin CONTRACT=catalog` — updates this pin AND the commons crossover
pin in one run at the same tag; they must never diverge.
"""
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

from locveil_voice.intents.device_commands import DeviceCommand, GroupScope, RoomGroupCommand
from locveil_voice.outputs.bridge import parse_catalog

PIN_DIR = Path(__file__).resolve().parents[2] / "contracts" / "pins" / "catalog"
GOLDEN = json.loads((PIN_DIR / "catalog.golden.json").read_text(encoding="utf-8"))
OPENAPI = json.loads((PIN_DIR / "openapi.json").read_text(encoding="utf-8"))
STAMP = json.loads((PIN_DIR / "STAMP.json").read_text(encoding="utf-8"))
PIN = json.loads((PIN_DIR / "PIN.json").read_text(encoding="utf-8"))


def _schema(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}", "components": OPENAPI["components"]}


# ------------------------------------------------------------------ pin coherence

def test_pin_matches_owner_stamp():
    assert PIN["tag"] == STAMP["tag"]
    assert PIN["bridge_commit"] == STAMP["bridge_commit"]
    assert PIN["catalog_version"] == STAMP["catalog_version"] == GOLDEN["version"]


# ------------------------------------------------------------------ client side (inbound)

def test_golden_is_a_catalog_response():
    """The pinned golden IS a CatalogResponse — the shape voice's fetcher receives."""
    jsonschema.validate(GOLDEN, _schema("CatalogResponse"))


def test_voice_client_parses_the_pinned_catalog():
    """`parse_catalog` (the ARCH-26 fetch path) accepts the pinned bytes end-to-end."""
    catalog = parse_catalog(GOLDEN)
    assert catalog is not None
    assert catalog.devices, "pinned golden parsed to an empty device set"
    assert catalog.rooms, "pinned golden parsed to an empty room set"


# ------------------------------------------------------------------ contract v1.11 ("Timing" + "Localization")

def _golden_capabilities():
    for d in GOLDEN["devices"]:
        for cap in d.get("capabilities") or ():
            yield d, cap


def test_schema_declares_the_v111_timing_fields():
    """The pinned schema carries the two optional timing fields (contract v1.11 "Timing"):
    `confirm_timeout_ms` on a capability, `max_duration_ms` on a value label."""
    schemas = OPENAPI["components"]["schemas"]
    assert "confirm_timeout_ms" in schemas["CatalogCapability"]["properties"]
    assert "max_duration_ms" in schemas["CatalogValueLabel"]["properties"]
    assert "confirm_timeout_ms" not in schemas["CatalogCapability"].get("required", [])
    assert "max_duration_ms" not in schemas["CatalogValueLabel"].get("required", [])


def test_parser_reads_confirm_timeout_ms_and_max_duration_ms():
    """The parser READS both timing fields — nothing published is dropped silently.
    Every golden capability's `confirm_timeout_ms` (present or absent) round-trips, and
    every scenario value's `max_duration_ms` (the `set(value)` table AND the `scenario`
    field, incl. its `none` entry) is on the parsed model."""
    catalog = parse_catalog(GOLDEN)
    published = {(d["id"], cap["name"]): cap.get("confirm_timeout_ms")
                 for d, cap in _golden_capabilities()}
    assert any(v is not None for v in published.values()), \
        "golden publishes no confirm_timeout_ms at all — the v1.11 tier-1 field is missing"
    for (device_id, cap_name), expected in published.items():
        device = catalog.device(device_id)
        assert device is not None
        cap = device.capability(cap_name)
        assert cap is not None
        assert cap.confirm_timeout_ms == expected, f"{device_id}.{cap_name}"

    seen_ceilings = 0
    for d, raw_cap in _golden_capabilities():
        cap = catalog.device(d["id"]).capability(raw_cap["name"])
        for raw_action in raw_cap.get("actions") or ():
            action = cap.action(raw_action["name"])
            for raw_param in raw_action.get("params") or ():
                param = action.param(raw_param["name"])
                for raw_value in raw_param.get("values") or ():
                    parsed = next(v for v in param.values if v.canonical == raw_value["canonical"])
                    assert parsed.max_duration_ms == raw_value.get("max_duration_ms")
                    assert parsed.labels == (raw_value.get("labels") or {})
                    seen_ceilings += parsed.max_duration_ms is not None
        for raw_field in raw_cap.get("fields") or ():
            field_spec = cap.field_spec(raw_field["name"])
            for raw_value in raw_field.get("values") or ():
                parsed = field_spec.value(raw_value["canonical"])
                assert parsed is not None, f"{d['id']}.{raw_cap['name']}.{raw_field['name']}: {raw_value['canonical']}"
                assert parsed.max_duration_ms == raw_value.get("max_duration_ms")
                seen_ceilings += parsed.max_duration_ms is not None
    assert seen_ceilings > 0, "golden publishes no max_duration_ms — the v1.11 tier-2 field is missing"


def test_by_value_select_entries_carry_labels():
    """Contract v1.11 "Localization": every `set(value)` entry of a selection capability
    carries `ru`+`en` labels — the nine by-value gaps (two IR inputs) are closed, so the
    resolver's value vocabulary is complete; only a `power` field's on/off pair is exempt."""
    for d, cap in _golden_capabilities():
        for action in cap.get("actions") or ():
            for param in action.get("params") or ():
                for value in param.get("values") or ():
                    labels = value.get("labels") or {}
                    assert labels.get("ru") and labels.get("en"), \
                        f"{d['id']}.{cap['name']}.{action['name']}({param['name']}): {value['canonical']}"


# ------------------------------------------------------------------ contract v1.12 ("Jobs")
# BUILD-59: the scenario-job surface the durable job follower (ARCH-69,
# docs/design/scenario_jobs_voice.md) is written against. The golden is byte-identical to
# v1.11.0 (no job data in it); the surface is openapi + guide only.

GUIDE = (PIN_DIR / "catalog-contract.md").read_text(encoding="utf-8")


def test_schema_honours_wait_false_on_the_scenario_capability():
    """`CanonicalActionRequest.wait` documents the 202-with-a-job behaviour (v1.12)."""
    wait = OPENAPI["components"]["schemas"]["CanonicalActionRequest"]["properties"]["wait"]
    assert "202" in wait["description"] and "v1.12" in wait["description"]


def test_schema_declares_the_job_operations_and_shapes():
    """The two `/scenario/jobs` operations + the record / accepted / event schemas exist."""
    assert "/scenario/jobs/{job_id}" in OPENAPI["paths"]
    assert "/scenario/jobs" in OPENAPI["paths"]
    get_job = OPENAPI["paths"]["/scenario/jobs/{job_id}"]["get"]["responses"]
    assert get_job["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/ScenarioJob")
    assert "404" in get_job, "GET /scenario/jobs/{id} must document the 404 job_unknown answer"
    schemas = OPENAPI["components"]["schemas"]
    for name in ("ScenarioJob", "ScenarioJobAccepted", "ScenarioJobStartedEvent",
                 "ScenarioPhaseEvent", "ScenarioStepEvent", "ScenarioSwitchedEvent",
                 "ScenarioShutdownEvent"):
        assert name in schemas, f"v1.12 schema {name} missing from the pinned openapi"
    # the terminal events carry what the follower speaks from
    for name in ("ScenarioSwitchedEvent", "ScenarioShutdownEvent"):
        props = schemas[name]["properties"]
        for field in ("job_id", "job_state", "failures", "duration_ms"):
            assert field in props, f"{name}.{field} missing"
    assert set(schemas["ScenarioJob"]["properties"]) >= {
        "job_id", "room_id", "kind", "target", "state", "max_duration_ms", "failures",
        "result_scenario", "duration_ms"}
    assert set(schemas["ScenarioJobAccepted"]["properties"]) >= {"job_id", "room_id", "kind",
                                                                 "target", "max_duration_ms"}


def test_schema_declares_job_in_progress_with_a_job_id():
    """`CanonicalErrorCode` gains `job_in_progress`; `CanonicalError` carries the running
    `job_id` the handler adopts (design §4.4)."""
    schemas = OPENAPI["components"]["schemas"]
    assert "job_in_progress" in schemas["CanonicalErrorCode"]["enum"]
    assert "job_id" in schemas["CanonicalError"]["properties"]


def test_guide_holds_the_jobs_section():
    """The owner's normative guide carries the v1.12 "Jobs" section the follower relies on."""
    assert "## Jobs (since contract v1.12)" in GUIDE
    for phrase in ("One job per room", "job_in_progress", "GET /scenario/jobs/{job_id}",
                   "job_unknown", "scenario_job_started"):
        assert phrase in GUIDE, f"Jobs section lacks {phrase!r}"


# ------------------------------------------------------------------ emit side (outbound)

def test_device_command_body_is_a_canonical_action_request():
    """What voice POSTs to /devices/{id}/canonical validates against the pinned schema —
    built from the golden's own first actionable capability, so the example stays real."""
    device = next(d for d in GOLDEN["devices"]
                  for cap in (d.get("capabilities") or [])
                  if cap.get("actions"))
    cap = next(c for c in device["capabilities"] if c.get("actions"))
    action = cap["actions"][0]
    cmd = DeviceCommand(device_id=device["id"], capability=cap["name"],
                        action=action["name"], params=None)
    jsonschema.validate(cmd.request_body(), _schema("CanonicalActionRequest"))


def test_room_group_command_body_is_a_room_canonical_request():
    """What voice POSTs to /rooms/{id}/canonical validates against the pinned schema."""
    room = GOLDEN["rooms"][0]
    cmd = RoomGroupCommand(room_id=room["id"], group="light", action="turn_on",
                           scope=GroupScope.AUTO)
    jsonschema.validate(cmd.request_body(), _schema("RoomCanonicalRequest"))
