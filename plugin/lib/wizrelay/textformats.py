"""Parsers for the Markdown conventions a task package uses.

A package is Markdown a person writes and reads. These parsers are what
turns that prose into the structure `brief`, `status`, `audit`, `hub validate` and
`hub comment` need: which acceptance criteria belong to a role, which questions are still
open, which decisions exist, how far the plan has got.

Two properties matter more than completeness:

* **Bilingual.** Keyword matching folds Turkish characters, so `Doğrulama:`, `DOGRULAMA:`
  and `Verification:` are one keyword, and `AÇIK`, `Açık`, `acik` are one value. The
  dotted and dotless I are the reason a plain `str.lower()` is not enough.
* **Examples do not count.** A fenced code block or a blockquote in `research.md` that
  shows the format must not be parsed as the format. The tests pin this
  down, because a documentation example silently inflating the open-question count would
  make the whole signal untrustworthy.

This module is pure: it takes text and returns data.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator, Sequence
from typing import Optional

__all__ = [
    "AcceptanceCriterion",
    "Decision",
    "PlanProgress",
    "Question",
    "acs_for_role",
    "content_lines",
    "fold",
    "parse_acceptance",
    "parse_decisions",
    "parse_plan_progress",
    "parse_questions",
    "slugify",
]

# --------------------------------------------------------------------------------------
# Bilingual folding
# --------------------------------------------------------------------------------------

# Turkish letters mapped to their ASCII skeleton. `İ`, `I` and `ı` all fold to `i`, which
# is what makes `İPTAL`, `IPTAL` and `iptal` one value. Python's own `str.lower()` turns
# `İ` into `i` plus a combining dot, so the normalisation below also strips marks.
_TR_MAP = str.maketrans(
    {
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ş": "s",
        "ş": "s",
        "Ğ": "g",
        "ğ": "g",
        "Ç": "c",
        "ç": "c",
        "Ö": "o",
        "ö": "o",
        "Ü": "u",
        "ü": "u",
        "Â": "a",
        "â": "a",
        "Î": "i",
        "î": "i",
        "Û": "u",
        "û": "u",
    }
)


def fold(text: str) -> str:
    """Case-fold and de-accent text so bilingual keywords compare equal.

    >>> fold("AÇIK") == fold("açık") == fold("Açık")
    True
    >>> fold("Doğrulama")
    'dogrulama'
    >>> fold("İPTAL")
    'iptal'
    """
    folded = text.translate(_TR_MAP).lower()
    decomposed = unicodedata.normalize("NFKD", folded)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


# Keyword vocabulary, stored folded so lookups never re-fold constants.
_VERIFICATION_KEYS = frozenset({fold("Verification"), fold("Doğrulama")})
_STATUS_KEYS = frozenset({fold("Status"), fold("Durum")})
_STATUS_OPEN = frozenset({fold("OPEN"), fold("AÇIK")})
_STATUS_ANSWERED = frozenset({fold("ANSWERED"), fold("YANITLANDI")})
_STATUS_CANCELLED = frozenset({fold("CANCELLED"), fold("CANCELED"), fold("İPTAL")})

STATUS_OPEN = "open"
STATUS_ANSWERED = "answered"
STATUS_CANCELLED = "cancelled"
STATUS_UNKNOWN = "unknown"

# Gherkin keywords stay English in both languages, the way the shipped templates write
# them. `hub validate` only warns when they are absent, so a hub that writes them in
# another language gets a warning rather than an error.
_GHERKIN = ("given", "when", "then")


# --------------------------------------------------------------------------------------
# Line scanning
# --------------------------------------------------------------------------------------

_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def content_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield `(line_number, line)` for lines that carry content, not examples.

    Skipped:

    * everything inside a fenced code block, and the fence lines themselves
    * blockquote lines, which is how a document quotes the format it describes

    Line numbers are 1-based so they can go straight into a `file:line` message.
    """
    fence: Optional[str] = None
    for number, raw in enumerate(text.splitlines(), start=1):
        opener = _FENCE.match(raw)
        if fence is None:
            if opener:
                fence = opener.group(1)[0]
                continue
        else:
            # A closing fence uses the same character; length may differ.
            if opener and opener.group(1)[0] == fence:
                fence = None
            continue
        if raw.lstrip().startswith(">"):
            continue
        yield number, raw


