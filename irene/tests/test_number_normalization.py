"""BUG-1 — spelled-out numbers must reach numeric parameter extraction (ru + en)."""
import pytest

from irene.utils.text_processing import normalize_numbers_to_digits


@pytest.mark.parametrize("text, lang, expected_substr", [
    ("поставь таймер на десять минут", "ru", "10 минут"),
    ("на двадцать пять минут", "ru", "25 минут"),        # compound
    ("set a timer for ten minutes", "en", "10 minutes"),
    ("for twenty five minutes", "en", "25 minutes"),     # compound
])
def test_spelled_numbers_become_digits(text, lang, expected_substr):
    assert expected_substr in normalize_numbers_to_digits(text, lang)


@pytest.mark.parametrize("text, lang", [
    ("на 10 минут", "ru"),
    ("for 5 minutes", "en"),
])
def test_idempotent_on_digits(text, lang):
    assert normalize_numbers_to_digits(text, lang) == text


@pytest.mark.parametrize("text, lang", [
    ("поставь таймер", "ru"),
    ("hello there", "en"),
])
def test_number_free_text_unchanged(text, lang):
    assert normalize_numbers_to_digits(text, lang) == text


def test_unsupported_language_degrades_to_unchanged():
    # No exception, no worse than the old digit-only path — returns the text as-is.
    assert normalize_numbers_to_digits("десять минут", "zz") == "десять минут"


def test_timer_handler_parses_spelled_and_english(monkeypatch):
    # The timer's duration is extracted by the handler's text fallback (its donation param has no
    # type). Exercise that path directly — stub the message extraction (needs an asset loader) so
    # the test focuses on duration+unit parsing: ru-spelled, ru-compound, English, digit regression.
    from irene.intents.handlers.timer import TimerIntentHandler
    h = TimerIntentHandler.__new__(TimerIntentHandler)
    monkeypatch.setattr(h, "_extract_timer_message", lambda text: "")
    assert h._parse_timer_from_text("поставь таймер на десять минут")[:2] == (10, "minutes")
    assert h._parse_timer_from_text("на двадцать пять минут")[:2] == (25, "minutes")
    assert h._parse_timer_from_text("set a timer for ten minutes")[:2] == (10, "minutes")
    assert h._parse_timer_from_text("на 10 минут")[:2] == (10, "minutes")            # digit regression
