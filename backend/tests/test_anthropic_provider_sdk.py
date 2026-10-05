"""QUAL-87 — the Anthropic provider against the real `anthropic` SDK (1.x), with no network.

Nothing else in the suite reaches `providers/llm/anthropic.py`'s two SDK calls, which is how a
major SDK release could make both of them fail (type gate AND runtime) without a single test
noticing. These tests run the provider through the installed SDK and replace only the HTTP
transport: the request the SDK would have put on the wire is captured and read back, and the
reply it parses is a canned Messages API body.

What is held in place:
- the calls are accepted by the SDK's `messages.create` at all (1.x rejects unknown keywords);
- the fixed temperature (`_LLM_TEMPERATURE`) still reaches the API for the model families that
  accept sampling parameters — through `extra_body`, the SDK's route since the keyword left
  the signature — and is absent for every other model id, which would answer 400 to it;
- the system prompt travels in `system`, never as a message; the reply is the first text
  block, thinking blocks skipped; an API error is raised, not swallowed.
"""
import json
from typing import Any, Dict, List, get_args

import anthropic
import httpx2
import pytest
from anthropic.types import ModelParam

from locveil_voice.providers.llm.anthropic import (
    AnthropicLLMProvider, _SAMPLING_MODEL_FAMILIES, _sampling_extra_body,
)
from locveil_voice.providers.llm.base import _GENERIC_SYSTEM_FALLBACK, _LLM_TEMPERATURE

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# Ids that refuse sampling parameters (Opus 4.7 and later, every Claude 5 model), plus an id
# nobody has heard of yet: unknown must behave like "newer", never like "older".
_NO_SAMPLING_MODELS = [
    "claude-opus-4-7", "claude-opus-4-8", "claude-sonnet-5", "claude-sonnet-5-5",
    "claude-opus-5", "claude-opus-5-5", "claude-fable-5-1", "claude-some-future-model",
]


def test_every_listed_family_is_a_model_the_sdk_still_names():
    """The list must not outlive the models: a family the installed SDK no longer names in
    its model ids has been retired and is dead weight here."""
    known = set(get_args(get_args(ModelParam)[0]))
    assert known, "the SDK's ModelParam no longer carries a Literal of ids — re-anchor this test"
    assert set(_SAMPLING_MODEL_FAMILIES) <= known
    assert _DEFAULT_MODEL in known


def _reply(model: str, text: str = "  готово  ") -> Dict[str, Any]:
    return {
        "id": "msg_test", "type": "message", "role": "assistant", "model": model,
        "content": [
            {"type": "thinking", "thinking": "", "signature": "sig"},
            {"type": "text", "text": text},
        ],
        "stop_reason": "end_turn", "stop_sequence": None,
        "usage": {"input_tokens": 3, "output_tokens": 2},
    }


@pytest.fixture
def wire(monkeypatch):
    """The provider on the real SDK with a recording transport. Yields `(provider, sent)`;
    `sent` collects the JSON body of every request the SDK issued. Setting `sent.status`
    makes the fake API answer with that HTTP status instead of a message."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-a-real-one")

    class Sent(list):
        status = 200

    sent = Sent()

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/v1/messages"
        body = json.loads(request.content)
        sent.append(body)
        if sent.status != 200:
            return httpx2.Response(sent.status, json={
                "type": "error",
                "error": {"type": "invalid_request_error", "message": "refused by the test"},
            })
        return httpx2.Response(200, json=_reply(body["model"]))

    real_client = anthropic.AsyncAnthropic

    def client_on_mock_transport(**kwargs):
        return real_client(
            **kwargs, max_retries=0,
            http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler)),
        )

    # the provider imports the client class at call time, so this is the one it constructs
    monkeypatch.setattr(anthropic, "AsyncAnthropic", client_on_mock_transport)
    return AnthropicLLMProvider({}), sent


def test_suite_exercises_the_migrated_sdk_major():
    assert int(anthropic.__version__.split(".")[0]) >= 1


async def test_chat_completion_request_on_the_default_model(wire):
    provider, sent = wire
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": "Ты ассистент."},
        {"role": "user", "content": "включи свет"},
    ]
    assert await provider.chat_completion(messages) == "готово"

    (body,) = sent
    assert body["model"] == _DEFAULT_MODEL
    assert body["temperature"] == _LLM_TEMPERATURE == 0.0
    assert body["system"] == "Ты ассистент."
    assert body["messages"] == [{"role": "user", "content": "включи свет"}]
    assert body["max_tokens"] == 8192
    assert "top_p" not in body and "top_k" not in body


async def test_chat_completion_without_a_system_message_uses_the_fallback(wire):
    provider, sent = wire
    await provider.chat_completion([{"role": "user", "content": "привет"}])
    assert sent[0]["system"] == _GENERIC_SYSTEM_FALLBACK


async def test_enhance_text_request_on_the_default_model(wire):
    provider, sent = wire
    out = await provider.enhance_text("включи свед", task="asr_correction",
                                      system_prompt="Исправь ошибки распознавания.")
    assert out == "готово"

    (body,) = sent
    assert body["model"] == _DEFAULT_MODEL
    assert body["temperature"] == 0.0
    assert body["system"] == "Исправь ошибки распознавания."
    assert body["messages"] == [{"role": "user", "content": "включи свед"}]


@pytest.mark.parametrize("model", _NO_SAMPLING_MODELS)
async def test_models_that_refuse_sampling_parameters_get_none(wire, model):
    provider, sent = wire
    await provider.chat_completion([{"role": "user", "content": "привет"}], model=model)
    await provider.enhance_text("привет", model=model)
    assert [b["model"] for b in sent] == [model, model]
    for body in sent:
        assert not {"temperature", "top_p", "top_k"} & set(body)


# the SDK itself warns on a listed id that is scheduled for retirement — its signal, not ours
@pytest.mark.filterwarnings("ignore:The model:DeprecationWarning")
@pytest.mark.parametrize("family", _SAMPLING_MODEL_FAMILIES)
async def test_every_listed_family_keeps_the_fixed_temperature(wire, family):
    provider, sent = wire
    await provider.chat_completion([{"role": "user", "content": "привет"}], model=family)
    assert sent[0]["temperature"] == 0.0


def test_dated_ids_resolve_to_their_family_and_neighbours_do_not():
    assert _sampling_extra_body("claude-haiku-4-5-20251001") == {"temperature": 0.0}
    assert _sampling_extra_body("claude-sonnet-4-6") == {"temperature": 0.0}
    assert _sampling_extra_body("claude-opus-4-8") is None      # not a prefix-neighbour of 4-6/4-5
    assert _sampling_extra_body("") is None


async def test_an_api_error_is_raised_to_the_caller(wire):
    """The component's fallback chain relies on the provider failing loudly."""
    provider, sent = wire
    sent.status = 400
    with pytest.raises(anthropic.BadRequestError):
        await provider.chat_completion([{"role": "user", "content": "привет"}])
    with pytest.raises(anthropic.BadRequestError):
        await provider.enhance_text("привет")
    assert len(sent) == 2