# --------------------------------------------------------------------------------------
# Acceptance criteria
# --------------------------------------------------------------------------------------

# `## AC-3 [backend, frontend] Quota is enforced per tenant`
# `###` is accepted too, and the role list may be absent or empty.
_AC_HEADING = re.compile(
    r"^\s{0,3}#{2,3}\s+AC-(\d+)\s*(?:\[(?P<roles>[^\]]*)\])?\s*(?P<title>.*?)\s*$",
    re.IGNORECASE,
)


class AcceptanceCriterion:
    """One acceptance criterion, with the role slice it applies to."""

    __slots__ = (
        "body",
        "has_gherkin",
        "identifier",
        "line",
        "number",
        "roles",
        "title",
        "verification",
    )

    def __init__(
        self,
        number: int,
        title: str,
        roles: Sequence[str],
        line: int,
        body: Sequence[str],
        verification: Optional[str],
        has_gherkin: bool,
    ) -> None:
        self.number = number
        self.identifier = f"AC-{number}"
        self.title = title
        #: Empty means "every role".
        self.roles: list[str] = list(roles)
        self.line = line
        self.body: list[str] = list(body)
        self.verification = verification
        self.has_gherkin = has_gherkin

    def applies_to(self, role: Optional[str]) -> bool:
        """An empty role list applies everywhere; otherwise compare folded names."""
        if not self.roles:
            return True
        if not role:
            return True
        return fold(role) in {fold(r) for r in self.roles}

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<AC-{self.number} roles={self.roles!r} title={self.title!r}>"


def _split_keyword_line(line: str) -> Optional[tuple[str, str]]:
    """Split a `- **Status:** OPEN` style line into its folded key and raw value.

    Markdown decoration around the key and the value is stripped, because authors write
    the same field as `Status: OPEN`, `- Durum: AÇIK` and `**Durum:** açık`.
    """
    stripped = line.strip()
    stripped = re.sub(r"^[-*+]\s+", "", stripped)
    match = re.match(r"^\**\s*([^:*]+?)\s*\**\s*:\s*(.*)$", stripped)
    if not match:
        return None
    key = fold(match.group(1))
    value = match.group(2).strip().strip("*").strip()
    return key, value


class _PendingCriterion:
    """A criterion being accumulated while the parser walks its body lines.

    A small class rather than a dictionary: the body, the role list and the line number
    have three different types, and a `dict[str, object]` accumulator costs a cast at
    every single use.
    """

    __slots__ = ("body", "line", "number", "roles", "title")

    def __init__(self, number: int, title: str, roles: list[str], line: int) -> None:
        self.number = number
        self.title = title
        self.roles = roles
        self.line = line
        self.body: list[str] = []


def parse_acceptance(text: str) -> list[AcceptanceCriterion]:
    """Parse every `## AC-<n>` block in `acceptance.md`.

    The body of a criterion is every content line up to the next heading, which is what
    carries the Given/When/Then lines and the verification line.
    """
    found: list[AcceptanceCriterion] = []
    current: Optional[_PendingCriterion] = None

    def close(pending: Optional[_PendingCriterion]) -> None:
        if pending is None:
            return
        verification: Optional[str] = None
        has_gherkin = False
        for line in pending.body:
            parsed = _split_keyword_line(line)
            if parsed and parsed[0] in _VERIFICATION_KEYS and parsed[1]:
                verification = parsed[1]
            folded = fold(line.strip()).lstrip("-*+ ").lstrip("*").strip()
            if folded.startswith(_GHERKIN):
                has_gherkin = True
        found.append(
            AcceptanceCriterion(
                number=pending.number,
                title=pending.title,
                roles=pending.roles,
                line=pending.line,
                body=pending.body,
                verification=verification,
                has_gherkin=has_gherkin,
            )
        )

    for number, line in content_lines(text):
        heading = _AC_HEADING.match(line)
        if heading:
            close(current)
            roles_raw = heading.group("roles") or ""
            current = _PendingCriterion(
                number=int(heading.group(1)),
                title=heading.group("title").strip(),
                roles=[part.strip() for part in roles_raw.split(",") if part.strip()],
                line=number,
            )
            continue
        if re.match(r"^\s{0,3}#{1,6}\s", line):
            # Any other heading ends the current criterion.
            close(current)
            current = None
            continue
        if current is not None:
            current.body.append(line)

    close(current)
    found.sort(key=lambda ac: ac.number)
    return found


