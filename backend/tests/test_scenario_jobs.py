"""ARCH-69 — the durable scenario job + the bridge SSE adapter (PROD-18 tier 3, voice side).

Design: `docs/design/scenario_jobs_voice.md` §7 — the nine test groups. Shapes are the bridge's
`scenario_jobs.md` §5 verbatim (contract v1.12 "Jobs"); the follower is driven by a fake events
port scripted per state-machine row (§5 table), the adapter's reader by byte lines.
"""

import asyncio
import json
import logging
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import aiohttp
import pytest

from locveil_voice.core.catalog_service import CatalogService
from locveil_voice.core.client_registry import ClientRegistry
from locveil_voice.core.device_command_dispatcher import DeviceCommandDispatcher
from locveil_voice.core.durable_actions import (
    DurableActionRecord,
    JsonFileDurableActionStore,
    reconcile_durable_actions,
    set_durable_action_store,
)
from locveil_voice.core.interfaces.output import DeliveryResult, OutputModality
from locveil_voice.core.notifications import NotificationService
from locveil_voice.intents.context_models import UnifiedConversationContext
from locveil_voice.intents.device_commands import DeviceCommand
from locveil_voice.intents.handlers.smart_home import (
    SCENARIO_JOB_METADATA_KEY,
    SmartHomeIntentHandler,
)
from locveil_voice.intents.models import Intent
from locveil_voice.intents.ports import ScenarioJobEventsPort
from locveil_voice.intents.scenario_jobs import (
    JobEvent,
    JobEventKind,
    JobFailure,
    JobLookupMiss,
    JobRecord,
    ceiling_bucket,
    hard_cap_seconds,
    remaining_seconds,
    watchdog_seconds,
)
from locveil_voice.outputs.bridge import BridgeClient
from locveil_voice.outputs.bridge_events import (
    BridgeEventsClient,
    backoff_seconds,
    parse_job_event,
    parse_job_record,
    read_sse_frames,
)
from locveil_voice.outputs.console import ConsoleOutput
from locveil_voice.outputs.device_command import OUTPUT_TYPE, CapturingDeviceCommandOutput
from locveil_voice.outputs.manager import OutputManager

import importlib.util
import sys

# the house slice + the smart_home donation loader of the handler suite (no tests package)
_spec = importlib.util.spec_from_file_location(
    "test_smart_home_handler", Path(__file__).with_name("test_smart_home_handler.py"))
_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("test_smart_home_handler", _mod)
_spec.loader.exec_module(_mod)
CATALOG_PAYLOAD = _mod.CATALOG_PAYLOAD
loader = _mod.loader  # noqa: F811 — the module-scoped fixture, re-exported for this module

JOB = "j-living_room-20261006T162958Z-c2a1"
ROOM = "living_room"

# --- the bridge's shapes, verbatim (scenario_jobs.md §5.1 / §5.4) ---------------------------------

ACCEPTED_202 = (202, {"success": True, "device_id": "scenario_manager", "capability": "scenario",
                      "action": "set", "executed_on": None, "skipped_reason": None,
                      "state": {"scenario": "none", "job_id": JOB, "max_duration_ms": 55500},
                      "error": None, "no_op": False})
BUSY_409 = (409, {"detail": {"success": False, "device_id": "scenario_manager",
                             "capability": "scenario", "action": "set", "state": None,
                             "error": {"code": "job_in_progress",
                                       "message": "a scenario job is running in room 'living_room'",
                                       "job_id": JOB}}})
SYNC_200 = (200, {"success": True, "device_id": "scenario_manager", "capability": "scenario",
                  "action": "set", "state": {"scenario": "movie_vhs", "job_id": JOB,
                                             "powered_off": [], "failures": []},
                  "error": None, "no_op": False})

SWITCHED_OK = {"eventType": "scenario_switched", "scenario_id": "movie_vhs", "room_id": ROOM,
               "timestamp": "2026-10-06T15:31:53.795Z", "state": {"scenario_id": "movie_vhs"},
               "job_id": JOB, "job_state": "succeeded", "duration_ms": 41377, "failures": [],
               "powered_off": ["streamer"]}
SWITCHED_FAILED = dict(SWITCHED_OK, job_state="failed",
                       failures=[{"device": "mf_amplifier", "command": "set_input",
                                  "error": "gate timeout: input did not reach 'source1'"}])
STEP_DONE = {"eventType": "scenario_step", "job_id": JOB, "room_id": ROOM, "phase": "teardown",
             "index": 0, "device_id": "streamer", "domain": "power", "target": False,
             "command": "power_off", "zone": None, "status": "done", "error": None,
             "elapsed_ms": 3410, "timestamp": "…"}


def _record(state="running", failures=(), **kw) -> JobRecord:
    base = dict(job_id=JOB, room_id=ROOM, kind="switch", target="movie_vhs", state=state,
                max_duration_ms=55500, failures=tuple(failures), result_scenario=None,
                duration_ms=None)
    base.update(kw)
    return JobRecord(**base)


# ==================================================================================================
# 1. the delivery seam: 202 / 409 / 200-on-wait:false / the wire body
# ==================================================================================================

