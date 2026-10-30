"""Message catalogue.

Three properties:

* every key used in the source exists in the catalogue
* every key exists in both languages
* every placeholder a message declares is one the call site could supply
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from wizrelay import i18n

PACKAGE = Path(__file__).resolve().parent.parent.parent / "plugin" / "lib" / "wizrelay"

_CALL = re.compile(r"""\bt(?:\.text)?\(\s*["']([a-z0-9_.]+)["']""")
# A doubled brace is an escaped literal for str.format, not a placeholder.
_PLACEHOLDER = re.compile(r"(?<!\{)\{([a-z_][a-z0-9_]*)\}(?!\})")


def _keys_used() -> set[str]:
    found: set[str] = set()
    for path in sorted(PACKAGE.rglob("*.py")):
        found |= set(_CALL.findall(path.read_text(encoding="utf-8")))
    return found


def test_both_languages_exist() -> None:
    assert set(i18n.available_languages()) == set(i18n.LANGUAGES)


def test_catalogues_have_identical_keys() -> None:
    en = set(i18n.catalogue("en"))
    tr = set(i18n.catalogue("tr"))
    assert en == tr, f"missing from tr: {sorted(en - tr)}; missing from en: {sorted(tr - en)}"


def test_every_key_used_in_the_source_exists() -> None:
    catalogue = set(i18n.catalogue("en"))
    missing = sorted(_keys_used() - catalogue)
    assert not missing, f"used in code but absent from the catalogue: {missing}"


def test_no_unused_keys() -> None:
    # An unused key is dead weight that still has to be translated.
    catalogue = set(i18n.catalogue("en"))
    unused = sorted(catalogue - _keys_used())
    assert not unused, f"in the catalogue but never used: {unused}"


@pytest.mark.parametrize("language", i18n.LANGUAGES)
def test_placeholders_match_across_languages(language: str) -> None:
    english = i18n.catalogue("en")
    other = i18n.catalogue(language)
    mismatches: dict[str, str] = {}
    for key, template in english.items():
        expected = set(_PLACEHOLDER.findall(template))
        actual = set(_PLACEHOLDER.findall(other[key]))
        if expected != actual:
            mismatches[key] = f"en={sorted(expected)} {language}={sorted(actual)}"
    assert not mismatches, f"placeholder mismatch: {mismatches}"


def test_placeholders_are_named_not_positional() -> None:
    # `{task_id}`, never `{0}`. Turkish and English order values
    # differently, and a positional placeholder cannot survive that.
    offenders = [
        key for key, template in i18n.catalogue("en").items() if re.search(r"\{\d+\}", template)
    ]
    assert not offenders, f"positional placeholders in: {offenders}"


def test_a_missing_key_renders_visibly_rather_than_raising() -> None:
    t = i18n.load("en")
    assert t("no.such.key") == "«no.such.key»"


def test_a_missing_key_raises_in_debug_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIZRELAY_DEBUG", "1")
    t = i18n.load("en")
    with pytest.raises(KeyError):
        t("no.such.key")


def test_a_forgotten_placeholder_does_not_raise() -> None:
    # A KeyError from a message lookup inside a hook would turn a cosmetic bug into a
    # broken session.
    t = i18n.load("en")
    assert "{" in t("warn.stale_version")


def test_an_unknown_language_falls_back_to_english() -> None:
    t = i18n.load("de")
    assert t.language == "en"


def test_turkish_falls_back_for_a_key_it_lacks(monkeypatch: pytest.MonkeyPatch) -> None:
    t = i18n.load("tr")
    assert t.has("audit.clean")
    assert t("audit.clean", count=1) != i18n.load("en")("audit.clean", count=1)
