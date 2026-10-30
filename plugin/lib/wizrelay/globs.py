"""Glob matching and glob-set intersection.

Scope is expressed as `allow` / `deny` glob lists relative to the repository root
. Two operations are needed:

* **Matching** — does this changed file fall inside the role's scope? Used by the
  `pre-edit` hook, by `audit`, and by `hub validate`.
* **Intersection** — could this scope touch the repository's critical or legacy paths?
  Used by routing, where the answer has to be conservative: a false
  "they intersect" costs a stronger model, a false "they do not" costs a missed risk
  signal.

`fnmatch` is not usable here: it treats `*` as matching `/` as well, which would make
`src/*.ts` match `src/b/a.ts`. The grammar below is the gitignore-style subset this project
appendix B1 pins down.

Grammar
-------

======================  ==========================================================
Pattern                 Meaning
======================  ==========================================================
``*``                   zero or more characters, never ``/``
``?``                   exactly one character, never ``/``
``[abc]`` ``[!a-z]``    a character class, never matching ``/``
``dir/**``              everything **below** ``dir``, but not ``dir`` itself
``a/**/b``              ``a/b`` and ``a/x/y/b`` — ``**`` spans zero or more segments
``name``                no slash, so it matches ``name`` at any depth (basename rule)
``dir`` (no wildcard)   the path itself and everything below it (directory rule)
======================  ==========================================================

This module is pure: no filesystem access, no IO.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Optional

__all__ = [
    "GlobError",
    "intersects",
    "match",
    "match_any",
    "matching_pattern",
    "normalize_rel_path",
    "static_prefix",
    "validate_glob",
]

# Characters that make a segment a pattern rather than a literal.
_WILDCARD_CHARS = "*?["

# Compiled patterns are reused across thousands of path checks in `audit`.
_CACHE: dict[str, re.Pattern[str]] = {}
_CACHE_LIMIT = 4096


class GlobError(ValueError):
    """A pattern that must be rejected rather than interpreted."""


def normalize_rel_path(path: str) -> str:
    """Put a repository-relative path into the single form everything compares against.

    Backslashes become forward slashes so a Windows-reported path compares equal to the
    POSIX form stored in `task.json`. A leading `./` and any duplicate or
    trailing slash are removed.
    """
    text = path.replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    text = re.sub(r"/{2,}", "/", text)
    return text.strip("/")


def validate_glob(pattern: str) -> Optional[str]:
    """Return a reason the pattern is invalid, or None when it is usable.

    Scope globs are repository-relative by definition, so anything that
    could reach outside the repository is rejected rather than normalised away. `hub
    validate` turns the returned reason into a `file:line` error.
    """
    if not pattern or not pattern.strip():
        return "empty pattern"
    text = pattern.replace("\\", "/").strip()
    if text.startswith("/"):
        return "absolute path; scope globs are relative to the repository root"
    if re.match(r"^[A-Za-z]:", text):
        return "drive letter; scope globs are relative to the repository root"
    if text.startswith("~"):
        return "home-relative path; scope globs are relative to the repository root"
    if ".." in text.split("/"):
        return "'..' segment; scope globs may not leave the repository root"
    if "\x00" in text:
        return "null byte"
    return None


def _normalize_pattern(pattern: str) -> str:
    """Apply the basename and directory rules, producing a canonical pattern string."""
    text = pattern.replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    text = text.lstrip("/")
    text = re.sub(r"/{2,}", "/", text)

    # A trailing slash names a directory: `build/` means everything below `build`.
    if text.endswith("/"):
        text = text + "**"

    # The basename rule: a pattern with no slash matches that name at any depth, the way
    # a gitignore line does. `poetry.lock` therefore also matches `sub/poetry.lock`.
    if "/" not in text:
        text = "**/" + text

    return text


def _segment_to_regex(segment: str) -> str:
    """Translate one path segment, where no construct may ever cross a `/`."""
    out: list[str] = []
    i = 0
    n = len(segment)
    while i < n:
        ch = segment[i]
        if ch == "*":
            # A segment-internal `**` carries no extra meaning; collapse the run.
            while i < n and segment[i] == "*":
                i += 1
            out.append("[^/]*")
            continue
        if ch == "?":
            out.append("[^/]")
            i += 1
            continue
        if ch == "[":
            close = segment.find("]", i + 1)
            if close == -1:
                # An unterminated class is a literal bracket, as in a shell.
                out.append(re.escape(ch))
                i += 1
                continue
            body = segment[i + 1 : close]
            if body.startswith(("!", "^")):
                body = "^" + body[1:]
            # Never let a class match a separator, whatever the author wrote.
            out.append("(?:(?![/])[" + body.replace("\\", "\\\\") + "])")
            i = close + 1
            continue
        out.append(re.escape(ch))
        i += 1
    return "".join(out)


def _compile(pattern: str) -> re.Pattern[str]:
    cached = _CACHE.get(pattern)
    if cached is not None:
        return cached

    canonical = _normalize_pattern(pattern)
    segments = canonical.split("/")
    parts: list[str] = []

    for index, segment in enumerate(segments):
        is_last = index == len(segments) - 1
        if segment == "**":
            if is_last:
                # `dir/**` is everything *below* dir. Requiring at least one character
                # after the separator is what makes `app/quota` not match
                # `app/quota/**`.
                parts.append(".+")
            else:
                # Zero or more whole segments, so `a/**/b` also matches `a/b`.
                parts.append("(?:[^/]+/)*")
            continue
        parts.append(_segment_to_regex(segment))
        if not is_last:
            # A following `**` supplies its own trailing separators, but it only ever
            # matches whole segments, so the separator after this one is still required.
            parts.append("/")

    body = "".join(parts)

    # The directory rule: a pattern with no wildcard at all also covers everything below
    # it, so `allow: ["app/quota"]` behaves the way a reader expects.
    if not any(c in canonical for c in _WILDCARD_CHARS):
        body += "(?:/.*)?"

    compiled = re.compile("^" + body + "$")
    if len(_CACHE) < _CACHE_LIMIT:
        _CACHE[pattern] = compiled
    return compiled


def match(path: str, pattern: str) -> bool:
    """True when the repository-relative `path` falls under `pattern`."""
    return bool(_compile(pattern).match(normalize_rel_path(path)))


def match_any(path: str, patterns: Iterable[str]) -> bool:
    """True when any pattern matches. An empty pattern list never matches."""
    normalized = normalize_rel_path(path)
    return any(_compile(p).match(normalized) for p in patterns if p)


def matching_pattern(path: str, patterns: Iterable[str]) -> Optional[str]:
    """Return the first matching pattern, so a message can name the rule that fired."""
    normalized = normalize_rel_path(path)
    for pattern in patterns:
        if pattern and _compile(pattern).match(normalized):
            return pattern
    return None


def static_prefix(pattern: str) -> str:
    """The fixed directory prefix of a pattern: everything before the first wildcard.

    Truncated at the last separator, so the result is always a directory path or the empty
    string. The empty string means "could be anywhere", which is why the basename rule
    normalises `poetry.lock` to `**/poetry.lock` first — a file named at any depth must not
    claim a narrow prefix.

    >>> static_prefix("app/quota/**")
    'app/quota/'
    >>> static_prefix("src/**/*.tsx")
    'src/'
    >>> static_prefix("app/api/v1/messages.py")
    'app/api/v1/messages.py'
    >>> static_prefix("poetry.lock")
    ''
    """
    canonical = _normalize_pattern(pattern)
    first = min(
        (canonical.find(c) for c in _WILDCARD_CHARS if canonical.find(c) != -1),
        default=-1,
    )
    if first == -1:
        return canonical
    cut = canonical.rfind("/", 0, first)
    return "" if cut == -1 else canonical[: cut + 1]


def _as_directory(prefix: str) -> str:
    return prefix if prefix.endswith("/") or not prefix else prefix + "/"


def _prefixes_intersect(left: str, right: str) -> bool:
    """Conservative prefix comparison.

    An empty prefix could be anywhere, so it intersects everything. Otherwise the two
    intersect when they are equal or when one is a directory prefix of the other.
    """
    if not left or not right:
        return True
    if left == right:
        return True
    a = _as_directory(left)
    b = _as_directory(right)
    return a.startswith(b) or b.startswith(a)


def intersects(left: Sequence[str], right: Sequence[str]) -> bool:
    """True when two glob sets could cover a common path.

    Deliberately an over-approximation: it compares static prefixes rather than solving
    pattern intersection exactly. Routing uses the answer as a risk signal, where a false
    positive costs a stronger model and a false negative costs a missed risk.
    """
    if not left or not right:
        return False
    left_prefixes = [static_prefix(p) for p in left if p]
    right_prefixes = [static_prefix(p) for p in right if p]
    return any(_prefixes_intersect(a, b) for a in left_prefixes for b in right_prefixes)


def split_scope(allow: Sequence[str], deny: Sequence[str]) -> tuple[list[str], list[str]]:
    """Return sorted copies of a scope pair, so every rendering is deterministic."""
    return sorted(p for p in allow if p), sorted(p for p in deny if p)