def test_request_body_carries_wait_only_when_false():
    cmd = DeviceCommand(device_id="scenario_manager", capability="scenario", action="set",
                        params={"value": "movie_vhs"})
    assert "wait" not in cmd.request_body()
    assert "wait" not in DeviceCommand(device_id="x", capability="power", action="on",
                                       wait=True).request_body()
    job = DeviceCommand(device_id="scenario_manager", capability="scenario", action="set",
                        params={"value": "movie_vhs"}, wait=False)
    assert job.request_body()["wait"] is False
    # the fixture/capture shape and the identity never see it
    assert "wait" not in job.to_dict() and job == cmd


def test_202_is_accepted_never_delivered():
    dr = BridgeClient._to_delivery_result(None, *ACCEPTED_202)
    assert dr.accepted and not dr.delivered and dr.error_code is None
    assert dr.job_id == JOB and dr.max_duration_ms == 55500
    assert dr.echoed_value["scenario"] == "none"      # the room AT acceptance


def test_409_job_in_progress_carries_the_running_job():
    dr = BridgeClient._to_delivery_result(None, *BUSY_409)
    assert not dr.delivered and not dr.accepted
    assert dr.error_code == "job_in_progress" and dr.job_id == JOB


def test_200_on_a_wait_false_request_is_the_sync_outcome():
    """A bridge that ignores `wait` (the commons mock bridge, pre-1.12) ran the chain: today's
    mapping, so the ARCH-67 confirmation is spoken."""
    dr = BridgeClient._to_delivery_result(None, *SYNC_200)
    assert dr.delivered and not dr.accepted and dr.job_id is None


def test_other_errors_carry_no_job_id():
    dr = BridgeClient._to_delivery_result(None, 404, {"success": False, "error": {
        "code": "device_not_found", "message": "no", "job_id": "stray"}})
    assert dr.error_code == "device_not_found" and dr.job_id is None


# ==================================================================================================
# 2. the SSE adapter: reader, parsing, backoff, STREAM_OPEN, queue overflow, the GETs
# ==================================================================================================

async def _lines(*chunks: bytes):
    for c in chunks:
        yield c


async def test_sse_reader_drops_housekeeping_and_parses_job_frames():
    frames = [f for f in [
        b"id: 1759764672418\n",
        b'data: {"eventType":"connected","message":"Connected to scenarios channel","timestamp":"2026-10-06T18:31:12.418532"}\n',
        b"\n",
        b'data: {"eventType":"keepalive","timestamp":"2026-10-06T18:31:13.419104"}\n',
        b"\n",
        b": a comment\n",
        b"id: 2\n",
        b"data: " + json.dumps(STEP_DONE).encode() + b"\n",
        b"\n",
        b"data: " + json.dumps(SWITCHED_OK).encode() + b"\n",   # trailing frame, no blank line
    ]]
    payloads = [p async for p in read_sse_frames(_lines(*frames))]
    assert [p["eventType"] for p in payloads] == ["connected", "keepalive", "scenario_step",
                                                  "scenario_switched"]
    events = [parse_job_event(p) for p in payloads]
    assert events[0] is None and events[1] is None
    assert events[2].kind is JobEventKind.STEP and events[2].job_id == JOB
    assert events[3].kind is JobEventKind.TERMINAL and events[3].job_state == "succeeded"
    assert events[3].result_scenario == "movie_vhs" and events[3].duration_ms == 41377


def test_parse_terminal_failures_and_the_restore_notification():
    ev = parse_job_event(SWITCHED_FAILED)
    assert ev.failures == (JobFailure(device="mf_amplifier", command="set_input",
                                      error="gate timeout: input did not reach 'source1'"),)
    # the startup restore's tracking notification has no job_id → dropped
    assert parse_job_event({"eventType": "scenario_switched", "scenario_id": "x",
                            "room_id": ROOM, "timestamp": "…"}) is None
    shutdown = parse_job_event({"eventType": "scenario_shutdown", "room_id": ROOM,
                                "job_id": JOB, "job_state": "succeeded", "failures": None})
    assert shutdown.result_scenario == "none"
    assert parse_job_event({"eventType": "something_new", "job_id": JOB}) is None


def test_parse_job_record_reads_the_section_3_record():
    rec = parse_job_record({"job_id": JOB, "room_id": ROOM, "kind": "switch",
                            "target": "movie_vhs", "from": "none", "source": "canonical",
                            "state": "failed", "max_duration_ms": 55500,
                            "started_at": "…", "finished_at": "…", "duration_ms": 41377,
                            "phases": [], "failures": [{"device": "processor",
                                                        "command": "set_input", "error": "x"}],
                            "powered_off": [], "result_scenario": "movie_vhs"})
    assert rec.terminal and rec.failures[0].device == "processor"
    assert rec.result_scenario == "movie_vhs" and rec.duration_ms == 41377


def test_backoff_is_1_2_4_8_16_30_with_bounded_jitter():
    rng = random.Random(7)
    for attempt, base in enumerate((1, 2, 4, 8, 16, 30, 30, 30)):
        for _ in range(20):
            got = backoff_seconds(attempt, rng)
            assert base * 0.75 <= got <= base * 1.25


class _StubRequests:
    def __init__(self, *responses):
        self.calls: List[tuple] = []
        self._responses = list(responses)

    async def __call__(self, method, path, body=None, timeout_seconds=None):
        self.calls.append((method, path))
        r = self._responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


