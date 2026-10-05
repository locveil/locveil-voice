"""ARCH-18 PR-3 — AudioNegotiator (config-derived canonical + transform-once at the boundary)."""
import tomllib
from pathlib import Path

import pytest

from locveil_voice.config.models import CoreConfig
from locveil_voice.core.audio_negotiator import AudioNegotiator
from locveil_voice.intents.models import AudioData

CONFIG_DIR = Path("config")


@pytest.mark.parametrize("name", [p.stem for p in Path("config").glob("*.toml")])
def test_every_config_derives_a_canonical(name):
    """No shipped config is an infeasible audio negotiation (would be fatal at startup)."""
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / f"{name}.toml", "rb")))
    neg = AudioNegotiator.from_config(cfg)
    assert neg.canonical.rate == 16000          # all consumers (asr/vt/vad) are 16 kHz
    assert neg.canonical.channels == 1


async def test_to_canonical_downsamples_then_noops():
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "config-master.toml", "rb")))  # mic 44.1k
    neg = AudioNegotiator.from_config(cfg)

    # 44.1k frame -> resampled to 16k
    pcm = b"\x00\x00" * 4410
    out = await neg.to_canonical(AudioData(data=pcm, timestamp=0.0, sample_rate=44100, channels=1))
    assert out.sample_rate == 16000

    # already-canonical frame -> returned unchanged (same object)
    canon_frame = AudioData(data=b"\x00\x00" * 1600, timestamp=0.0, sample_rate=16000, channels=1)
    assert await neg.to_canonical(canon_frame) is canon_frame


class _MockConsumer:
    """A consumer provider declaring an arbitrary audio contract."""
    def __init__(self, rates):
        from locveil_voice.utils.audio_negotiation import AudioContract
        self._c = AudioContract(list(rates), rates[0], ["pcm16"], "pcm16", 1)

    def audio_contract(self):
        return self._c


def test_from_pipeline_uses_provider_declared_contracts():
    from locveil_voice.providers.vad.energy import EnergyVADProvider
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "config-master.toml", "rb")))  # mic 44.1k
    # VAD provider declares 16 kHz; with asr/vt disabled the canonical comes purely from the provider.
    cfg.components.asr = False
    cfg.components.voice_trigger = False
    neg = AudioNegotiator.from_pipeline(cfg, vad_provider=EnergyVADProvider({}))
    assert neg.canonical.rate == 16000


def test_provider_capability_used_when_config_rate_unset():
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "config-master.toml", "rb")))  # mic 44.1k
    cfg.vad.enabled = False
    cfg.components.asr = False
    cfg.components.voice_trigger = True
    cfg.voice_trigger.sample_rate = None              # no operator override → use the provider's capability
    neg = AudioNegotiator.from_pipeline(cfg, wake_provider=_MockConsumer([8000]))
    assert neg.canonical.rate == 8000                 # the provider's declared rate, not a config number


def test_authoritative_config_overrides_provider_capability():
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "config-master.toml", "rb")))
    cfg.vad.enabled = False
    cfg.components.asr = False
    cfg.components.voice_trigger = True
    cfg.voice_trigger.sample_rate = 16000             # authoritative override
    neg = AudioNegotiator.from_pipeline(cfg, wake_provider=_MockConsumer([8000]))
    assert neg.canonical.rate == 16000                # operator pin wins over the provider's 8 kHz


def test_source_uses_enabled_input_not_irrelevant_mic_config():
    # Satellite/WS-primary: mic disabled, web enabled. The source must be the WS delivery (16 kHz),
    # NOT the (irrelevant) mic config — else a 16 kHz consumer would look infeasible.
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "config-master.toml", "rb")))
    cfg.inputs.microphone = False
    cfg.inputs.web = True
    cfg.inputs.microphone_config.sample_rate = 8000   # irrelevant — mic is disabled
    neg = AudioNegotiator.from_config(cfg)            # 16 kHz consumers + 16 kHz WS source → feasible
    assert neg.canonical.rate == 16000


def test_config_pin_is_honored_and_infeasible_pin_is_fatal():
    from locveil_voice.utils.audio_negotiation import AudioNegotiationError
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "config-master.toml", "rb")))  # mic 44.1k
    cfg.audio.canonical_rate = 16000                  # feasible pin
    assert AudioNegotiator.from_config(cfg).canonical.rate == 16000

    cfg2 = CoreConfig(**tomllib.load(open(CONFIG_DIR / "standalone-x86_64.toml", "rb")))   # mic 16k
    cfg2.audio.canonical_rate = 48000                 # exceeds the capture → fatal
    with pytest.raises(AudioNegotiationError):
        AudioNegotiator.from_config(cfg2)


