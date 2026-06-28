"""
Context-Based Entity Resolution System

This module implements context-aware entity resolution capabilities that use
client identification, device context, and conversation history to enhance
entity extraction and provide better understanding of user intents.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from ..intents.models import Intent
from ..intents.context_models import UnifiedConversationContext
from ..utils.units import parse_duration, TIME_UNITS  # the one shared time-unit parser + surface table

# Required rapidfuzz import for fuzzy matching
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


@dataclass
class EntityResolutionResult:
    """Result of entity resolution with confidence and metadata"""
    resolved_value: Any
    original_value: str
    confidence: float
    resolution_type: str  # "exact", "fuzzy", "contextual", "inferred"
    metadata: Dict[str, Any]


class ContextualEntityResolver:
    """
    Context-aware entity resolver that uses client identification, device
    capabilities, and conversation history to resolve entity references.
    
    This implements the entity resolution capabilities described in the 
    Intent Keyword Donation Architecture document.
    """
    
    def __init__(self, asset_loader=None):
        self.logger = logging.getLogger(f"{__name__}.ContextualEntityResolver")
        
        # Entity type resolvers
        self.device_resolver = DeviceEntityResolver(asset_loader)
        self.location_resolver = LocationEntityResolver(asset_loader)
        self.temporal_resolver = TemporalEntityResolver()
        self.quantity_resolver = QuantityEntityResolver()
    
    async def resolve_entities(self, intent: Intent, context: UnifiedConversationContext) -> Dict[str, Any]:
        """
        Resolve all entities in the intent using context-aware resolution.
        
        Args:
            intent: Intent with entities to resolve
            context: UnifiedConversationContext with client and device information
            
        Returns:
            Dictionary with resolved entities and resolution metadata
        """
        resolved_entities = intent.entities.copy()
        resolution_metadata = {}
        
        for entity_name, entity_value in intent.entities.items():
            if isinstance(entity_value, str) and entity_value.strip():
                # Try different resolution strategies
                resolution_result, attempted_kind = await self._resolve_single_entity(
                    entity_name, entity_value, intent, context
                )

                if resolution_result:
                    resolved_entities[f"{entity_name}_resolved"] = resolution_result.resolved_value
                    resolved_entities[f"{entity_name}_confidence"] = resolution_result.confidence
                    resolved_entities[f"{entity_name}_resolution_type"] = resolution_result.resolution_type

                    resolution_metadata[entity_name] = resolution_result.metadata

                    self.logger.debug(f"Resolved entity '{entity_name}': '{entity_value}' -> "
                                    f"{resolution_result.resolved_value} ({resolution_result.resolution_type})")
                elif attempted_kind in ("device", "location"):
                    # We classified this as a device/room reference and tried to resolve it, but found no
                    # match. Mark it so the fail-loud / clarification boundary (QUAL-30) can distinguish
                    # "unresolvable reference" from "never a resolvable entity". (Device/room resolution
                    # becomes fully real once ARCH-6 registers physical devices/rooms.)
                    resolved_entities[f"{entity_name}_resolution_failed"] = True
                    self.logger.debug(f"Entity '{entity_name}'='{entity_value}' classified as {attempted_kind} "
                                      f"but did not resolve — marked _resolution_failed")

        # Add resolution metadata
        if resolution_metadata:
            resolved_entities["_resolution_metadata"] = resolution_metadata

        return resolved_entities

    async def _resolve_single_entity(self, entity_name: str, entity_value: str,
                                   intent: Intent, context: UnifiedConversationContext) -> Tuple[Optional[EntityResolutionResult], Optional[str]]:
        """Resolve a single entity using the appropriate strategy.

        Returns ``(result, attempted_kind)`` where ``attempted_kind`` ∈
        {device, location, temporal, quantity, None} names the resolver that ran (or None if the
        entity matched no resolvable class) — so the caller can mark an attempted-but-unresolved
        device/location reference (``_resolution_failed``) without flagging every plain parameter.

        NOTE: dispatch is heuristic (`_is_*_entity` name/value patterns). The declarative
        `entity_type`-driven swap is owned by ARCH-6 (it activates with real room/device registration;
        every `entity_type` decl is `generic` today, so the swap would be inert before then)."""
        # Device entity resolution
        if self._is_device_entity(entity_name, entity_value, intent):
            return await self.device_resolver.resolve(entity_value, context), "device"

        # Location entity resolution
        if self._is_location_entity(entity_name, entity_value, intent):
            return await self.location_resolver.resolve(entity_value, context), "location"

        # Temporal entity resolution
        if self._is_temporal_entity(entity_name, entity_value, intent):
            return await self.temporal_resolver.resolve(entity_value, context), "temporal"

        # Quantity entity resolution
        if self._is_quantity_entity(entity_name, entity_value, intent):
            return await self.quantity_resolver.resolve(entity_value, context), "quantity"

        return None, None
    
    def _is_device_entity(self, entity_name: str, entity_value: str, intent: Intent) -> bool:
        """Check if entity is a device reference based on intent domain and generic entity name patterns"""
        # Primary: Check intent domain for device-related intents
        if intent.domain in ["device", "smart_home", "iot", "home_automation"]:
            return True
        
        # Secondary: Check for generic device entity naming patterns
        generic_device_patterns = [
            "device", "target", "appliance", "устройство", "цель"
        ]
        
        if any(pattern in entity_name.lower() for pattern in generic_device_patterns):
            return True
        
        return False
    
    def _is_location_entity(self, entity_name: str, entity_value: str, intent: Intent) -> bool:
        """Check if entity is a location reference based on generic entity name patterns"""
        # Check for generic location entity naming patterns
        generic_location_patterns = [
            "location", "place", "destination", "area", "zone",
            "место", "локация", "расположение", "зона"  # Russian equivalents
        ]
        
        return any(pattern in entity_name.lower() for pattern in generic_location_patterns)
    
    def _is_temporal_entity(self, entity_name: str, entity_value: str, intent: Intent) -> bool:
        """Check if entity is a time/date reference based on entity name patterns and value patterns"""
        # Check entity name patterns (common entity naming conventions)
        temporal_entity_names = [
            "time", "date", "when", "duration", "timeout", "delay", "schedule",
            "время", "дата", "длительность", "таймаут", "расписание"  # Russian equivalents
        ]
        
        # Check entity name patterns
        if any(pattern in entity_name.lower() for pattern in temporal_entity_names):
            return True
        
        # Check entity value patterns (time formats)
        time_patterns = r'\d+:\d+|\d+\s*(hours?|minutes?|seconds?|часов?|часа|минут?|мин|секунд?|сек)'
        return bool(re.search(time_patterns, entity_value.lower()))
    
    def _is_quantity_entity(self, entity_name: str, entity_value: str, intent: Intent) -> bool:
        """Check if entity is a quantity/number reference based on entity name patterns and value patterns"""
        # Check entity name patterns (common entity naming conventions)
        quantity_entity_names = [
            "number", "count", "amount", "quantity", "value", "level", "percent", "percentage",
            "число", "количество", "сумма", "объем", "размер", "процент"  # Russian equivalents
        ]
        
        # Check entity name patterns
        if any(pattern in entity_name.lower() for pattern in quantity_entity_names):
            return True
        
        # Check entity value patterns (contains numbers)
        return bool(re.search(r'\d+', entity_value))


class DeviceEntityResolver:
    """Resolver for device-related entities using client context"""
    
    def __init__(self, asset_loader=None):
        self.asset_loader = asset_loader
        self.logger = logging.getLogger(f"{__name__}.DeviceEntityResolver")
        self._assets_warned = False  # warn-once guard for missing/empty localization assets

    def _warn_assets_once(self, message: str) -> None:
        """Log a degradation warning at most once per resolver (avoid per-request log spam)."""
        if not self._assets_warned:
            self.logger.warning(message)
            self._assets_warned = True

    def _load_device_types(self, language: str = "en") -> Dict[str, List[str]]:
        """Load device type keywords from localization files.

        Best-effort: returns {} (with a one-time warning) when the asset loader isn't wired yet or
        the localization data is missing/empty, rather than raising. The resolver then simply skips
        type-inference matching and degrades — a device utterance must never abort the whole request
        just because deferred asset coordination hasn't run (QUAL-11 P0 #4)."""
        if not self.asset_loader:
            self._warn_assets_once(
                "DeviceEntityResolver: asset loader not wired — skipping device type-inference "
                "(exact/fuzzy device-name matching still works)."
            )
            return {}

        try:
            device_localization = self.asset_loader.localizations.get("devices", {})
            device_data = device_localization.get(language, {})

            if not device_data and language != "en":
                # Fallback to English
                device_data = device_localization.get("en", {})

            device_types = device_data.get("device_types", {}) if device_data else {}
            if not device_types:
                self._warn_assets_once(
                    f"DeviceEntityResolver: no device type mappings for language '{language}' "
                    f"in assets/localization/devices/ — skipping type-inference."
                )
                return {}

            # Convert to expected format
            result = {}
            for device_type, config in device_types.items():
                keywords = config.get("keywords", [])
                aliases = config.get("aliases", [])
                result[device_type] = keywords + aliases

            return result
        except Exception as e:
            self._warn_assets_once(
                f"DeviceEntityResolver: failed to load device types from localization files: {e} — "
                f"skipping type-inference."
            )
            return {}
    
    
    async def resolve(self, device_reference: str, context: UnifiedConversationContext) -> Optional[EntityResolutionResult]:
        """
        Resolve device reference using client context and fuzzy matching.
        """
        available_devices = context.get_device_capabilities()
        if not available_devices:
            return None
        
        device_reference_lower = device_reference.lower().strip()
        
        # 1. Exact name match
        for device in available_devices:
            device_name = device.get("name", "").lower()
            if device_name == device_reference_lower:
                return EntityResolutionResult(
                    resolved_value=device,
                    original_value=device_reference,
                    confidence=1.0,
                    resolution_type="exact",
                    metadata={"match_type": "exact_name", "device_id": device.get("id")}
                )
        
        # 2. Fuzzy name matching using rapidfuzz
        device_names = [device.get("name", "") for device in available_devices]
        best_match = process.extractOne(device_reference, device_names, scorer=fuzz.ratio)
        
        if best_match and best_match[1] >= 70:  # 70% similarity threshold
            for device in available_devices:
                if device.get("name", "") == best_match[0]:
                    return EntityResolutionResult(
                        resolved_value=device,
                        original_value=device_reference,
                        confidence=best_match[1] / 100.0,
                        resolution_type="fuzzy",
                        metadata={"match_type": "fuzzy_name", "similarity": best_match[1]}
                    )
        
        # 3. Type-based matching using localization files
        # Determine language from context
        language = context.language
        device_types = self._load_device_types(language)
        
        for device_type, keywords in device_types.items():
            if any(keyword in device_reference_lower for keyword in keywords):
                # Find devices of this type
                matching_devices = [d for d in available_devices 
                                  if d.get("type", "").lower() == device_type]
                
                if matching_devices:
                    # If only one device of this type, return it
                    if len(matching_devices) == 1:
                        return EntityResolutionResult(
                            resolved_value=matching_devices[0],
                            original_value=device_reference,
                            confidence=0.8,
                            resolution_type="contextual",
                            metadata={"match_type": "type_inference", "device_type": device_type}
                        )
                    else:
                        # Multiple devices, return list
                        return EntityResolutionResult(
                            resolved_value=matching_devices,
                            original_value=device_reference,
                            confidence=0.6,
                            resolution_type="contextual",
                            metadata={"match_type": "type_multiple", "device_type": device_type, 
                                    "count": len(matching_devices)}
                        )
        
        return None


