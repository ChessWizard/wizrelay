"""Glob matching and intersection.

The table rows are the appendix verbatim. If one of these changes, the scope contract
changed, and that is a decision for the plan owner.
"""

from __future__ import annotations

import pytest

from wizrelay import globs

# First table.
MATCH_CASES = [
    ("app/quota/x.py", "app/quota/**", True),
    ("app/quota", "app/quota/**", False),
    ("tests/a/b/test_x.py", "tests/**/test_*.py", True),
    ("tests/test_x.py", "tests/**/test_*.py", True),
    ("sub/poetry.lock", "poetry.lock", True),
    ("src/a.ts", "src/*.ts", True),
    ("src/b/a.ts", "src/*.ts", False),
    (".github/workflows/ci.yml", ".github/**", True),
]

# Second table.
INTERSECT_CASES = [
    (["app/quota/**"], ["app/auth/**"], False),
    (["app/api/v1/messages.py"], ["app/api/**"], True),
    (["src/**/*.tsx"], ["src/billing/**"], True),
]


@pytest.mark.parametrize(("path", "pattern", "expected"), MATCH_CASES)
def test_appendix_b1_match_table(path: str, pattern: str, expected: bool) -> None:
    assert globs.match(path, pattern) is expected


@pytest.mark.parametrize(("left", "right", "expected"), INTERSECT_CASES)
def test_appendix_b1_intersection_table(left, right, expected) -> None:
    assert globs.intersects(left, right) is expected


def test_intersection_is_symmetric() -> None:
    for left, right, expected in INTERSECT_CASES:
        assert globs.intersects(right, left) is expected


def test_empty_set_never_intersects() -> None:
    # An empty allow list means "nothing is in scope", not "everything is".
    assert globs.intersects([], ["app/**"]) is False
    assert globs.intersects(["app/**"], []) is False


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("app/quota/**", "app/quota/"),
        ("src/**/*.tsx", "src/"),
        ("app/api/v1/messages.py", "app/api/v1/messages.py"),
        # A basename pattern can match at any depth, so it claims no prefix at all.
        ("poetry.lock", ""),
        ("**", ""),
        ("*.py", ""),
    ],
)
def test_static_prefix(pattern: str, expected: str) -> None:
    assert globs.static_prefix(pattern) == expected


@pytest.mark.parametrize(
    "pattern",
    ["/etc/passwd", "../outside", "app/../../etc", "C:/Windows", "~/secrets", ""],
)
def test_validate_glob_rejects_escapes(pattern: str) -> None:
    assert globs.validate_glob(pattern) is not None


@pytest.mark.parametrize("pattern", ["app/**", "poetry.lock", "src/*.ts", "a/**/b.py"])
def test_validate_glob_accepts_relative(pattern: str) -> None:
    assert globs.validate_glob(pattern) is None


def test_directory_pattern_covers_its_contents() -> None:
    # A literal pattern with no wildcard behaves like a gitignore directory entry.
    assert globs.match("app/quota", "app/quota") is True
    assert globs.match("app/quota/service.py", "app/quota") is True
    assert globs.match("app/quotas/service.py", "app/quota") is False


def test_character_class_does_not_cross_a_separator() -> None:
    assert globs.match("src/a.ts", "src/[ab].ts") is True
    assert globs.match("src/c.ts", "src/[ab].ts") is False
    assert globs.match("src/x/a.ts", "src/[ab].ts") is False


def test_question_mark_matches_one_non_separator() -> None:
    assert globs.match("src/a.ts", "src/?.ts") is True
    assert globs.match("src/ab.ts", "src/?.ts") is False


def test_windows_separators_are_normalised() -> None:
    assert globs.match("app\\quota\\x.py", "app/quota/**") is True


def test_matching_pattern_names_the_rule_that_fired() -> None:
    assert globs.matching_pattern("app/billing/x.py", ["app/auth/**", "app/billing/**"]) == (
        "app/billing/**"
    )
    assert globs.matching_pattern("app/quota/x.py", ["app/billing/**"]) is None


def test_normalize_rel_path() -> None:
    assert globs.normalize_rel_path("./a//b/") == "a/b"
    assert globs.normalize_rel_path("a\\b") == "a/b"
