"""Markdown parsers.

The question-status cases are the acceptance criterion verbatim: `Status: OPEN`,
`- Durum: AÇIK`, `**Durum:** açık` and `Durum: Açık` all count as open; ANSWERED,
YANITLANDI and İPTAL do not; and nothing inside a blockquote or a code fence counts.
"""

from __future__ import annotations

import pytest

from wizrelay import textformats as tf

QUESTIONS_DOC = """
## Q-001 Plain English
Status: OPEN

## Q-002 Turkish with a bullet
- Durum: AÇIK

## Q-003 Turkish, bold, lowercase
**Durum:** açık

## Q-004 Turkish, title case
Durum: Açık

## Q-005 Answered in English
Status: ANSWERED (D-004)

## Q-006 Answered in Turkish
Durum: YANITLANDI (D-005)

## Q-007 Cancelled in Turkish
Durum: İPTAL

## Q-008 Cancelled in English
Status: CANCELLED

> ## Q-100 A quoted example
> Status: OPEN

```
## Q-200 A fenced example
Status: OPEN
```
"""


def test_question_count_excludes_examples() -> None:
    questions = tf.parse_questions(QUESTIONS_DOC)
    assert [q.number for q in questions] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_open_questions_are_the_four_spellings() -> None:
    questions = tf.parse_questions(QUESTIONS_DOC)
    assert [q.number for q in questions if q.is_open] == [1, 2, 3, 4]


@pytest.mark.parametrize(
    ("number", "status", "ref"),
    [
        (5, tf.STATUS_ANSWERED, "D-004"),
        (6, tf.STATUS_ANSWERED, "D-005"),
        (7, tf.STATUS_CANCELLED, None),
        (8, tf.STATUS_CANCELLED, None),
    ],
)
def test_closed_statuses(number: int, status: str, ref) -> None:
    question = next(q for q in tf.parse_questions(QUESTIONS_DOC) if q.number == number)
    assert question.status == status
    assert question.answer_ref == ref


def test_a_question_with_no_status_counts_as_open() -> None:
    # Unknown has to count as open: a question nobody has marked still needs an answer.
    questions = tf.parse_questions("## Q-009 No status line\n\nSomething.\n")
    assert questions[0].status == tf.STATUS_UNKNOWN
    assert questions[0].is_open is True


ACCEPTANCE_DOC = """
## AC-1 [backend, frontend] Two roles
Given a state
When an action
Then a result
Verification: `pytest -q`

### AC-2 Every role
Then a result
Doğrulama: `make test`

## AC-3 [backend] No verification and no gherkin
Just prose.
"""


def test_role_list_parsing() -> None:
    criteria = tf.parse_acceptance(ACCEPTANCE_DOC)
    assert [c.roles for c in criteria] == [["backend", "frontend"], [], ["backend"]]


def test_empty_role_list_applies_to_every_role() -> None:
    criteria = tf.parse_acceptance(ACCEPTANCE_DOC)
    assert criteria[1].applies_to("mobile") is True
    assert criteria[0].applies_to("mobile") is False


def test_verification_line_is_bilingual() -> None:
    criteria = tf.parse_acceptance(ACCEPTANCE_DOC)
    assert criteria[0].verification == "`pytest -q`"
    assert criteria[1].verification == "`make test`"
    assert criteria[2].verification is None


def test_gherkin_detection() -> None:
    criteria = tf.parse_acceptance(ACCEPTANCE_DOC)
    assert [c.has_gherkin for c in criteria] == [True, True, False]


def test_acs_for_role() -> None:
    criteria = tf.parse_acceptance(ACCEPTANCE_DOC)
    assert [c.identifier for c in tf.acs_for_role(criteria, "frontend")] == ["AC-1", "AC-2"]
    assert [c.identifier for c in tf.acs_for_role(criteria, "backend")] == [
        "AC-1",
        "AC-2",
        "AC-3",
    ]


def test_decisions() -> None:
    decisions = tf.parse_decisions(
        "## D-004 Retry-After upper bound (v2, 2026-10-30)\n\nbody\n\n## D-001 Something\n"
    )
    assert [d.identifier for d in decisions] == ["D-001", "D-004"]
    latest = decisions[-1]
    assert (latest.version, latest.date) == (2, "2026-10-30")


def test_plan_progress_accepts_both_bullets_and_cases() -> None:
    progress = tf.parse_plan_progress("- [x] a\n* [X] b\n+ [ ] c\n- [ ] d\n")
    assert (progress.total, progress.done, progress.remaining) == (4, 2, 2)
    assert progress.next_step == "c"


def test_plan_progress_ignores_fenced_examples() -> None:
    progress = tf.parse_plan_progress("```\n- [ ] not a step\n```\n- [x] a real one\n")
    assert (progress.total, progress.done) == (1, 1)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        (
            "Tenant bazlı günlük API istek kotası",
            "tenant-bazli-gunluk-api-istek-kotasi",
        ),
        # An apostrophe is a separator, not a character to drop: in Turkish it marks a
        # suffix on a proper noun, so `istanbul-da` reads better than `istanbulda`.
        ("İstanbul'da ÇÖĞÜŞ", "istanbul-da-cogus"),
        ("   multiple   spaces   ", "multiple-spaces"),
        ("!!!", "task"),
    ],
)
def test_slugify(title: str, expected: str) -> None:
    assert tf.slugify(title) == expected


def test_slugify_cuts_at_a_word_boundary() -> None:
    slug = tf.slugify("alpha beta gamma delta epsilon zeta eta theta iota kappa", limit=20)
    assert len(slug) <= 20
    assert not slug.endswith("-")
    assert slug == "alpha-beta-gamma"


@pytest.mark.parametrize(
    ("left", "right"),
    [("AÇIK", "açık"), ("AÇIK", "Açık"), ("İPTAL", "iptal"), ("Doğrulama", "DOGRULAMA")],
)
def test_fold_handles_turkish_dotted_and_dotless_i(left: str, right: str) -> None:
    assert tf.fold(left) == tf.fold(right)


def test_content_lines_skips_fences_and_quotes() -> None:
    text = "a\n> quoted\n```\nfenced\n```\nb\n"
    assert [line for _n, line in tf.content_lines(text)] == ["a", "b"]


def test_content_lines_numbers_are_one_based() -> None:
    assert next(iter(tf.content_lines("first\n")))[0] == 1
