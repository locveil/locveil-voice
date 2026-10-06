"""ARCH-67 — request sizing from the catalog's published timing (contract v1.11 "Timing";
board PROD-18 round 2, decision 8), at the domain + dispatcher level.

The handler-level acceptance (the acknowledgement, the spoken outcome) lives in
`test_smart_home_handler.py`; this file pins the formula, the per-address-form lookup, and
the dispatcher's bounded wait — the three places the policy could silently drift.
"""

import asyncio

import pytest

from locveil_voice.core.device_command_dispatcher import (
    DEFAULT_FALLBACK_TIMEOUT_S,
    DISPATCH_GRACE_S,
    DeviceCommandDispatcher,
)
from locveil_voice.intents.device_commands import (
    SLOW_ACTION_THRESHOLD_MS,
    DeviceCommand,
    GroupScope,
    RoomGroupCommand,
    is_slow_action,
    published_wait_ms,
    size_request_timeout,
)
from locveil_voice.outputs.bridge import parse_catalog

HOUSE = {
    "version": "sizing-1",
    "rooms": [{"id": "living", "names": {"ru": "Гостиная", "en": "Living room"},
               "devices": [], "group_defaults": {"climate": "ac"}}],
    "devices": [
        {"id": "ac", "room": "living", "names": {"ru": "Кондиционер", "en": "AC"},
         "capabilities": [
             {"name": "power", "group": "climate", "confirm_timeout_ms": 15000,
              "actions": [{"name": "on"}, {"name": "off"}]},
             {"name": "mode", "group": "climate", "confirm_timeout_ms": 15000,
              "actions": [{"name": "set", "params": [
                  {"name": "value", "type": "string", "required": True,
                   "values": [{"wire": "2", "canonical": "cool",
                               "labels": {"ru": "охлаждение", "en": "cool"}}]}]}]}]},
        {"id": "heater", "room": "living", "names": {"ru": "Обогрев", "en": "Heater"},
         "capabilities": [
             {"name": "climate", "group": "climate",   # a relay: nothing published
              "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "spots", "room": "living", "names": {"ru": "Споты", "en": "Spots"},
         "capabilities": [
             {"name": "power", "group": "light", "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "tv", "room": "living", "names": {"ru": "Телевизор", "en": "TV"},
         "capabilities": [
             {"name": "power", "group": "power", "confirm_timeout_ms": 8000,
              "actions": [{"name": "on"}, {"name": "off"}]},
             {"name": "input", "group": "input", "confirm_timeout_ms": 3000,
              "actions": [{"name": "set", "params": [
                  {"name": "value", "type": "string", "required": True, "options_from": "inputs"}]}]}]},
        {"id": "scenarios", "room": "living", "names": {"ru": "Сценарии", "en": "Scenarios"},
         "capabilities": [
             {"name": "scenario", "group": "scenario",
              "actions": [{"name": "set", "params": [
                  {"name": "value", "type": "enum", "required": True,
                   "values": [{"wire": "movie_zappiti", "canonical": "movie_zappiti",
                               "labels": {"ru": "Кино с Заппити", "en": "Movie (Zappiti)"},
                               "max_duration_ms": 61500},
                              {"wire": "music_tape", "canonical": "music_tape",
                               "labels": {"ru": "Музыка с кассеты", "en": "Tape"},
                               "max_duration_ms": 29500}]}]},
                          {"name": "off"}],
              "fields": [{"name": "scenario", "type": "string",
                          "labels": {"ru": "сценарий", "en": "scenario"},
                          "values": [{"wire": "none", "canonical": "none",
                                      "labels": {"ru": "нет", "en": "none"},
                                      "max_duration_ms": 29000}]}]}]},
    ],
}


@pytest.fixture(scope="module")
def catalog():
    return parse_catalog(HOUSE)


# --- the formula ----------------------------------------------------------------------------------

@pytest.mark.parametrize("published_ms, expected_s", [
    (15000, 20.75),    # HVAC
    (25000, 33.25),    # streamer power
    (8000, 12.0),      # TV power
    (3000, 5.75),      # inputs
    (61500, 78.875),   # movie_zappiti ceiling
    (500, 2.625),
])
def test_size_request_timeout_is_1_25x_plus_2s(published_ms, expected_s):
    assert size_request_timeout(published_ms) == pytest.approx(expected_s)


def test_slow_threshold_is_strict_at_3s():
    assert SLOW_ACTION_THRESHOLD_MS == 3000
    assert not is_slow_action(None)
    assert not is_slow_action(3000)
    assert is_slow_action(3001)
    assert is_slow_action(5000)


# --- the lookup, device form ----------------------------------------------------------------------

def test_device_form_reads_confirm_timeout_ms(catalog):
    assert published_wait_ms(catalog, DeviceCommand("ac", "power", "on")) == 15000
    assert published_wait_ms(catalog, DeviceCommand("ac", "mode", "set", {"value": "cool"})) == 15000
    assert published_wait_ms(catalog, DeviceCommand("tv", "input", "set", {"value": "hdmi1"})) == 3000


def test_device_form_absent_field_is_none(catalog):
    assert published_wait_ms(catalog, DeviceCommand("spots", "power", "on")) is None
    assert published_wait_ms(catalog, DeviceCommand("heater", "climate", "off")) is None


def test_unknown_device_or_capability_is_none(catalog):
    assert published_wait_ms(catalog, DeviceCommand("ghost", "power", "on")) is None
    assert published_wait_ms(catalog, DeviceCommand("ac", "fan", "set", {"value": "auto"})) is None


def test_scenario_value_ceiling_wins_over_the_capability(catalog):
    """`max_duration_ms` on the chosen value is the bound; the scenario capability itself
    carries no `confirm_timeout_ms` (as pinned)."""
    assert published_wait_ms(
        catalog, DeviceCommand("scenarios", "scenario", "set", {"value": "movie_zappiti"})) == 61500
    assert published_wait_ms(
        catalog, DeviceCommand("scenarios", "scenario", "set", {"value": "music_tape"})) == 29500


def test_scenario_off_reads_the_fields_none_entry(catalog):
    assert published_wait_ms(catalog, DeviceCommand("scenarios", "scenario", "off")) == 29000


def test_scenario_unknown_value_falls_to_none(catalog):
    assert published_wait_ms(
        catalog, DeviceCommand("scenarios", "scenario", "set", {"value": "nope"})) is None


# --- the lookup, room form -------------------------------------------------------------------------

def test_room_form_takes_the_slowest_member(catalog):
    """«включи кондиционер» as a room-group: the bridge may pick the AC (15 s) or fan out to the
    relay heater (nothing published) — the honest ceiling is the slowest member."""
    cmd = RoomGroupCommand("living", "climate", "on", scope=GroupScope.AUTO)
    assert published_wait_ms(catalog, cmd) == 15000


def test_room_form_with_no_published_member_is_none(catalog):
    assert published_wait_ms(catalog, RoomGroupCommand("living", "light", "on")) is None
    assert published_wait_ms(catalog, RoomGroupCommand("living", "cover", "open")) is None
    assert published_wait_ms(catalog, RoomGroupCommand("nowhere", "climate", "on")) is None


# --- the command carries the sizing without changing its identity ---------------------------------

def test_timeout_is_not_part_of_the_command_identity():
    plain = DeviceCommand("ac", "power", "on")
    sized = DeviceCommand("ac", "power", "on", timeout_seconds=20.75)
    assert plain == sized                       # fixtures/captures compare WHAT is sent
    assert sized.to_dict() == plain.to_dict()   # the capture shape is untouched
    assert sized.request_body() == plain.request_body()
    room = RoomGroupCommand("living", "climate", "on", timeout_seconds=20.75)
    assert room == RoomGroupCommand("living", "climate", "on")
    assert "timeout" not in str(room.request_body())


# --- the dispatcher's bounded wait -----------------------------------------------------------------

def test_dispatcher_wait_is_sized_or_fallback_plus_grace():
    d = DeviceCommandDispatcher(output_manager=None, fallback_timeout_seconds=20.0)
    assert d.wait_seconds(DeviceCommand("ac", "power", "on", timeout_seconds=20.75)) == \
        pytest.approx(20.75 + DISPATCH_GRACE_S)
    assert d.wait_seconds(DeviceCommand("spots", "power", "on")) == \
        pytest.approx(20.0 + DISPATCH_GRACE_S)
    # the default fallback agrees with the config model's default (20 s), so a dispatcher built
    # without the config (tests) bounds exactly like one built from it
    assert DEFAULT_FALLBACK_TIMEOUT_S == 20.0
    assert DeviceCommandDispatcher(None).wait_seconds(DeviceCommand("spots", "power", "on")) == \
        pytest.approx(22.0)


async def test_dispatcher_honours_the_sized_wait():
    """A delivery slower than the sized wait + grace → None (the degraded path); one that fits
    returns the adapter's result. The wait is per command, not one constant."""
    class SlowManager:
        def __init__(self, delay):
            self.delay = delay

        async def deliver(self, result, context, modality):
            await asyncio.sleep(self.delay)
            return ["delivered"]

    fast = DeviceCommandDispatcher(SlowManager(0.01), fallback_timeout_seconds=0.05)
    assert await fast.deliver_device_command(DeviceCommand("spots", "power", "on"), None) == "delivered"
    # the generous fallback (10 s) is NOT what bounds a sized command — its own number (+ grace) is
    slow = DeviceCommandDispatcher(SlowManager(DISPATCH_GRACE_S + 0.2), fallback_timeout_seconds=10.0)
    assert await slow.deliver_device_command(
        DeviceCommand("ac", "power", "on", timeout_seconds=0.05), None) is None
