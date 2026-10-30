"""Exit codes and the error type that carries a three-part user message.

Every user-facing error has to say what happened, why it happened and
what to do next, with the command to run, and to take its text from the i18n catalogue.
`WizrelayError` is how that message travels from the place that detects the problem to the
single place that prints it (`cli.main`).

Exit codes:

    0  success
    1  a violation or a validation failure — the work is wrong, not the invocation
    2  a user or configuration error — the invocation is wrong
    3  an unexpected internal error
"""

from __future__ import annotations

from typing import Optional

EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_USER = 2
EXIT_INTERNAL = 3


class WizrelayError(Exception):
    """A failure with a message intended for a person.

    Attributes:
        message: what happened, already localised.
        reason: why it happened. Optional, but expected for anything a user can fix.
        remedy: what to do next, including the exact command. Optional.
        code: the process exit code to use.
    """

    def __init__(
        self,
        message: str,
        *,
        reason: Optional[str] = None,
        remedy: Optional[str] = None,
        code: int = EXIT_USER,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.reason = reason
        self.remedy = remedy
        self.code = code

    def render(self) -> str:
        """Lay the three parts out as the lines a terminal shows."""
        lines = [self.message]
        if self.reason:
            lines.append(f"  Why: {self.reason}")
        if self.remedy:
            lines.append(f"  Fix: {self.remedy}")
        return "\n".join(lines)


class UsageError(WizrelayError):
    """The command line itself was wrong. Always exit code 2."""

    def __init__(
        self, message: str, *, reason: Optional[str] = None, remedy: Optional[str] = None
    ) -> None:
        super().__init__(message, reason=reason, remedy=remedy, code=EXIT_USER)


class ValidationError(WizrelayError):
    """A document or a working tree failed a check. Always exit code 1."""

    def __init__(
        self, message: str, *, reason: Optional[str] = None, remedy: Optional[str] = None
    ) -> None:
        super().__init__(message, reason=reason, remedy=remedy, code=EXIT_VIOLATION)