class LocationEntityResolver:
    """Resolver for location-related entities using client context"""
    
    def __init__(self, asset_loader=None):
        self.asset_loader = asset_loader
        self.logger = logging.getLogger(f"{__name__}.LocationEntityResolver")
        self._assets_warned = False  # warn-once guard for missing/empty localization assets

    def _warn_assets_once(self, message: str) -> None:
        """Log a degradation warning at most once per resolver (avoid per-request log spam)."""
        if not self._assets_warned:
            self.logger.warning(message)
            self._assets_warned = True

    def _load_location_keywords(self, language: str = "en") -> Dict[str, List[str]]:
        """Load location keywords from localization files.

        Best-effort: returns {} (with a one-time warning) when the asset loader isn't wired yet or
        the data is missing/empty, rather than raising. resolve() then skips "here"-inference and
        degrades to exact/fuzzy room matching — a location utterance must never abort the request
        just because deferred asset coordination hasn't run (QUAL-11 P0 #4)."""
        if not self.asset_loader:
            self._warn_assets_once(
                "LocationEntityResolver: asset loader not wired — skipping 'here'-inference "
                "(exact/fuzzy room matching still works)."
            )
            return {}

        try:
            room_localization = self.asset_loader.localizations.get("rooms", {})
            room_data = room_localization.get(language, {})

            if not room_data and language != "en":
                # Fallback to English
                room_data = room_localization.get("en", {})

            room_keywords = room_data.get("room_keywords", {}) if room_data else {}
            if not room_keywords:
                self._warn_assets_once(
                    f"LocationEntityResolver: no location keywords for language '{language}' "
                    f"in assets/localization/rooms/ — skipping 'here'-inference."
                )
                return {}

            return room_keywords
        except Exception as e:
            self._warn_assets_once(
                f"LocationEntityResolver: failed to load location keywords from localization files: {e} — "
                f"skipping 'here'-inference."
            )
            return {}
    
    
    async def resolve(self, location_reference: str, context: UnifiedConversationContext) -> Optional[EntityResolutionResult]:
        """
        Resolve location reference using client and room context.
        """
        location_lower = location_reference.lower().strip()
        
        # 1. Current room inference using localization files
        current_room = context.get_room_name()
        # Determine language from context
        language = context.language
        location_keywords = self._load_location_keywords(language)
        here_keywords = location_keywords.get("here_indicators", [])
        
        if current_room and any(keyword in location_lower for keyword in here_keywords):
            return EntityResolutionResult(
                resolved_value=current_room,
                original_value=location_reference,
                confidence=0.9,
                resolution_type="contextual",
                metadata={"match_type": "current_room", "room_name": current_room}
            )
        
        # 2. Room name matching from client metadata
        available_rooms = context.client_metadata.get("available_rooms", [])
        if available_rooms:
            # Exact match
            for room in available_rooms:
                if isinstance(room, dict):
                    room_name = room.get("name", "").lower()
                else:
                    room_name = str(room).lower()
                
                if room_name == location_lower:
                    return EntityResolutionResult(
                        resolved_value=room,
                        original_value=location_reference,
                        confidence=1.0,
                        resolution_type="exact",
                        metadata={"match_type": "room_name"}
                    )
            
            # Fuzzy match using rapidfuzz
            room_names = [r.get("name", str(r)) if isinstance(r, dict) else str(r) 
                        for r in available_rooms]
            best_match = process.extractOne(location_reference, room_names, scorer=fuzz.ratio)
            
            if best_match and best_match[1] >= 75:
                return EntityResolutionResult(
                    resolved_value=best_match[0],
                    original_value=location_reference,
                    confidence=best_match[1] / 100.0,
                    resolution_type="fuzzy",
                    metadata={"match_type": "room_fuzzy", "similarity": best_match[1]}
                )
        
        return None