async def test_adapter_fans_out_by_room_and_emits_stream_open_per_connect():
    client = BridgeEventsClient("http://bridge", _StubRequests())
    received: List[JobEvent] = []

    async def consume():
        async for ev in client.events(ROOM):
            received.append(ev)
            if ev.kind is JobEventKind.TERMINAL:
                break

    task = asyncio.create_task(consume())
    await asyncio.sleep(0)
    client._on_connected()                       # connect #1
    client._dispatch(STEP_DONE)
    client._dispatch(dict(STEP_DONE, room_id="bedroom"))   # another room: filtered
    client._dispatch({"eventType": "keepalive"})
    client._on_connected()                       # reconnect
    client._dispatch(SWITCHED_OK)
    await asyncio.wait_for(task, 2)
    assert [e.kind for e in received] == [JobEventKind.STREAM_OPEN, JobEventKind.STEP,
                                          JobEventKind.STREAM_OPEN, JobEventKind.TERMINAL]
    assert client._queues == []                  # unsubscribed on exit


async def test_adapter_subscriber_joining_an_open_stream_starts_with_a_get_cue():
    client = BridgeEventsClient("http://bridge", _StubRequests())
    client._on_connected()
    agen = client.events(ROOM)
    first = await asyncio.wait_for(agen.__anext__(), 1)
    assert first.kind is JobEventKind.STREAM_OPEN
    await agen.aclose()


def test_adapter_queue_overflow_drops_oldest_and_resyncs():
    queue: asyncio.Queue = asyncio.Queue(maxsize=4)
    step = parse_job_event(STEP_DONE)
    for _ in range(4):
        BridgeEventsClient._put(queue, step)
    BridgeEventsClient._put(queue, step)             # full → drop oldest, STREAM_OPEN, then it
    kinds = []
    while not queue.empty():
        kinds.append(queue.get_nowait().kind)
    # the oldest went, the re-sync cue took its place; the overflowing event itself is dropped
    # (the follower's GET after STREAM_OPEN reads the record instead)
    assert kinds[-1] is JobEventKind.STREAM_OPEN and len(kinds) == 4


async def test_adapter_reconnects_with_backoff_on_dead_stream(monkeypatch):
    opened = []
    sleeps = []

    async def fake_open(self):
        opened.append(1)
        self._on_connected()
        if len(opened) == 1:
            raise asyncio.TimeoutError()        # sock_read 5 s: no frame = dead stream
        yield SWITCHED_OK
        raise aiohttp.ClientConnectionError("gone")

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) >= 2:
            raise asyncio.CancelledError()

    monkeypatch.setattr(BridgeEventsClient, "_open", fake_open)
    monkeypatch.setattr("locveil_voice.outputs.bridge_events.asyncio.sleep", fake_sleep)
    client = BridgeEventsClient("http://bridge", _StubRequests())
    with pytest.raises(asyncio.CancelledError):
        await client._run()
    assert len(opened) == 2 and not client.connected
    assert 0.75 <= sleeps[0] <= 1.25             # attempt 0 after the dead stream
    assert 0.75 <= sleeps[1] <= 1.25             # a frame arrived in between → reset to 1 s


async def test_adapter_get_job_maps_200_404_and_transport():
    stub = _StubRequests(
        (200, {"job_id": JOB, "room_id": ROOM, "kind": "switch", "target": "movie_vhs",
               "state": "running", "max_duration_ms": 55500}),
        (404, {"detail": {"code": "job_unknown", "job_id": JOB}}),
        aiohttp.ClientConnectionError("refused"),
        (500, {"detail": "boom"}))
    client = BridgeEventsClient("http://bridge", stub)
    rec = await client.get_job(JOB)
    assert isinstance(rec, JobRecord) and rec.state == "running"
    assert (await client.get_job(JOB)) == JobLookupMiss("unknown")
    assert (await client.get_job(JOB)) == JobLookupMiss("unreachable")
    assert (await client.get_job(JOB)) == JobLookupMiss("unreachable")
    assert stub.calls[0] == ("GET", f"/scenario/jobs/{JOB}")


async def test_adapter_get_active_scenario_maps_state():
    stub = _StubRequests((200, {"scenario_id": "movie_vhs", "devices": {}, "manual_steps": []}),
                         (404, {"detail": "No active scenario"}),
                         aiohttp.ClientConnectionError("refused"))
    client = BridgeEventsClient("http://bridge", stub)
    assert await client.get_active_scenario(ROOM) == "movie_vhs"
    assert await client.get_active_scenario(ROOM) == "none"
    assert await client.get_active_scenario(ROOM) is None
    assert stub.calls[0] == ("GET", f"/scenario/state?room={ROOM}")


# ==================================================================================================
# the speech-policy helpers (design §4.1 / §4.4 / §5)
# ==================================================================================================

def test_ceiling_buckets_and_timers():
    assert ceiling_bucket(None) is None and ceiling_bucket(4000) is None
    assert ceiling_bucket(5000) is None and ceiling_bucket(5001) == "seconds"
    assert ceiling_bucket(15000) == "seconds" and ceiling_bucket(20000) == "seconds"
    assert ceiling_bucket(29000) == "half_minute" and ceiling_bucket(45000) == "half_minute"
    assert ceiling_bucket(55500) == "minute" and ceiling_bucket(61500) == "minute"
    assert ceiling_bucket(90000) == "minute" and ceiling_bucket(120000) == "minutes"
    assert watchdog_seconds(61500) == pytest.approx(78.875)
    assert hard_cap_seconds(61500) == pytest.approx(108.875)
    assert remaining_seconds(100.0, 55500, 140.0) == 20      # 15.5 → 20
    assert remaining_seconds(100.0, 55500, 160.0) == 5       # floor


