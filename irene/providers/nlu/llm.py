"""
LLM NLU Provider (QUAL-50).

A **last-resort** NLU cascade fallback: when the deterministic providers (keyword matcher, and
spaCy on 64-bit) don't recognize an utterance, ask the LLM to classify it into a known intent and
extract its parameters — recovering fuzzy *commands* the pattern layers miss.

It behaves like every other NLU provider: `recognize_with_parameters` returns a **plain `Intent`**
{name, entities, confidence, raw_text} or `None` (abstain). There is no special structured output and
no catalog grounding here — entity *grounding* is the shared `ContextualEntityResolver` applied
downstream to every provider's Intent (so this provider emits **raw** spans like "kitchen"/"lamp", not
canonical IDs). The intent taxonomy + parameter specs come from the **same donations** the keyword
matcher uses — there is no separate NLU model.

The LLM is reached through the injected `LLMPort` (set via `set_llm_component`, mirroring the
conversation handler's QUAL-24 injection). With no LLM configured / offline / unparseable reply, the
provider abstains and the cascade falls through to `conversation.general` — offline still works.

Confidence is **derived** (not the LLM's self-rating) and written to the standard `Intent.confidence`:
abstain unless intent ∈ donation set [hard gate] and the LLM quotes an **evidence span** present in the
text [anti-hallucination]; otherwise `0.7 + 0.25 × (required-param coverage)`. A command with a missing
required param therefore still passes the cascade threshold (so the handler's QUAL-30 `_clarify`
elicits the missing value); only an unknown intent / no-evidence reply abstains.

Prompt wording is a deliberate first cut — QUAL-51 is the prompt-tightening session.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from .base import NLUProvider
from ...intents.models import Intent
from ...intents.context_models import UnifiedConversationContext
from ...intents.ports import LLMPort
from ...core.donations import ParameterSpec, KeywordDonation

logger = logging.getLogger(__name__)


class LLMNLUProvider(NLUProvider):
    """LLM-backed NLU classifier — cascade fallback after keyword/spaCy (QUAL-50)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # The LLM capability port, injected post-init by NLUComponent (None until then / when no LLM).
        self.llm_component: Optional[LLMPort] = None
        # Optional routing: pin a provider/model, else the LLM component's default chain is used.
        self.model: Optional[str] = config.get("model")
        self.provider: Optional[str] = config.get("provider")
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        # Prompt budget knobs (kept small; QUAL-51 tightens). The catalog is NOT in the prompt — only
        # the intent taxonomy from donations — so this stays compact and budget-aware.
        self.max_phrases_per_intent = config.get("max_phrases_per_intent", 3)
        # intent_name -> {"phrases": [...], "parameters": [ParameterSpec, ...]}
        self._intents: Dict[str, Dict[str, Any]] = {}

    def get_provider_name(self) -> str:
        return "llm"

    def set_llm_component(self, llm_component: Optional[LLMPort]) -> None:
        """Inject the LLM capability port (QUAL-50; mirrors the conversation handler's QUAL-24 setter).
        Called by NLUComponent.post_initialize_coordination. None ⇒ the provider abstains at runtime."""
        self.llm_component = llm_component

    async def is_available(self) -> bool:
        """Always loadable — it abstains at call time if no LLM is injected / available. (Keeping it in
        the cascade with no LLM is harmless: every `recognize` returns None and the cascade continues.)"""
        return True

    async def _do_initialize(self) -> None:
        """No heavy init — the taxonomy is loaded later from donations, the LLM is injected later."""
        if not hasattr(self, "parameter_specs") or self.parameter_specs is None:
            self.parameter_specs = {}

    async def _initialize_from_donations(self, keyword_donations: List[KeywordDonation]) -> None:
        """Build the intent taxonomy + parameter specs from the SAME donations the keyword matcher uses."""
        self._intents = {}
        self.parameter_specs = {}
        if not keyword_donations:
            logger.warning("LLMNLUProvider: no donations — provider will abstain on every utterance")
            return
        for donation in keyword_donations:
            intent_name = donation.intent
            self._intents[intent_name] = {
                "phrases": list(donation.phrases or [])[: self.max_phrases_per_intent],
                "parameters": list(donation.parameters or []),
            }
            self.parameter_specs[intent_name] = donation.parameters
        logger.info("LLMNLUProvider initialized with %d intents from donations", len(self._intents))

    # --- recognition -------------------------------------------------------------------------------

    async def recognize(self, text: str, context: UnifiedConversationContext) -> Optional[Intent]:
        """Single-shot classify + extract (one LLM call). Delegates to recognize_with_parameters so the
        two entrypoints never double-call the model."""
        return await self.recognize_with_parameters(text, context)

    async def recognize_with_parameters(self, text: str,
                                        context: UnifiedConversationContext) -> Optional[Intent]:
        llm = self.llm_component
        if llm is None or not self._intents:
            return None
        try:
            if not await llm.is_available():
                return None
        except Exception:
            return None

        language = getattr(context, "language", None) or "ru"
        messages = [
            {"role": "system", "content": self._build_system_prompt(language)},
            {"role": "user", "content": text},
        ]
        try:
            raw = await llm.generate_response(messages=messages, model=self.model, provider=self.provider)
        except Exception as e:  # never break the cascade on an LLM hiccup — abstain
            logger.debug("LLMNLUProvider: LLM call failed, abstaining: %s", e)
            return None

        parsed = self._parse_response(raw)
        if not parsed:
            return None

        intent_name = parsed.get("intent")
        if not isinstance(intent_name, str) or intent_name not in self._intents:
            return None  # hard gate: only a known donation intent counts

        evidence = parsed.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip() \
                or evidence.strip().lower() not in text.lower():
            return None  # anti-hallucination: the LLM must quote a span that is actually in the text

        entities = self._collect_entities(intent_name, parsed.get("params"))
        confidence = self._derive_confidence(intent_name, entities)
        domain, _, action = intent_name.partition(".")
        return Intent(
            name=intent_name,
            entities=entities,
            confidence=confidence,
            raw_text=text,
            domain=domain or None,
            action=action or None,
        )

    def _collect_entities(self, intent_name: str, raw_params: Any) -> Dict[str, Any]:
        """Keep only params declared for this intent (canonicalizing aliases); drop hallucinated keys.
        Values stay RAW — the shared ContextualEntityResolver grounds them downstream."""
        specs: List[ParameterSpec] = self.parameter_specs.get(intent_name, [])
        canonical: Dict[str, str] = {}
        for p in specs:
            canonical[p.name] = p.name
            for alias in p.aliases:
                canonical[alias] = p.name
        entities: Dict[str, Any] = {}
        if isinstance(raw_params, dict):
            for key, value in raw_params.items():
                name = canonical.get(key)
                if name is not None and value not in (None, "", []):
                    entities[name] = value
        return entities

    def _derive_confidence(self, intent_name: str, entities: Dict[str, Any]) -> float:
        """0.7 (≥ threshold) + 0.25 × fraction of required params resolved. A command missing a required
        param still clears the threshold → the handler clarifies it; full coverage / a query → ~0.95."""
        specs: List[ParameterSpec] = self.parameter_specs.get(intent_name, [])
        required = [p.name for p in specs if p.required]
        if not required:
            return 0.95
        resolved = sum(1 for name in required if entities.get(name) not in (None, "", []))
        return round(0.7 + 0.25 * (resolved / len(required)), 3)

    # --- prompt + parsing --------------------------------------------------------------------------

    def _build_system_prompt(self, language: str) -> str:
        """List the intent taxonomy (names + a few sample phrases + params) and ask for a compact JSON
        verdict. Deliberately minimal — QUAL-51 is the tightening session."""
        lines = [
            "You are an intent classifier for a voice assistant. Choose AT MOST ONE intent from the list "
            "below that matches the user's message, and extract its parameters.",
            "",
            "Intents (name — sample phrases — parameters):",
        ]
        for name, info in self._intents.items():
            phrases = ", ".join(info["phrases"]) if info["phrases"] else "—"
            params = ", ".join(self._format_param(p) for p in info["parameters"]) or "none"
            lines.append(f"- {name} — {phrases} — params: {params}")
        lines += [
            "",
            "Rules:",
            "- Use ONLY an intent name from the list. If none clearly fits, return intent \"none\".",
            "- Extract parameter values as RAW spans copied from the message (do not normalize or invent).",
            "- 'evidence' MUST be a verbatim substring of the user's message that justifies the intent.",
            "- Reply with ONLY a compact JSON object, no prose, no markdown:",
            '  {"intent": "<name|none>", "params": {"<param>": "<raw value>"}, "evidence": "<span>"}',
        ]
        return "\n".join(lines)

    @staticmethod
    def _format_param(p: ParameterSpec) -> str:
        mark = "" if p.required else "?"
        return f"{p.name}{mark}:{p.type.value}"

    @staticmethod
    def _parse_response(text: Optional[str]) -> Optional[Dict[str, Any]]:
        """Best-effort parse of the LLM reply into a JSON object (provider-local; handles ```json fences
        and surrounding prose). Returns None on garbage / non-object — so the caller abstains."""
        if not text:
            return None
        s = text.strip()
        if s.startswith("```"):
            parts = s.split("```")
            if len(parts) >= 2:
                s = parts[1]
                if s.lstrip().lower().startswith("json"):
                    s = s.lstrip()[4:]
        s = s.strip()
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else None
        except (ValueError, TypeError):
            pass
        start, end = s.find("{"), s.rfind("}")
        if 0 <= start < end:
            try:
                obj = json.loads(s[start:end + 1])
                return obj if isinstance(obj, dict) else None
            except (ValueError, TypeError):
                return None
        return None

    # --- contract methods --------------------------------------------------------------------------

    async def extract_entities(self, text: str, intent_name: str) -> Dict[str, Any]:
        """Unused: the LLM extracts entities inline in `recognize_with_parameters` (one call)."""
        return {}

    async def extract_parameters(self, text: str, intent_name: str,
                                 parameter_specs: List[ParameterSpec]) -> Dict[str, Any]:
        """Unused: parameters are produced inline by the single classification call."""
        return {}

    def get_supported_intents(self) -> List[str]:
        return list(self._intents.keys())

    def get_supported_languages(self) -> List[str]:
        return ["ru", "en"]

    # --- asset / build metadata --------------------------------------------------------------------

    @classmethod
    def _get_default_extension(cls) -> str:
        return ""

    @classmethod
    def _get_default_directory(cls) -> str:
        return "llm_nlu"

    @classmethod
    def _get_default_credentials(cls) -> List[str]:
        return []  # credentials belong to the LLM provider it borrows, not here

    @classmethod
    def _get_default_cache_types(cls) -> List[str]:
        return ["runtime"]

    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, str]:
        return {}

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        return []  # reaches the LLM through the injected port; no extra deps

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        return {"linux.ubuntu": [], "linux.alpine": [], "macos": [], "windows": []}

    @classmethod
    def get_platform_support(cls) -> List[str]:
        return ["linux.ubuntu", "linux.alpine", "macos", "windows"]

    # get_supported_architectures: inherits the default (all three) — a cloud LLM is reached over HTTP,
    # so the classifier is armv7-viable (ARCH-24 T3); no override needed.
