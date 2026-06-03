"""QUAL-15 — LLM offline foundation: real fallback chain + console floor.

Verifies the component-level logic without network: the provider chain is default → fallback_providers
→ console (terminal); `is_available()` excludes the console stub (so the conversation handler still
prefers its own template over a stub); the console floor returns a localized message; and
generate_response never raises offline.
"""
from irene.components.llm_component import LLMComponent
from irene.providers.llm.console import ConsoleLLMProvider


class _FakeProvider:
    is_stub = False

    def __init__(self, name, fail=False):
        self._name = name
        self._fail = fail

    async def chat_completion(self, messages, **kwargs):
        if self._fail:
            raise RuntimeError(f"{self._name} offline")
        return f"{self._name}-response"


def _component(providers, default, fallback):
    c = LLMComponent()
    c.providers = providers
    c.default_provider = default
    c.fallback_providers = fallback
    c.initialized = True
    return c


def test_provider_chain_order_and_console_terminal():
    c = _component(
        {"deepseek": _FakeProvider("deepseek"), "console": ConsoleLLMProvider({})},
        default="deepseek", fallback=["console"])
    assert c._provider_chain() == ["deepseek", "console"]
    # console is appended as terminal even if not in the configured chain
    c2 = _component({"deepseek": _FakeProvider("deepseek"), "console": ConsoleLLMProvider({})},
                    default="deepseek", fallback=[])
    assert c2._provider_chain() == ["deepseek", "console"]


def test_is_available_excludes_console_stub():
    only_console = _component({"console": ConsoleLLMProvider({})}, "deepseek", ["console"])
    real = _component({"deepseek": _FakeProvider("deepseek"), "console": ConsoleLLMProvider({})},
                      "deepseek", ["console"])
    # async is_available
    import asyncio
    assert asyncio.get_event_loop().run_until_complete(only_console.is_available()) is False
    assert asyncio.get_event_loop().run_until_complete(real.is_available()) is True


async def test_generate_response_falls_through_to_console_no_raise():
    # the real provider fails (offline) → chain falls to console → localized floor message, no raise
    console = ConsoleLLMProvider({})
    console._responses.update({"ru": "недоступна", "en": "unavailable"})
    c = _component({"deepseek": _FakeProvider("deepseek", fail=True), "console": console},
                   "deepseek", ["console"])
    c._messages_loaded = True  # skip asset load in the unit test
    out = await c.generate_response([{"role": "user", "content": "hi"}], language="en")
    assert out == "unavailable"


async def test_generate_response_uses_real_provider_when_available():
    c = _component({"deepseek": _FakeProvider("deepseek"), "console": ConsoleLLMProvider({})},
                   "deepseek", ["console"])
    c._messages_loaded = True
    assert await c.generate_response([{"role": "user", "content": "hi"}]) == "deepseek-response"