# ==================================================================================================
# 3–8. the handler + the follower, driven by a fake events port
# ==================================================================================================

class FakeEvents(ScenarioJobEventsPort):
    """Scripted port: `push()` feeds events; `jobs` answers `get_job` in order (last repeats);
    `active` answers `get_active_scenario`."""

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.jobs: List[Any] = []
        self.active: Optional[str] = None
        self.get_calls = 0
        self.state_calls = 0
        self.subscribed: List[str] = []

    def push(self, *events):
        for e in events:
            self.queue.put_nowait(e)

    async def events(self, room_id):
        self.subscribed.append(room_id)
        while True:
            yield await self.queue.get()

    async def get_job(self, job_id):
        self.get_calls += 1
        if not self.jobs:
            return JobLookupMiss("unreachable")
        return self.jobs.pop(0) if len(self.jobs) > 1 else self.jobs[0]

    async def get_active_scenario(self, room_id):
        self.state_calls += 1
        return self.active


class FakeNotifications:
    def __init__(self):
        self.outcomes: List[Dict[str, Any]] = []
        self.acks: List[Dict[str, Any]] = []

    async def send_action_outcome(self, **kw):
        self.outcomes.append(kw)
        return True

    async def send_acknowledgement(self, **kw):
        self.acks.append(kw)
        return True

    async def send_action_completion_notification(self, **kw):   # must never be reached
        raise AssertionError(f"generic completion sent: {kw}")

    async def send_action_failure_notification(self, **kw):
        raise AssertionError(f"generic failure sent: {kw}")


class Env:
    """Registry + tmp store patched in, the handler wired with the capturing bridge + fake port."""

    def __init__(self, tmp_path: Path, loader, responses=None, flag=True):
        from locveil_voice.outputs.bridge import parse_catalog
        self.store = JsonFileDurableActionStore(tmp_path / "durable_actions.json")
        self.registry = ClientRegistry({"persistent_storage": False})
        self._patch = patch("locveil_voice.intents.handlers.base.get_client_registry",
                            return_value=self.registry)
        self.responses = list(responses or [])
        self.catalog_service = CatalogService()
        self.catalog_service.set_catalog(parse_catalog(CATALOG_PAYLOAD))
        self.capture = CapturingDeviceCommandOutput(responder=self._respond)
        self.output_manager = OutputManager()
        self.events = FakeEvents()
        self.notes = FakeNotifications()
        self.handler = SmartHomeIntentHandler()
        self.handler.donation = loader.get_donation("smart_home")
        self.handler._donation_initialized = True
        self.handler.asset_loader = loader
        self.handler._asset_loader_initialized = True
        self.handler.set_device_command_services(
            self.catalog_service, DeviceCommandDispatcher(self.output_manager),
            acknowledge_slow_actions=flag)
        self.handler.set_scenario_job_events_port(self.events)
        self.handler._notification_service = self.notes

    def _respond(self, command) -> DeliveryResult:
        status, payload = self.responses.pop(0)
        return BridgeClient._to_delivery_result(command, status, payload)

    async def __aenter__(self):
        self._patch.start()
        set_durable_action_store(self.store)
        await self.output_manager.add_output(OUTPUT_TYPE, self.capture)
        self.output_manager.designate(OutputModality.DEVICE_COMMAND, OUTPUT_TYPE)
        return self

    async def __aexit__(self, *exc):
        for rec in list(self.registry.get_all_live_actions()):
            r = self.registry.get_action(rec["physical_id"], rec["action_name"])
            if r is not None and not r.task.done():
                r.task.cancel()
        await asyncio.sleep(0)
        self._patch.stop()
        set_durable_action_store(None)
        return False

    async def run(self, suffix: str, raw_text: str, room="Гостиная", session="s1"):
        context = UnifiedConversationContext(session_id=session, room_name=room,
                                             client_id="sat-living", language="ru")
        context.request_source = "ws_audio"
        intent = Intent(name=f"smart_home.{suffix}", entities={}, confidence=1.0,
                        raw_text=raw_text, domain="smart_home")
        result = await self.handler.execute(intent, context)
        await asyncio.sleep(0.01)                    # let the follower subscribe
        return result

    def record(self):
        return self.registry.get_action("sat-living", f"scenario_job:{ROOM}")

    async def settle(self, timeout=2.0):
        rec = self.record()
        if rec is not None:
            await asyncio.wait_for(rec.task, timeout)
        for _ in range(4):
            await asyncio.sleep(0)

    def outcome_texts(self):
        return [o["message"] for o in self.notes.outcomes]


# --- 3. launch, persistence, acceptance texts ------------------------------------------------------

