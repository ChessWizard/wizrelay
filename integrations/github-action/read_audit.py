#!/usr/bin/env python3
"""Read one field out of `wizrelay audit --format json` for the composite action.

This exists as a **file** rather than as a string passed to `python -c`. The action runs
in someone else's repository, on their runner, with their token in the environment, so
what it executes should be readable in this repository before it runs and should show up
in a diff when it changes. An inline `-c` program is neither: it is assembled by the shell
at run time, it cannot be linted, and a security scan reading this repository can only
report that the action builds a command rather than tell anyone what that command does.

Contract, which `action.yml` depends on:

* On success the value is printed on one line and the exit status is 0.
* When `audit.json` is missing, unreadable or not valid JSON, **nothing is printed and the
  exit status is 1.** The caller captures stdout, so the variable comes back empty, and an
  empty `violations` fails the gate. That is deliberate: a parse problem must not be
  indistinguishable from a clean audit.

Standard library only, and no `wizrelay` import: the action installs the package, but this
script runs even when that install is the thing that went wrong.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

FIELDS = ("skipped", "reason", "violations")

DEFAULT_PATH = "audit.json"


def render(field: str, document: Any) -> str:
    """Return the shell-facing text for one field of an audit document."""
    if not isinstance(document, dict):
        raise ValueError("the audit document is not a JSON object")

    if field == "skipped":
        return "true" if document.get("skipped", False) else "false"
    if field == "reason":
        return str(document.get("reason", "") or "")
    if field == "violations":
        return str(document.get("violations", 0))
    raise ValueError(f"unknown field {field!r}")


def main(argv: Optional[list] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in FIELDS:
        sys.stderr.write(f"usage: read_audit.py {{{'|'.join(FIELDS)}}} [path]\n")
        return 2
    field = args[0]
    path = args[1] if len(args) > 1 else DEFAULT_PATH

    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"read_audit.py: cannot read {path}: {exc}\n")
        return 1

    try:
        sys.stdout.write(render(field, document) + "\n")
    except ValueError as exc:
        sys.stderr.write(f"read_audit.py: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