class TemporalEntityResolver:
    """Resolver for time and date entities"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TemporalEntityResolver")
    
    async def resolve(self, temporal_reference: str, context: UnifiedConversationContext) -> Optional[EntityResolutionResult]:
        """
        Resolve temporal references using context and patterns.
        """
        temporal_lower = temporal_reference.lower().strip()
        
        # Time pattern matching
        time_pattern = re.search(r'(\d{1,2}):(\d{2})', temporal_reference)
        if time_pattern:
            hours, minutes = time_pattern.groups()
            return EntityResolutionResult(
                resolved_value={"hours": int(hours), "minutes": int(minutes)},
                original_value=temporal_reference,
                confidence=0.95,
                resolution_type="exact",
                metadata={"match_type": "time_pattern", "format": "HH:MM"}
            )
        
        # Duration (value + time unit) via the shared bilingual parser — the one place time units live.
        parsed = parse_duration(temporal_lower)
        if parsed:
            value, unit = parsed
            return EntityResolutionResult(
                resolved_value={"value": value, "unit": unit},
                original_value=temporal_reference,
                confidence=0.9,
                resolution_type="exact",
                metadata={"match_type": "duration_pattern", "unit": unit}
            )
        
        # Relative time references (Russian + English)
        relative_times = {
            # Russian terms
            "сейчас": {"relative": "now", "offset": 0},
            "потом": {"relative": "future", "offset": None},
            "позже": {"relative": "future", "offset": None},
            "скоро": {"relative": "future", "offset": "short"},
            "вскоре": {"relative": "future", "offset": "short"},
            "сегодня": {"relative": "today", "offset": 0},
            "завтра": {"relative": "tomorrow", "offset": 1},
            "вчера": {"relative": "yesterday", "offset": -1},
            # English terms
            "now": {"relative": "now", "offset": 0},
            "later": {"relative": "future", "offset": None},
            "soon": {"relative": "future", "offset": "short"},
            "today": {"relative": "today", "offset": 0},
            "tomorrow": {"relative": "tomorrow", "offset": 1},
            "yesterday": {"relative": "yesterday", "offset": -1}
        }
        
        for keyword, time_info in relative_times.items():
            if keyword in temporal_lower:
                return EntityResolutionResult(
                    resolved_value=time_info,
                    original_value=temporal_reference,
                    confidence=0.8,
                    resolution_type="contextual",
                    metadata={"match_type": "relative_time", "keyword": keyword}
                )
        
        return None


class QuantityEntityResolver:
    """Resolver for quantity and number entities"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.QuantityEntityResolver")
    
    async def resolve(self, quantity_reference: str, context: UnifiedConversationContext) -> Optional[EntityResolutionResult]:
        """
        Resolve quantity references with unit inference.
        """
        quantity_lower = quantity_reference.lower().strip()
        
        # Number extraction
        number_pattern = re.search(r'(\d+(?:\.\d+)?)', quantity_reference)
        if number_pattern:
            number = float(number_pattern.group(1))
            
            # Unit inference (Russian + English). Non-time units (percent/degrees) stay here as the
            # nucleus of the future general unit-of-measurement layer; the TIME units reuse the ONE
            # shared surface table (no duplicate sec/min/hour lists).
            unit_patterns = {
                "percent": [
                    # Russian
                    "%", "процент", "процента", "процентов",
                    # English
                    "percent", "percentage"
                ],
                "degrees": [
                    # Russian
                    "градус", "градуса", "градусов", "°",
                    # English
                    "degrees", "degree"
                ],
                **{u: list(surfaces) for u, (_mult, surfaces) in TIME_UNITS.items()},
                "times": [
                    # Russian
                    "раз", "раза", "x",
                    # English
                    "times", "time", "x"
                ],
                "count": [
                    # Russian
                    "штук", "штука", "штуки", "элемент", "элемента", "элементов",
                    "предмет", "предмета", "предметов", "вещь", "вещи", "вещей",
                    # English
                    "items", "things", "pieces"
                ]
            }
            
            inferred_unit = "count"  # default
            for unit, keywords in unit_patterns.items():
                if any(keyword in quantity_lower for keyword in keywords):
                    inferred_unit = unit
                    break
            
            return EntityResolutionResult(
                resolved_value={"value": number, "unit": inferred_unit},
                original_value=quantity_reference,
                confidence=0.85,
                resolution_type="exact",
                metadata={"match_type": "number_with_unit", "inferred_unit": inferred_unit}
            )
        
        # Word numbers (Russian + English)
        word_numbers = {
            # Russian numbers
            "ноль": 0, "один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2, 
            "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, 
            "восемь": 8, "девять": 9, "десять": 10,
            # English numbers
            "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "none": 0, "a": 1, "an": 1
        }
        
        for word, number in word_numbers.items():
            if word in quantity_lower:
                return EntityResolutionResult(
                    resolved_value={"value": number, "unit": "count"},
                    original_value=quantity_reference,
                    confidence=0.8,
                    resolution_type="contextual",
                    metadata={"match_type": "word_number", "word": word}
                )
        
        return None 