async def test_start_sends_wait_false_persists_the_record_and_speaks_the_ceiling(tmp_path, loader):
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        result = await env.run("scenario_start", "включи кино с видеокассеты")
        sent = env.capture.captured[0]
        assert sent.request_body()["wait"] is False and sent.to_dict() == {
            "kind": "actuate", "device_id": "scenario_manager", "capability": "scenario",
            "action": "set", "params": {"value": "movie_vhs"}}
        assert sent.timeout_seconds == pytest.approx(71.375)   # ARCH-67 sizing kept
        assert result.text == "Запускаю сценарий, около минуты" and result.should_speak
        assert result.metadata["acknowledgement"] == result.text
        assert result.metadata[SCENARIO_JOB_METADATA_KEY] == {
            "job_id": JOB, "room_id": ROOM, "max_duration_ms": 55500}
        assert env.notes.acks == []                      # no mid-turn ack for a job request
        persisted = env.store.load_all()
        assert len(persisted) == 1
        rec = persisted[0]
        assert rec.action_name == f"scenario_job:{ROOM}" and rec.redeliver
        assert rec.metadata["on_missed"] == "rearm" and rec.metadata["language"] == "ru"
        p = rec.rearm["params"]
        assert p["job_id"] == JOB and p["bridge_room"] == ROOM and p["kind"] == "switch"
        assert p["target"] == "movie_vhs" and p["label"] == "Кино с видеокассеты"
        assert p["max_duration_ms"] == 55500 and p["origin_id"] == "sat-living"
        assert p["origin_session"] == "s1" and p["origin_source"] == "ws_audio"
        assert env.record() is not None and env.handler._jobs[ROOM].job_id == JOB
        assert env.events.subscribed == [ROOM]


async def test_stop_speaks_the_none_ceiling(tmp_path, loader):
    stop_202 = (202, dict(ACCEPTED_202[1], action="off",
                          state={"scenario": "movie_vhs", "job_id": JOB, "max_duration_ms": 29000}))
    async with Env(tmp_path, loader, [stop_202]) as env:
        result = await env.run("scenario_stop", "выключи кино")
        assert env.capture.captured[0].request_body() == {"capability": "scenario",
                                                          "action": "off", "params": None,
                                                          "wait": False}
        assert result.text == "Выключаю сценарий, около полминуты"
        assert env.store.load_all()[0].rearm["params"]["kind"] == "stop"


@pytest.mark.parametrize("ceiling, text", [
    (4000, "Запускаю сценарий"),
    (15000, "Запускаю сценарий, секунд 15"),
    (16500, "Запускаю сценарий, секунд 20"),
    (29500, "Запускаю сценарий, около полминуты"),
    (61500, "Запускаю сценарий, около минуты"),
    (120000, "Запускаю сценарий, пару минут"),
])
async def test_acceptance_buckets(tmp_path, loader, ceiling, text):
    resp = (202, dict(ACCEPTED_202[1], state={"scenario": "none", "job_id": JOB,
                                               "max_duration_ms": ceiling}))
    async with Env(tmp_path, loader, [resp]) as env:
        result = await env.run("scenario_start", "включи кино с видеокассеты")
        assert result.text == text


async def test_flag_off_is_a_silent_acceptance(tmp_path, loader):
    async with Env(tmp_path, loader, [ACCEPTED_202], flag=False) as env:
        result = await env.run("scenario_start", "включи кино с видеокассеты")
        assert result.text == "" and not result.should_speak
        assert "acknowledgement" not in result.metadata
        assert result.metadata[SCENARIO_JOB_METADATA_KEY]["job_id"] == JOB
        assert env.record() is not None                  # the job is still followed
        env.events.push(parse_job_event(SWITCHED_OK))
        await env.settle()
        assert env.outcome_texts() == ["Включила «Кино с видеокассеты»"]


async def test_device_level_commands_never_carry_wait(tmp_path, loader):
    ok = (200, {"success": True, "device_id": "bedroom_hvac", "capability": "power",
                "action": "on", "state": {"power": "on"}, "error": None})
    async with Env(tmp_path, loader, [ok]) as env:
        context = UnifiedConversationContext(session_id="s1", room_name="Спальня", language="ru")
        intent = Intent(name="smart_home.power_on", entities={"target": "кондей"},
                        confidence=1.0, raw_text="включи кондей", domain="smart_home")
        from locveil_voice.core.entity_resolver import ContextualEntityResolver
        resolver = ContextualEntityResolver(loader, catalog_port=env.catalog_service)
        intent.entities = await resolver.resolve_entities(intent, context)
        await env.handler.execute(intent, context)
        assert "wait" not in env.capture.captured[0].request_body()
        assert env.capture.captured[0].wait is None
        assert env.store.load_all() == []


async def test_sync_200_on_wait_false_speaks_the_arch67_confirmation(tmp_path, loader):
    """The commons mock bridge ignores `wait` → the cross-suite's path."""
    async with Env(tmp_path, loader, [SYNC_200]) as env:
        result = await env.run("scenario_start", "включи кино с видеокассеты")
        assert result.text == "Включила «Кино с видеокассеты»" and result.success
        assert env.store.load_all() == [] and env.record() is None


# --- 4. the follower per state-machine row ---------------------------------------------------------

async def _accepted(env):
    await env.run("scenario_start", "включи кино с видеокассеты")
    assert env.record() is not None


