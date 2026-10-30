"""Message catalogue.

Every string a user reads comes from here. Code, comments and skill
bodies are English; the *output* follows the `language` setting, which comes from the hub
at `init` time and can be overridden per project.

Two rules make the catalogue maintainable:

* **Parity.** Every key exists in both `en` and `tr`. `tests/unit/test_i18n.py` asserts it,
  and also asserts that every key used in the source exists in the catalogue, so a message
  added in code without a translation fails the build.
* **Named placeholders.** `{task_id}`, never `{0}`. Turkish and English put the same
  values in different positions, and a named placeholder survives that.

A missing key never raises in production: it renders as the key in guillemets, which is
visible in a bug report but does not break a session. Everything except
edit protection fail open, and a message lookup is no exception.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional

__all__ = ["DEFAULT_LANGUAGE", "LANGUAGES", "Translator", "available_languages", "load"]

DEFAULT_LANGUAGE = "en"
LANGUAGES = ("en", "tr")

_CATALOGUE_DIR = Path(__file__).resolve().parent / "i18n"
_CACHE: dict[str, dict[str, str]] = {}


def available_languages() -> tuple[str, ...]:
    """Language codes with a catalogue file on disk."""
    return tuple(sorted(p.stem for p in _CATALOGUE_DIR.glob("*.json")))


def _read(language: str) -> dict[str, str]:
    cached = _CACHE.get(language)
    if cached is not None:
        return cached
    path = _CATALOGUE_DIR / f"{language}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    # Keys beginning with `_` are catalogue metadata, not messages.
    catalogue = {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, str)}
    _CACHE[language] = catalogue
    return catalogue


class Translator:
    """Looks a key up in the chosen language, falling back to English.

    Instances are cheap and carry no state beyond the two catalogues, so they are passed
    as a parameter rather than held in a module global.
    """

    __slots__ = ("_fallback", "_messages", "language")

    def __init__(self, language: str = DEFAULT_LANGUAGE) -> None:
        self.language = language if language in LANGUAGES else DEFAULT_LANGUAGE
        self._messages = _read(self.language)
        self._fallback = _read(DEFAULT_LANGUAGE) if self.language != DEFAULT_LANGUAGE else {}

    def has(self, key: str) -> bool:
        return key in self._messages or key in self._fallback

    def __call__(self, key: str, /, **values: Any) -> str:
        return self.text(key, **values)

    def text(self, key: str, /, **values: Any) -> str:
        """Return the message for `key`, formatted with named placeholders.

        An unknown key renders as `«key»`. A placeholder the caller forgot renders the
        template unformatted rather than raising, because a `KeyError` from a message
        lookup inside a hook would turn a cosmetic bug into a broken session.
        """
        template = self._messages.get(key) or self._fallback.get(key)
        if template is None:
            if os.environ.get("WIZRELAY_DEBUG") == "1":
                raise KeyError(f"missing i18n key: {key}")
            return f"«{key}»"
        if not values:
            return template
        try:
            return template.format(**values)
        except (KeyError, IndexError, ValueError):
            return template

    def plural(self, key_one: str, key_many: str, count: int, /, **values: Any) -> str:
        """Pick a singular or plural key. Turkish rarely needs it; English does."""
        return self.text(key_one if count == 1 else key_many, count=count, **values)


def load(language: Optional[str] = None) -> Translator:
    """Build a translator for `language`, defaulting to English."""
    return Translator(language or DEFAULT_LANGUAGE)


def catalogue(language: str) -> Mapping[str, str]:
    """Raw catalogue access, for the parity tests."""
    return dict(_read(language))