async def test_to_canonical_downmixes_stereo_to_mono():
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "standalone-x86_64.toml", "rb")))    # canonical 16k/mono
    neg = AudioNegotiator.from_config(cfg)
    # 16 kHz stereo frame (interleaved int16, 2 ch) → downmixed to mono, rate already canonical
    stereo = b"\x10\x00\x20\x00" * 100                # 100 stereo frames -> 200 int16
    out = await neg.to_canonical(AudioData(data=stereo, timestamp=0.0, sample_rate=16000, channels=2))
    assert out.channels == 1
    assert len(out.data) == len(stereo) // 2          # mono has half the samples


def test_output_sink_defaults_to_cd():
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "standalone-x86_64.toml", "rb")))
    neg = AudioNegotiator.from_config(cfg)                 # no audio_provider → CD default
    assert max(neg.output_sink.supported_rates) == 44100
    assert neg.output_sink.channels == 2


def test_output_sink_audio_override():
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "standalone-x86_64.toml", "rb")))
    cfg.audio.output_rate = 22050
    cfg.audio.output_channels = 1
    neg = AudioNegotiator.from_config(cfg)
    assert max(neg.output_sink.supported_rates) == 22050
    assert neg.output_sink.channels == 1


async def test_to_sink_passes_through_when_below_device():
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "standalone-x86_64.toml", "rb")))
    neg = AudioNegotiator.from_config(cfg)                 # CD sink (44.1k/stereo)
    # a 22 kHz mono TTS frame is <= the sink → played as-is (any device plays lower)
    frame = AudioData(data=b"\x00\x00" * 220, timestamp=0.0, sample_rate=22050, channels=1)
    assert await neg.to_sink(frame) is frame


async def test_to_sink_downsamples_when_above_device():
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "standalone-x86_64.toml", "rb")))
    cfg.audio.output_rate = 16000                          # device max 16 kHz
    neg = AudioNegotiator.from_config(cfg)
    out = await neg.to_sink(AudioData(data=b"\x00\x00" * 480, timestamp=0.0, sample_rate=48000, channels=1))
    assert out.sample_rate == 16000                        # conformed DOWN to the device


async def test_to_sink_downmixes_stereo_for_mono_sink():
    from locveil_voice.utils.audio_negotiation import AudioContract
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "standalone-x86_64.toml", "rb")))
    neg = AudioNegotiator.from_config(cfg)
    mono_sink = AudioContract([44100], 44100, ["pcm16"], "pcm16", 1)
    stereo = AudioData(data=b"\x10\x00\x20\x00" * 100, timestamp=0.0, sample_rate=44100, channels=2)
    out = await neg.to_sink(stereo, mono_sink)
    assert out.channels == 1


def test_infeasible_config_is_fatal():
    """A consumer needing a higher rate than the mic can deliver fails loudly at from_config."""
    from locveil_voice.utils.audio_negotiation import AudioNegotiationError
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "standalone-x86_64.toml", "rb")))
    cfg.inputs.microphone_config.sample_rate = 16000
    cfg.components.asr = True
    cfg.asr.sample_rate = 48000          # would require upsampling from the 16 kHz mic
    with pytest.raises(AudioNegotiationError):
        AudioNegotiator.from_config(cfg)


# --- BUG-50: exact conversion to a remote device's registered format ----------------------------

def _device(rate, channels=1):
    from locveil_voice.utils.audio_negotiation import AudioContract
    return AudioContract([rate], rate, ["pcm16"], "pcm16", channels)


def _negotiator():
    from locveil_voice.utils.audio_negotiation import CanonicalFormat
    return AudioNegotiator(CanonicalFormat(16000, "pcm16", 1))


async def test_to_device_returns_the_same_object_when_nothing_needs_converting():
    frame = AudioData(data=b"\x00\x00" * 220, timestamp=0.0, sample_rate=22050, channels=1)
    assert await _negotiator().to_device(frame, _device(22050)) is frame


@pytest.mark.parametrize("source,target", [(16000, 22050), (16000, 48000), (48000, 22050), (22050, 16000)])
async def test_to_device_converts_the_rate_both_ways(source, target):
    frame = AudioData(data=b"\x01\x02" * source, timestamp=0.0, sample_rate=source, channels=1)  # 1 s
    out = await _negotiator().to_device(frame, _device(target))
    assert (out.sample_rate, out.channels) == (target, 1)
    assert abs(len(out.data) / 2 - target) <= 2            # still one second