async def test_terminal_succeeded_speaks_the_fact_and_releases(tmp_path, loader):
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        env.events.push(parse_job_event(STEP_DONE), parse_job_event(SWITCHED_OK))
        await env.settle()
        assert env.outcome_texts() == ["Включила «Кино с видеокассеты»"]
        o = env.notes.outcomes[0]
        assert o["redeliver"] and o["physical_id"] == "sat-living" and o["source"] == "ws_audio"
        assert o["session_id"] == "s1" and o["language"] == "ru" and o["room_name"] == "sat-living"
        assert env.store.load_all() == []                 # record deleted with the task
        assert ROOM not in env.handler._jobs and env.record() is None
        assert env.events.get_calls == 0                 # a live terminal needs no GET


async def test_terminal_failed_names_the_devices_from_the_catalog(tmp_path, loader):
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        failed = dict(SWITCHED_FAILED, failures=[
            {"device": "mf_amplifier", "command": "set_input", "error": "gate timeout"},
            {"device": "mf_amplifier", "command": "power", "error": "x"},
            {"device": "unknown_box", "command": "power", "error": "y"}])
        env.events.push(parse_job_event(failed))
        await env.settle()
        assert env.outcome_texts() == [
            "Включила «Кино с видеокассеты», но не ответили: Усилитель, unknown_box"]


async def test_other_jobs_terminal_and_steps_are_ignored(tmp_path, loader):
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        env.events.jobs = [_record("running")]
        env.events.push(parse_job_event(dict(STEP_DONE, job_id="j-other")),
                        parse_job_event(dict(SWITCHED_OK, job_id="j-other")))
        await asyncio.sleep(0.05)
        assert env.outcome_texts() == [] and env.record() is not None
        assert env.events.get_calls == 1                 # a foreign terminal → GET, still running
        env.events.push(parse_job_event(SWITCHED_OK))
        await env.settle()
        assert env.outcome_texts() == ["Включила «Кино с видеокассеты»"]


async def test_stream_open_gets_the_record_running_then_terminal(tmp_path, loader):
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        env.events.jobs = [_record("running"), _record("failed", failures=[
            JobFailure(device="living_room_tv", command="power_on", error="gate timeout")])]
        # (`living_room_tv` is not in the test house → the id itself is spoken)
        env.events.push(JobEvent(kind=JobEventKind.STREAM_OPEN))
        await asyncio.sleep(0.05)
        assert env.outcome_texts() == [] and env.record() is not None
        env.events.push(JobEvent(kind=JobEventKind.STREAM_OPEN))      # reconnect: GET → failed
        await env.settle()
        assert env.events.get_calls == 2
        assert env.outcome_texts() == ["Включила «Кино с видеокассеты», но не ответили: living_room_tv"]


async def test_bridge_restart_speaks_the_actual_state(tmp_path, loader):
    for active, text in [("movie_vhs", "Сценарий «Кино с видеокассеты» включён, мост перезапускался"),
                         ("none", "Мост перезапускался, сценарий «Кино с видеокассеты» не включился"),
                         (None, "Мост не отвечает — не знаю, включился ли сценарий «Кино с видеокассеты»")]:
        async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
            await _accepted(env)
            env.events.jobs = [JobLookupMiss("unknown")]
            env.events.active = active
            env.events.push(JobEvent(kind=JobEventKind.STREAM_OPEN))
            await env.settle()
            assert env.outcome_texts() == [text] and env.events.state_calls == 1


async def test_bridge_restart_after_a_stop_checks_for_idle(tmp_path, loader):
    stop_202 = (202, dict(ACCEPTED_202[1], action="off",
                          state={"scenario": "movie_vhs", "job_id": JOB, "max_duration_ms": 29000}))
    async with Env(tmp_path, loader, [stop_202]) as env:
        await env.run("scenario_stop", "выключи кино")
        env.events.jobs = [JobLookupMiss("unknown")]
        env.events.active = "none"
        env.events.push(JobEvent(kind=JobEventKind.STREAM_OPEN))
        await env.settle()
        assert env.outcome_texts() == ["Сценарий выключен, мост перезапускался"]


async def test_unreachable_on_reconnect_keeps_following(tmp_path, loader):
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        env.events.jobs = []                              # unreachable
        env.events.push(JobEvent(kind=JobEventKind.STREAM_OPEN))
        await asyncio.sleep(0.05)
        assert env.outcome_texts() == [] and env.record() is not None
        env.events.push(parse_job_event(SWITCHED_OK))
        await env.settle()
        assert env.outcome_texts() == ["Включила «Кино с видеокассеты»"]


async def test_watchdog_then_hard_cap_stalled(tmp_path, loader, monkeypatch):
    """W fires with the stream alive → GET (running) → keep following; H fires → one last GET
    (still running) → «всё ещё переключается»."""
    monkeypatch.setattr("locveil_voice.intents.scenario_jobs.WATCHDOG_FACTOR", 0.0)
    monkeypatch.setattr("locveil_voice.intents.scenario_jobs.WATCHDOG_MARGIN_S", 0.05)
    monkeypatch.setattr("locveil_voice.intents.scenario_jobs.HARD_CAP_EXTRA_S", 0.1)
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        env.events.jobs = [_record("running")]
        await env.settle(timeout=3)
        assert env.events.get_calls == 2                  # W, then H
        assert env.outcome_texts() == ["Сценарий «Кино с видеокассеты» всё ещё переключается — проверьте"]
        assert env.record() is None and ROOM not in env.handler._jobs


