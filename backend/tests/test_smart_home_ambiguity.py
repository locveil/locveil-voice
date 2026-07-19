"""BUG-39 — the ambiguity clarification must be answerable.

`_ambiguous_result` used to build the option list from names alone, so three ACs all named
«Кондиционер» produced «Какой именно: Кондиционер или Кондиционер или Кондиционер?» — a
question the user can only answer by repeating themselves. Identical names are now qualified
by room (room-led when ALL candidates share one name), falling back to the device id when
the rooms coincide too. Distinct-name lists are unchanged.
"""

from pathlib import Path

import pytest

from locveil_voice.core.catalog_service import CatalogService
from locveil_voice.core.intent_asset_loader import AssetLoaderConfig, IntentAssetLoader
from locveil_voice.intents.context_models import UnifiedConversationContext
from locveil_voice.intents.handlers.smart_home import SmartHomeIntentHandler
from locveil_voice.intents.models import Intent

CATALOG_PAYLOAD = {
    "version": "test-ambiguity-1",
    "rooms": [
        {"id": "bedroom", "names": {"ru": "Спальня"}, "devices": []},
        {"id": "children_room", "names": {"ru": "Детская"}, "devices": []},
        {"id": "living_room", "names": {"ru": "Гостиная"}, "devices": []},
    ],
    "devices": [],
}


@pytest.fixture(scope="module")
async def handler():
    loader = IntentAssetLoader(Path("assets"), AssetLoaderConfig(strict_mode=True))
    await loader.load_all_assets(["smart_home"])
    h = SmartHomeIntentHandler()
    h.donation = loader.get_donation("smart_home")
    h._donation_initialized = True
    h.asset_loader = loader
    h._asset_loader_initialized = True
    service = CatalogService()
    from locveil_voice.outputs.bridge import parse_catalog
    service.set_catalog(parse_catalog(CATALOG_PAYLOAD))
    h.catalog_port = service
    return h


def _ask(handler, candidates):
    context = UnifiedConversationContext(session_id="s", language="ru")
    intent = Intent(name="smart_home.power_on", entities={}, confidence=1.0,
                    raw_text="включи кондиционер", domain="smart_home")
    result = handler._ambiguous_result(intent, context, candidates, "target")
    return result, context


async def test_identical_names_ask_room_led(handler):
    result, context = _ask(handler, [
        {"device_id": "bedroom_hvac", "room": "bedroom", "name": "Кондиционер"},
        {"device_id": "children_room_hvac", "room": "children_room", "name": "Кондиционер"},
        {"device_id": "living_room_hvac", "room": "living_room", "name": "Кондиционер"},
    ])
    assert "в нескольких комнатах" in result.text
    assert "Спальня" in result.text and "Детская" in result.text and "Гостиная" in result.text
    assert "Кондиционер или Кондиционер" not in result.text
    # the clarification machinery is unchanged
    assert result.metadata.get("clarification") is True
    assert result.metadata.get("candidates") == [
        "bedroom_hvac", "children_room_hvac", "living_room_hvac"]
    assert context.pending_clarification is not None


async def test_mixed_list_qualifies_only_collisions(handler):
    result, _ = _ask(handler, [
        {"device_id": "bedroom_hvac", "room": "bedroom", "name": "Кондиционер"},
        {"device_id": "living_room_hvac", "room": "living_room", "name": "Кондиционер"},
        {"device_id": "bedroom_heater", "room": "bedroom", "name": "Обогреватель"},
    ])
    assert "Кондиционер — Спальня" in result.text
    assert "Кондиционер — Гостиная" in result.text
    assert "Обогреватель —" not in result.text and "Обогреватель" in result.text


async def test_same_room_collision_falls_back_to_device_id(handler):
    # genuine within-room ambiguity: two sconces, one room — the id is the last honest qualifier
    result, _ = _ask(handler, [
        {"device_id": "bedroom_sconce_left", "room": "bedroom", "name": "Ночник"},
        {"device_id": "bedroom_sconce_right", "room": "bedroom", "name": "Ночник"},
    ])
    assert "Ночник — bedroom_sconce_left" in result.text
    assert "Ночник — bedroom_sconce_right" in result.text


async def test_distinct_names_stay_plain(handler):
    result, _ = _ask(handler, [
        {"device_id": "bedroom_heating", "room": "bedroom", "name": "Обогрев"},
        {"device_id": "bedroom_hvac", "room": "bedroom", "name": "Кондиционер"},
    ])
    assert "Обогрев или Кондиционер" in result.text
    assert "—" not in result.text