def acs_for_role(
    criteria: Sequence[AcceptanceCriterion], role: Optional[str]
) -> list[AcceptanceCriterion]:
    """Filter criteria down to the ones a role has to satisfy."""
    return [ac for ac in criteria if ac.applies_to(role)]


# --------------------------------------------------------------------------------------
# Decisions
# --------------------------------------------------------------------------------------

# `## D-004 Retry-After upper bound (v2, 2026-10-30)`
_D_HEADING = re.compile(
    r"^\s{0,3}#{2,3}\s+D-(\d+)\s*(?P<title>.*?)"
    r"(?:\s*\(\s*v(?P<version>\d+)\s*,\s*(?P<date>\d{4}-\d{2}-\d{2})\s*\)\s*)?$",
    re.IGNORECASE,
)


class Decision:
    """A recorded decision from `decisions.md`."""

    __slots__ = ("date", "identifier", "line", "number", "title", "version")

    def __init__(
        self,
        number: int,
        title: str,
        version: Optional[int],
        date: Optional[str],
        line: int,
    ) -> None:
        self.number = number
        self.identifier = f"D-{number:03d}"
        self.title = title
        self.version = version
        self.date = date
        self.line = line

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.identifier} v={self.version} title={self.title!r}>"


def parse_decisions(text: str) -> list[Decision]:
    """Parse every `## D-<nnn>` heading, newest-first ordering left to the caller."""
    out: list[Decision] = []
    for number, line in content_lines(text):
        match = _D_HEADING.match(line)
        if not match:
            continue
        version = match.group("version")
        out.append(
            Decision(
                number=int(match.group(1)),
                title=(match.group("title") or "").strip(),
                version=int(version) if version else None,
                date=match.group("date"),
                line=number,
            )
        )
    out.sort(key=lambda d: d.number)
    return out


# --------------------------------------------------------------------------------------
# Questions
# --------------------------------------------------------------------------------------

_Q_HEADING = re.compile(r"^\s{0,3}#{2,3}\s+Q-(\d+)\s*(?P<title>.*?)\s*$", re.IGNORECASE)
_D_REF = re.compile(r"\bD-(\d+)\b", re.IGNORECASE)


class Question:
    """A question from `questions.md`, with the status that decides whether it blocks."""

    __slots__ = ("answer_ref", "identifier", "line", "number", "status", "title")

    def __init__(
        self,
        number: int,
        title: str,
        status: str,
        answer_ref: Optional[str],
        line: int,
    ) -> None:
        self.number = number
        self.identifier = f"Q-{number:03d}"
        self.title = title
        #: One of STATUS_OPEN, STATUS_ANSWERED, STATUS_CANCELLED, STATUS_UNKNOWN.
        self.status = status
        self.answer_ref = answer_ref
        self.line = line

    @property
    def is_open(self) -> bool:
        """Unknown counts as open: a question with no status still needs an answer."""
        return self.status in (STATUS_OPEN, STATUS_UNKNOWN)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.identifier} {self.status} title={self.title!r}>"


def _classify_status(value: str) -> str:
    folded = fold(value)
    first = re.split(r"[\s(\[.,;:]", folded, maxsplit=1)[0]
    if first in _STATUS_ANSWERED or folded.startswith(tuple(_STATUS_ANSWERED)):
        return STATUS_ANSWERED
    if first in _STATUS_CANCELLED or folded.startswith(tuple(_STATUS_CANCELLED)):
        return STATUS_CANCELLED
    if first in _STATUS_OPEN or folded.startswith(tuple(_STATUS_OPEN)):
        return STATUS_OPEN
    return STATUS_UNKNOWN