async def test_to_device_converts_the_channel_count_both_ways():
    mono = AudioData(data=b"\x10\x00\x20\x00" * 50, timestamp=0.0, sample_rate=22050, channels=1)
    stereo = await _negotiator().to_device(mono, _device(22050, channels=2))
    assert stereo.channels == 2 and len(stereo.data) == 2 * len(mono.data)
    assert stereo.data[:8] == b"\x10\x00\x10\x00\x20\x00\x20\x00"
    back = await _negotiator().to_device(stereo, _device(22050, channels=1))
    assert back.channels == 1 and back.data == mono.data


async def test_to_device_raises_when_the_result_is_not_the_devices_format(monkeypatch):
    """A resample that fails returns its input; the negotiator must notice, not pass it on."""
    from locveil_voice.utils import audio_helpers
    from locveil_voice.utils.audio_negotiation import AudioNegotiationError

    async def _broken(audio_bytes, source_rate, target_rate, channels, method):
        raise RuntimeError("no resampler")
    monkeypatch.setattr(audio_helpers.AudioTranscoder, "_resample_bytes", staticmethod(_broken))
    audio_helpers.AudioTranscoder.clear_cache()
    frame = AudioData(data=b"\x07\x00" * 1600, timestamp=0.0, sample_rate=16000, channels=1)
    with pytest.raises(AudioNegotiationError):
        await _negotiator().to_device(frame, _device(22050))


@pytest.mark.parametrize("source,target,channels", [(16000, 22050, 1), (48000, 16000, 1), (16000, 22050, 2)])
def test_linear_resample_needs_no_numpy_and_keeps_duration_and_shape(source, target, channels):
    """The last-resort resampler (stdlib only — the armv7 image has no numpy): the output lasts
    as long as the input, a ramp stays a ramp, and channels stay separate."""
    import array
    frames = source // 10                                    # 100 ms
    ramp = array.array("h")
    for n in range(frames):
        for ch in range(channels):
            ramp.append((n if ch == 0 else -n) * 3)          # channel 1 mirrors channel 0
    from locveil_voice.utils.audio_helpers import AudioTranscoder
    out = array.array("h")
    out.frombytes(AudioTranscoder._linear_resample_pcm16(ramp.tobytes(), source, target, channels))
    assert len(out) == (frames * target // source) * channels
    left = out[0::channels]
    assert list(left) == sorted(left) and left[0] == 0 and abs(left[-1] - (frames - 1) * 3) <= 3
    if channels == 2:
        assert all(abs(a + b) <= 1 for a, b in zip(left, out[1::2]))   # still mirrored: not mixed


async def test_basic_resample_fallback_resamples_without_numpy(monkeypatch):
    """BUG-50: with numpy missing this fallback returned its INPUT, and the caller relabelled
    it with the target rate — audio at the wrong speed on the numpy-free armv7 image."""
    import builtins
    from locveil_voice.utils.audio_helpers import AudioTranscoder
    real_import = builtins.__import__

    def _no_numpy(name, *args, **kwargs):
        if name == "numpy" or name.startswith("numpy."):
            raise ImportError("numpy is not installed on this image")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", _no_numpy)
    pcm = b"\x01\x02" * 1600                                 # 100 ms at 16 kHz
    out = await AudioTranscoder._basic_resample_bytes(pcm, 16000, 22050, 1)
    assert len(out) == 2 * (1600 * 22050 // 16000) and out != pcm


async def test_resample_cache_never_hands_one_utterance_the_audio_of_another():
    """BUG-50: the resampling cache keyed on the first 1 KB only. Two utterances that START
    alike — leading silence — and differ later got each other's audio."""
    from locveil_voice.utils.audio_helpers import AudioTranscoder
    silence = b"\x00\x00" * 1024                              # an identical first 2 KB
    first = AudioData(data=silence + b"\x10\x10" * 4000, timestamp=0.0, sample_rate=16000, channels=1)
    second = AudioData(data=silence + b"\x70\x70" * 8000, timestamp=0.0, sample_rate=16000, channels=1)
    out_first = await AudioTranscoder.resample_audio_data(first, 22050)
    out_second = await AudioTranscoder.resample_audio_data(second, 22050)
    assert len(out_second.data) > len(out_first.data)          # its own length…
    assert out_second.data[-200:] != out_first.data[-200:]     # …and its own content
