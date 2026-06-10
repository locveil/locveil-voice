"""Audio negotiator — derives the canonical format from config and transforms capture to it once (ARCH-18 PR-3).

Built once at workflow init from the audio config (mic + the audio consumers: VAD / wake / ASR). It derives the
canonical encoding via `utils.audio_negotiation.derive_canonical` — **fatal at startup** if no canonical
satisfies everyone — and then `to_canonical()` transforms each captured frame to it **once** at the input
boundary (via `AudioTranscoder`), recording a trace event. Downstream stages see canonical audio.

The per-party contracts are derived from the *config* sample rates (the authoritative `[asr]`/`[voice_trigger]`
rates + the 16 kHz VAD requirement) — config is the declared contract.
"""

import logging
import time
from typing import Optional

from ..config.models import CoreConfig
from ..core.trace_context import TraceContext
from ..utils.audio_data import AudioData
from ..utils.audio_helpers import AudioTranscoder
from ..utils.audio_negotiation import AudioContract, CanonicalFormat, derive_canonical

logger = logging.getLogger(__name__)

_VAD_RATE = 16000  # the VAD providers are 16 kHz


class AudioNegotiator:
    """Holds the negotiated canonical format and transforms capture to it once."""

    def __init__(self, canonical: CanonicalFormat):
        self.canonical = canonical

    @classmethod
    def from_config(cls, config: CoreConfig) -> "AudioNegotiator":
        """Derive the canonical format; raises `AudioNegotiationError` (fatal) if none is feasible."""
        mc = config.inputs.microphone_config
        source = AudioContract([mc.sample_rate], mc.sample_rate, channels=mc.channels)

        consumers = []
        if config.asr.enabled and config.asr.sample_rate:
            consumers.append(AudioContract([config.asr.sample_rate], config.asr.sample_rate,
                                           channels=config.asr.channels))
        if config.voice_trigger.enabled and config.voice_trigger.sample_rate:
            consumers.append(AudioContract([config.voice_trigger.sample_rate], config.voice_trigger.sample_rate,
                                           channels=config.voice_trigger.channels))
        if config.vad.enabled:
            consumers.append(AudioContract([_VAD_RATE], _VAD_RATE))

        canonical = derive_canonical(source, consumers)
        logger.info("Audio canonical format negotiated: %dHz/%s/%dch (capture %dHz, %d consumer(s))",
                    canonical.rate, canonical.format, canonical.channels, mc.sample_rate, len(consumers))
        return cls(canonical)

    async def to_canonical(self, audio_data: AudioData,
                           trace_context: Optional[TraceContext] = None) -> AudioData:
        """Transform `audio_data` to the canonical format once. No-op if it already matches."""
        if audio_data.sample_rate == self.canonical.rate and audio_data.channels == self.canonical.channels:
            return audio_data
        if audio_data.channels != self.canonical.channels:
            logger.warning("Audio negotiator: channel mismatch %d->%d not converted (mono expected)",
                           audio_data.channels, self.canonical.channels)

        t0 = time.time()
        method = AudioTranscoder.get_optimal_conversion_path(audio_data.sample_rate, self.canonical.rate, "general")
        out = await AudioTranscoder.resample_audio_data(audio_data, self.canonical.rate, method)
        if trace_context:
            trace_context.record_stage(
                "audio_negotiate",
                {"sample_rate": audio_data.sample_rate, "channels": audio_data.channels},
                {"sample_rate": out.sample_rate, "channels": out.channels},
                {"canonical": f"{self.canonical.rate}Hz/{self.canonical.format}",
                 "method": getattr(method, "value", str(method))},
                (time.time() - t0) * 1000.0,
            )
        return out
