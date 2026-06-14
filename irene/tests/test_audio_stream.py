"""ARCH-20: raw-PCM streaming-output helpers + contract wiring."""

import io
import wave

import pytest

from irene.utils.audio_stream import (
    collect_pcm,
    is_wav,
    iter_frames,
    parse_wav,
    width_to_alsa_format,
)


def _make_wav(pcm: bytes, rate: int, channels: int, width: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def test_is_wav():
    assert is_wav(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    assert not is_wav(b"\x00\x01\x02\x03raw pcm bytes")
    assert not is_wav(b"RIFF")  # too short


def test_width_to_alsa_format():
    assert width_to_alsa_format(1) == "U8"
    assert width_to_alsa_format(2) == "S16_LE"
    assert width_to_alsa_format(4) == "S32_LE"
    assert width_to_alsa_format(99) == "S16_LE"  # unknown -> safe default


def test_parse_wav_roundtrips_pcm_and_format():
    pcm = b"\x01\x00\x02\x00\x03\x00\x04\x00"  # 4 mono 16-bit frames
    wav = _make_wav(pcm, rate=16000, channels=1, width=2)
    out_pcm, rate, channels, width = parse_wav(wav)
    assert out_pcm == pcm
    assert (rate, channels, width) == (16000, 1, 2)


def test_iter_frames_blocks():
    pcm = b"abcdefg"
    assert list(iter_frames(pcm, 3)) == [b"abc", b"def", b"g"]
    with pytest.raises(ValueError):
        list(iter_frames(pcm, 0))


@pytest.mark.asyncio
async def test_collect_pcm_drains_stream():
    async def gen():
        yield b"aa"
        yield b"bb"
        yield b"cc"

    assert await collect_pcm(gen()) == b"aabbcc"


@pytest.mark.asyncio
async def test_console_provider_play_stream_pcm_contract():
    """Console provider accepts the raw-PCM keyword contract without error."""
    from irene.providers.audio.console import ConsoleAudioProvider

    provider = ConsoleAudioProvider({"simulate_timing": False})

    async def gen():
        yield b"\x00\x01" * 8

    await provider.play_stream(gen(), sample_rate=16000, channels=1, sample_width=2)


@pytest.mark.asyncio
async def test_component_play_stream_forwards_pcm_kwargs():
    """The component bridges bytes -> iterator and forwards (rate, channels, width)."""
    from irene.components.audio_component import AudioComponent

    captured = {}

    class _FakeProvider:
        async def play_stream(self, pcm_stream, *, sample_rate, channels, sample_width, **kwargs):
            captured["rate"] = sample_rate
            captured["channels"] = channels
            captured["width"] = sample_width
            captured["pcm"] = await collect_pcm(pcm_stream)

    component = AudioComponent()
    component.providers = {"fake": _FakeProvider()}
    component.default_provider = "fake"

    await component.play_stream(b"\x10\x20\x30\x40", sample_rate=22050, channels=2, sample_width=2)

    assert captured == {"rate": 22050, "channels": 2, "width": 2, "pcm": b"\x10\x20\x30\x40"}


def test_miniaudio_provider_metadata():
    """Miniaudio provider declares itself with no system dependencies (ARCH-20)."""
    from irene.providers.audio.miniaudio import MiniaudioAudioProvider

    provider = MiniaudioAudioProvider({})
    assert provider.get_provider_name() == "miniaudio"
    assert provider.get_python_dependencies() == ["miniaudio>=1.59"]
    # Self-contained: no system packages on any platform.
    assert all(pkgs == [] for pkgs in provider.get_platform_dependencies().values())


@pytest.mark.asyncio
async def test_miniaudio_play_stream_empty_is_noop():
    """An empty PCM stream short-circuits before any device is opened (device-safe)."""
    from irene.providers.audio.miniaudio import MiniaudioAudioProvider

    provider = MiniaudioAudioProvider({})
    if not await provider.is_available():
        pytest.skip("miniaudio not installed")

    async def empty():
        return
        yield  # pragma: no cover - makes this an async generator

    await provider.play_stream(empty(), sample_rate=16000, channels=1, sample_width=2)
    assert provider.is_playing() is False


def _build_workflow_with_fakes(captured):
    import logging

    from irene.workflows.voice_assistant import UnifiedVoiceAssistantWorkflow

    class _FakeAudio:
        async def play_stream(self, pcm, *, sample_rate, channels, sample_width, **kw):
            captured.update(pcm=pcm, rate=sample_rate, channels=channels, width=sample_width)

        async def play_file(self, path):
            captured["played_file"] = True

    class _FakeNegotiator:  # pass-through sink conform
        async def to_sink(self, audio_data, sink=None, trace_context=None):
            return audio_data

    wf = UnifiedVoiceAssistantWorkflow()
    wf.audio = _FakeAudio()
    wf.audio_negotiator = _FakeNegotiator()
    wf.logger = logging.getLogger("test.workflow")
    return wf


@pytest.mark.asyncio
async def test_workflow_stream_mode_parses_wav_and_play_streams(tmp_path):
    """ARCH-20 stream mode: WAV -> PCM -> to_sink -> play_stream with the right format."""
    captured = {}
    wf = _build_workflow_with_fakes(captured)

    pcm = b"\x01\x00\x02\x00\x03\x00\x04\x00" * 20
    wav_path = tmp_path / "tts.wav"
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm)

    await wf._play_tts_stream(wav_path)

    assert captured["pcm"] == pcm
    assert (captured["rate"], captured["channels"], captured["width"]) == (16000, 1, 2)
    assert "played_file" not in captured


@pytest.mark.asyncio
async def test_workflow_stream_mode_falls_back_to_play_file_for_non_wav(tmp_path):
    """Text-only TTS output (not WAV) degrades to play_file rather than erroring."""
    captured = {}
    wf = _build_workflow_with_fakes(captured)

    text_path = tmp_path / "tts.txt"
    text_path.write_text("console tts output, not audio")

    await wf._play_tts_stream(text_path)

    assert captured.get("played_file") is True
    assert "pcm" not in captured