async def test_hard_cap_unreachable_is_lost(tmp_path, loader, monkeypatch):
    monkeypatch.setattr("locveil_voice.intents.scenario_jobs.WATCHDOG_FACTOR", 0.0)
    monkeypatch.setattr("locveil_voice.intents.scenario_jobs.WATCHDOG_MARGIN_S", 0.05)
    monkeypatch.setattr("locveil_voice.intents.scenario_jobs.HARD_CAP_EXTRA_S", 0.05)
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        await env.settle(timeout=3)
        assert env.outcome_texts() == [
            "Мост не отвечает — не знаю, включился ли сценарий «Кино с видеокассеты»"]


async def test_watchdog_get_finds_the_terminal(tmp_path, loader, monkeypatch):
    monkeypatch.setattr("locveil_voice.intents.scenario_jobs.WATCHDOG_FACTOR", 0.0)
    monkeypatch.setattr("locveil_voice.intents.scenario_jobs.WATCHDOG_MARGIN_S", 0.05)
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        env.events.jobs = [_record("succeeded")]
        await env.settle(timeout=3)
        assert env.outcome_texts() == ["Включила «Кино с видеокассеты»"]


# --- 5. the 409 both ways + 6. «stop» ----------------------------------------------------------------

async def test_second_command_mid_job_is_refused_locally(tmp_path, loader):
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        env.handler._jobs[ROOM].accepted_at = time.time() - 30     # 25.5 s left → 30
        result = await env.run("scenario_start", "включи кино с эппл ти ви")
        assert result.text == "Ещё переключаю на «Кино с видеокассеты», остановить можно будет секунд через 30"
        assert not result.success and result.metadata[SCENARIO_JOB_METADATA_KEY]["busy"]
        assert len(env.capture.captured) == 1             # no second request
        stop = await env.run("scenario_stop", "выключи кино")
        assert stop.text.startswith("Ещё переключаю на «Кино с видеокассеты»")
        assert len(env.capture.captured) == 1
        # after the terminal, «stop» is a new job with none's ceiling
        env.events.push(parse_job_event(SWITCHED_OK))
        await env.settle()
        env.responses.append((202, dict(ACCEPTED_202[1], action="off", state={
            "scenario": "movie_vhs", "job_id": "j-2", "max_duration_ms": 29000})))
        stop = await env.run("scenario_stop", "выключи кино")
        assert stop.text == "Выключаю сценарий, около полминуты"
        assert env.capture.captured[-1].request_body()["action"] == "off"
        assert env.handler._jobs[ROOM].job_id == "j-2"


async def test_409_from_another_clients_job_is_adopted(tmp_path, loader):
    async with Env(tmp_path, loader, [BUSY_409]) as env:
        env.events.jobs = [_record("running", target="movie_appletv", max_duration_ms=60500)]
        result = await env.run("scenario_start", "включи кино с видеокассеты")
        assert result.text == "Ещё переключаю на «Кино с Apple TV», остановить можно будет секунд через 65"
        assert env.record() is not None and env.handler._jobs[ROOM].job_id == JOB
        assert env.store.load_all()[0].rearm["params"]["target"] == "movie_appletv"
        env.events.push(parse_job_event(dict(SWITCHED_OK, scenario_id="movie_appletv")))
        await env.settle()
        assert env.outcome_texts() == ["Включила «Кино с Apple TV»"]


async def test_409_whose_job_vanished_is_refused_without_a_follower(tmp_path, loader):
    async with Env(tmp_path, loader, [BUSY_409]) as env:
        env.events.jobs = [JobLookupMiss("unknown")]
        result = await env.run("scenario_start", "включи кино с видеокассеты")
        # N from the catalog's ceiling for the command voice sent (55 500 → 60)
        assert result.text == "Ещё переключаю на «Кино с видеокассеты», остановить можно будет секунд через 60"
        assert env.record() is None and env.store.load_all() == []


async def test_a_stop_running_refuses_with_its_own_phrase(tmp_path, loader):
    stop_202 = (202, dict(ACCEPTED_202[1], action="off",
                          state={"scenario": "movie_vhs", "job_id": JOB, "max_duration_ms": 29000}))
    async with Env(tmp_path, loader, [stop_202]) as env:
        await env.run("scenario_stop", "выключи кино")
        result = await env.run("scenario_start", "включи кино с видеокассеты")
        assert result.text == "Ещё выключаю сценарий, секунд через 30 можно будет продолжить"


# --- 7. restart paths ----------------------------------------------------------------------------------

def _persisted(env, **over) -> DurableActionRecord:
    rec = env.store.load_all()[0]
    data = rec.to_dict()
    data.update(over)
    return DurableActionRecord.from_dict(data)


async def test_voice_restart_rearms_and_gets_the_record(tmp_path, loader):
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        env.record().task.cancel()                        # process teardown: record kept
        await asyncio.sleep(0.02)
        assert len(env.store.load_all()) == 1
        assert env.record() is None, "teardown cancel must reap the in-memory record"
        env.handler._jobs.clear()
        env.events.jobs = [_record("succeeded")]
        stats = await reconcile_durable_actions(
            env.store, {"SmartHomeIntentHandler": env.handler}, env.notes)
        assert stats["rearmed"] == 1
        assert env.handler._jobs[ROOM].job_id == JOB     # the index is rebuilt
        await env.settle()
        assert env.events.get_calls == 1 and env.outcome_texts() == ["Включила «Кино с видеокассеты»"]
        assert env.store.load_all() == []


