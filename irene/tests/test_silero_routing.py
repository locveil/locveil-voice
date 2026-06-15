"""Silero TTS model-id routing (QUAL-49).

Regression: silero v3/v4 used to place the model at `<dir>/<config:model_file>` with a shared
default (`v3_ru.pt`), bypassing the AssetManager model-id router — so two v3 languages that both
left `model_file` at the default resolved to the *same* file. The fix routes the path through
`get_model_path("silero_v{3,4}", model_id)` so distinct models always get distinct paths.
"""

from irene.providers.tts.silero_v3 import SileroV3TTSProvider
from irene.providers.tts.silero_v4 import SileroV4TTSProvider


def test_v3_model_id_routes_to_distinct_paths():
    # Different v3 languages must never collide on a shared default file.
    ru = SileroV3TTSProvider({"model": "v3_ru"}).model_file
    en = SileroV3TTSProvider({"model": "v3_en"}).model_file
    assert ru.name == "v3_ru.pt"
    assert en.name == "v3_en.pt"
    assert ru != en                       # anti-collision: the whole point of the fix
    assert ru.parent == en.parent         # same provider dir, distinct files


def test_v3_default_is_russian():
    p = SileroV3TTSProvider({})
    assert p.model_id == "v3_ru"
    assert p.model_file.name == "v3_ru.pt"


def test_v4_routes_by_model_id():
    p = SileroV4TTSProvider({"model": "v4_ru"})
    assert p.model_file.name == "v4_ru.pt"
    # model_url is derived from the descriptor for the selected model_id (legacy-fallback safety).
    assert p.model_url == p._get_default_model_urls()["v4_ru"]


def test_explicit_model_file_override_still_honored():
    # Back-compat: an explicit model_file wins over model-id routing.
    p = SileroV4TTSProvider({"model_file": "custom.pt"})
    assert p.model_file.name == "custom.pt"