class _PendingQuestion:
    """A question being accumulated while the parser looks for its status line."""

    __slots__ = ("answer_ref", "line", "number", "status", "title")

    def __init__(self, number: int, title: str, line: int) -> None:
        self.number = number
        self.title = title
        self.line = line
        self.status = STATUS_UNKNOWN
        self.answer_ref: Optional[str] = None


def parse_questions(text: str) -> list[Question]:
    """Parse every `## Q-<nnn>` block and the status line inside it."""
    out: list[Question] = []
    current: Optional[_PendingQuestion] = None

    def close(pending: Optional[_PendingQuestion]) -> None:
        if pending is None:
            return
        out.append(
            Question(
                number=pending.number,
                title=pending.title,
                status=pending.status,
                answer_ref=pending.answer_ref,
                line=pending.line,
            )
        )

    for number, line in content_lines(text):
        heading = _Q_HEADING.match(line)
        if heading:
            close(current)
            current = _PendingQuestion(
                number=int(heading.group(1)),
                title=(heading.group("title") or "").strip(),
                line=number,
            )
            continue
        if re.match(r"^\s{0,3}#{1,6}\s", line):
            close(current)
            current = None
            continue
        if current is None:
            continue
        parsed = _split_keyword_line(line)
        if parsed and parsed[0] in _STATUS_KEYS:
            current.status = _classify_status(parsed[1])
            ref = _D_REF.search(parsed[1])
            if ref:
                current.answer_ref = f"D-{int(ref.group(1)):03d}"

    close(current)
    out.sort(key=lambda q: q.number)
    return out


# --------------------------------------------------------------------------------------
# Plan progress
# --------------------------------------------------------------------------------------

# `- [ ] step` and `- [x] step`; `*` bullets and an uppercase `X` are accepted too.
_PLAN_STEP = re.compile(r"^\s*[-*+]\s*\[(?P<mark>[ xX])\]\s*(?P<text>.*)$")


class PlanProgress:
    """How far `plan.md` has got, used in the session-start context and in `status`."""

    __slots__ = ("done", "next_step", "total")

    def __init__(self, total: int, done: int, next_step: Optional[str]) -> None:
        self.total = total
        self.done = done
        #: The first unchecked step, so the context line can say what comes next.
        self.next_step = next_step

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.done)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<PlanProgress {self.done}/{self.total}>"


def parse_plan_progress(text: str) -> PlanProgress:
    """Count checklist items in `plan.md`, ignoring examples in fences and quotes."""
    total = 0
    done = 0
    next_step: Optional[str] = None
    for _number, line in content_lines(text):
        match = _PLAN_STEP.match(line)
        if not match:
            continue
        total += 1
        if match.group("mark") in ("x", "X"):
            done += 1
        elif next_step is None:
            next_step = match.group("text").strip() or None
    return PlanProgress(total=total, done=done, next_step=next_step)


# --------------------------------------------------------------------------------------
# Slugs
# --------------------------------------------------------------------------------------

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(title: str, *, limit: int = 60) -> str:
    """Turn a task title into the directory-safe slug used in `<ID>-<slug>`.

    Folds Turkish characters to ASCII first, so "Tenant bazlı günlük API istek kotası"
    becomes `tenant-bazli-gunluk-api-istek-kotasi` rather than losing the accented
    letters entirely. Truncation happens at a word boundary
    so the slug stays readable.

    Every run of non-alphanumeric characters becomes one hyphen, apostrophes included:
    `İstanbul'da` becomes `istanbul-da`. Dropping the apostrophe instead, as some
    slugifiers do, would give `istanbulda`, and in Turkish the apostrophe marks a suffix
    on a proper noun, so keeping the boundary reads better.
    """
    folded = fold(title)
    slug = _SLUG_STRIP.sub("-", folded).strip("-")
    if not slug:
        return "task"
    if len(slug) <= limit:
        return slug
    cut = slug[: limit + 1]
    boundary = cut.rfind("-")
    if boundary >= limit // 2:
        return cut[:boundary].strip("-")
    return slug[:limit].strip("-")
