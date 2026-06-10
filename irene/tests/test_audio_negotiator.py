"""ARCH-18 PR-3 — AudioNegotiator (config-derived canonical + transform-once at the boundary)."""
import tomllib
from pathlib import Path

import pytest

from irene.config.models import CoreConfig
from irene.workflows.audio_negotiator import AudioNegotiator
from irene.intents.models import AudioData

CONFIG_DIR = Path("configs")


@pytest.mark.parametrize("name", [p.stem for p in Path("configs").glob("*.toml")])
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


def test_infeasible_config_is_fatal():
    """A consumer needing a higher rate than the mic can deliver fails loudly at from_config."""
    from irene.utils.audio_negotiation import AudioNegotiationError
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "development.toml", "rb")))
    cfg.inputs.microphone_config.sample_rate = 16000
    cfg.asr.enabled = True
    cfg.asr.sample_rate = 48000          # would require upsampling from the 16 kHz mic
    with pytest.raises(AudioNegotiationError):
        AudioNegotiator.from_config(cfg)
