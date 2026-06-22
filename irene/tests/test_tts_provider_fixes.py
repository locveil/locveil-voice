"""Regression tests for the standalone-correctness TTS fixes (review CR-A4, CR-A8)."""
import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from irene.providers.tts.vosk import VoskTTSProvider
from irene.providers.tts.elevenlabs import ElevenLabsTTSProvider


def _arun(coro):
    return asyncio.run(coro)


class TestVoskTTSIsAvailable(unittest.TestCase):
    """CR-A4: is_available must probe the correct asset namespace so the model can download on first run."""

    def _provider(self, get_model_info):
        # Bypass __init__ (which wires the real asset manager); set only what is_available reads.
        p = object.__new__(VoskTTSProvider)
        p._available = True
        p.model_path = Path("/nonexistent/vosk_tts_model")  # not downloaded yet → take the asset-manager path
        p.asset_manager = SimpleNamespace(get_model_info=get_model_info)
        return p

    def test_queries_vosk_tts_namespace_not_vosk(self):
        calls = []

        def get_model_info(provider, model_id):
            calls.append((provider, model_id))
            return {"url": "..."} if (provider, model_id) == ("vosk_tts", "ru_multi") else None

        p = self._provider(get_model_info)
        # The bug queried ("vosk","tts") → None → is_available False → model never downloaded.
        self.assertTrue(_arun(p.is_available()))
        self.assertEqual(calls, [("vosk_tts", "ru_multi")])

    def test_unavailable_when_model_info_missing(self):
        p = self._provider(lambda provider, model_id: None)
        self.assertFalse(_arun(p.is_available()))


class TestElevenLabsSynthesizeRaises(unittest.TestCase):
    """CR-A8: synthesize_to_file must raise on failure (not silently write no file)."""

    def test_raises_runtimeerror_on_generation_failure(self):
        p = object.__new__(ElevenLabsTTSProvider)
        p.voice_id, p.stability, p.similarity_boost = "v", 0.5, 0.5
        p._generate_audio = AsyncMock(side_effect=Exception("quota exceeded"))
        out = Path("/tmp/irene_elevenlabs_should_not_exist.wav")
        if out.exists():
            out.unlink()
        with self.assertRaises(RuntimeError):
            _arun(p.synthesize_to_file("hi", out))
        self.assertFalse(out.exists())  # no phantom file left behind


if __name__ == "__main__":
    unittest.main()