async def test_voice_restart_after_the_deadline_still_asks_the_handler(tmp_path, loader):
    """`on_missed: rearm` — a record past its deadline is re-armed, not announced as a missed
    timer; the follower GETs and speaks the truth."""
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        env.record().task.cancel()
        await asyncio.sleep(0.02)
        late = _persisted(env, deadline=time.time() - 600, started_at=time.time() - 700)
        late.rearm["params"]["accepted_at"] = time.time() - 700
        env.store.save(late)
        env.handler._jobs.clear()
        env.events.jobs = [JobLookupMiss("unknown")]
        env.events.active = "movie_vhs"
        stats = await reconcile_durable_actions(
            env.store, {"SmartHomeIntentHandler": env.handler}, env.notes)
        assert stats == {"rearmed": 1, "fired_late": 0, "expired": 0}
        await env.settle()
        assert env.outcome_texts() == ["Сценарий «Кино с видеокассеты» включён, мост перезапускался"]


async def test_stale_resume_is_silent(tmp_path, loader):
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        env.record().task.cancel()
        await asyncio.sleep(0.02)
        old = _persisted(env, deadline=time.time() - 7200, started_at=time.time() - 7300)
        old.rearm["params"]["accepted_at"] = time.time() - 7300
        env.store.save(old)
        env.handler._jobs.clear()
        stats = await reconcile_durable_actions(
            env.store, {"SmartHomeIntentHandler": env.handler}, env.notes)
        assert stats["rearmed"] == 1
        await env.settle()
        assert env.outcome_texts() == [] and env.events.get_calls == 0
        assert env.store.load_all() == [] and ROOM not in env.handler._jobs


async def test_timer_records_keep_the_deadline_gate(tmp_path):
    """A record WITHOUT `on_missed` past its deadline takes today's path (no re-arm call)."""
    store = JsonFileDurableActionStore(tmp_path / "d.json")
    store.save(DurableActionRecord(action_name="timer_1", domain="timers", handler="H",
                                   physical_id="k", started_at=time.time() - 100,
                                   deadline=time.time() - 10, session_id=None,
                                   metadata={"language": "ru", "completion_message": "чай"}))

    class H:
        calls = 0

        async def rearm_durable_action(self, record):
            H.calls += 1
            return True

    stats = await reconcile_durable_actions(store, {"H": H()}, None)
    assert stats == {"rearmed": 0, "fired_late": 1, "expired": 0} and H.calls == 0


async def test_rearm_refuses_a_record_without_a_job(tmp_path, loader):
    async with Env(tmp_path, loader) as env:
        rec = DurableActionRecord(action_name="scenario_job:x", domain="smart_home",
                                  handler="SmartHomeIntentHandler", physical_id="k",
                                  started_at=time.time(), deadline=None,
                                  rearm={"method": "_follow_scenario_job", "params": {}})
        assert await env.handler.rearm_durable_action(rec) is False


# --- 8. routing: the outcome reaches the origin channel as speech, queued when offline ---------------

async def test_outcome_reaches_the_origin_channel_and_bypasses_the_threshold():
    captured = []
    om = OutputManager()
    await om.add_output("console", ConsoleOutput(sink=captured.append, origin="cli"))
    svc = NotificationService()
    svc.set_output_manager(om)

    class _Ctx:
        def should_notify_completion(self, domain, duration):
            return False                                    # the 30 s gate would say no

    class _CM:
        async def get_or_create_context(self, sid):
            return _Ctx()

    svc.context_manager = _CM()
    assert await svc.send_action_outcome(session_id="s1", domain="smart_home",
                                         action_name="scenario_job:living_room",
                                         message="Включила «Кино»", source="cli",
                                         physical_id="s1", language="ru")
    note = await asyncio.wait_for(svc._notification_queue.get(), 1)
    await svc._deliver_notification(note)
    assert captured == ["📝 Включила «Кино»"] and note.redeliver


async def test_outcome_for_an_offline_satellite_is_queued_for_redelivery(tmp_path):
    store = JsonFileDurableActionStore(tmp_path / "d.json")
    set_durable_action_store(store)
    try:
        om = OutputManager()
        await om.add_output("console", ConsoleOutput(sink=lambda t: None, origin="cli"))
        svc = NotificationService()
        svc.set_output_manager(om)
        await svc.send_action_outcome(session_id="s1", domain="smart_home",
                                      action_name="scenario_job:living_room",
                                      message="Включила «Кино»", source="ws_audio",
                                      physical_id="sat-living", language="ru")
        note = await asyncio.wait_for(svc._notification_queue.get(), 1)
        await svc._deliver_notification(note)
        queued = store.pop_undelivered(["sat-living"])
        assert [q.message for q in queued] == ["Включила «Кино»"]
    finally:
        set_durable_action_store(None)


async def test_announced_record_sends_no_generic_completion(tmp_path, loader):
    """The follower marks the record; the done-callback's generic notice is suppressed (the
    FakeNotifications raises on any generic completion/failure)."""
    async with Env(tmp_path, loader, [ACCEPTED_202]) as env:
        await _accepted(env)
        env.events.push(parse_job_event(SWITCHED_OK))
        await env.settle()
        assert len(env.notes.outcomes) == 1
