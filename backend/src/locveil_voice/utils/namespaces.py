"""Canonical entry-point namespace registry (ARCH-57).

ONE place that names the entry-point groups this codebase discovers from.
`backend/pyproject.toml` `[project.entry-points]` is the artifact of record; this
module mirrors it so runtime code never restates a group name as a scattered string
literal. Every component→namespace map, analyzer fallback list, and cross-family
search sweep derives from here — adding a provider family means one entry in
`PROVIDER_NAMESPACES` plus the pyproject group, nothing else.
"""

from typing import Dict, Tuple

# component config key -> provider entry-point group (the 8 provider families)
PROVIDER_NAMESPACES: Dict[str, str] = {
    "tts": "locveil_voice.providers.tts",
    "asr": "locveil_voice.providers.asr",
    "audio": "locveil_voice.providers.audio",
    "llm": "locveil_voice.providers.llm",
    "voice_trigger": "locveil_voice.providers.voice_trigger",
    "vad": "locveil_voice.providers.vad",
    "nlu": "locveil_voice.providers.nlu",
    "text_processor": "locveil_voice.providers.text_processor",
}

COMPONENTS_NAMESPACE = "locveil_voice.components"
WORKFLOWS_NAMESPACE = "locveil_voice.workflows"
INTENT_HANDLERS_NAMESPACE = "locveil_voice.intents.handlers"
INPUTS_NAMESPACE = "locveil_voice.inputs"

# Every group pyproject registers (outputs are composition-registered by ARCH-15 design
# and deliberately have NO entry-point group; the decorative runners group was deleted
# at ARCH-56 — runners launch via `python -m`, nothing discovers them).
ALL_NAMESPACES: Tuple[str, ...] = (
    *PROVIDER_NAMESPACES.values(),
    COMPONENTS_NAMESPACE,
    WORKFLOWS_NAMESPACE,
    INTENT_HANDLERS_NAMESPACE,
    INPUTS_NAMESPACE,
)
