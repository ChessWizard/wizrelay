"""Loading and rendering the files `init`, `hub init` and `hub new` write.

Not one of the original modules; a structural addition
alongside `gitcmd.py`. Three callers need the same three operations, and duplicating them
in `cli.py` would make that file harder to read than it already is.

The placeholder convention does real work. A template ships
`{{like this}}`, and `hub validate` treats a remaining placeholder as an **error** with a
`file:line` reference. That is what makes an unfinished package unpublishable:
the scaffold is deliberately invalid until a person fills it in. So rendering substitutes
only the keys it was given and leaves the rest alone — a template is never silently
completed with a plausible default.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Optional

from .errors import UsageError
from .i18n import DEFAULT_LANGUAGE

__all__ = [
    "PLACEHOLDER",
    "dev_template",
    "find_placeholders",
    "hub_template",
    "render",
    "template_root",
    "write_if_absent",
    "write_if_changed",
]

#: `{{anything}}` with no nested braces, so a rendered `{path}` in a command string is not
#: mistaken for a placeholder.
PLACEHOLDER = re.compile(r"\{\{([^{}]{0,200})\}\}")


def template_root() -> Path:
    """Locate `plugin/templates/`."""
    here = Path(__file__).resolve()
    for candidate in (
        here.parent.parent.parent / "templates",
        here.parent / "templates",
    ):
        if candidate.is_dir():
            return candidate
    raise UsageError(
        "The template directory is missing from this installation.",
        reason="plugin/templates/ could not be found next to the library.",
        remedy="Reinstall the plugin, or set WIZRELAY_TEMPLATES_DIR.",
    )


def _read(kind: str, language: str, name: str) -> str:
    root = template_root() / kind
    for candidate in (language, DEFAULT_LANGUAGE):
        path = root / candidate / name
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise UsageError(
        f"Template {kind}/{language}/{name} is missing.",
        reason="The plugin's template set is incomplete.",
        remedy="Reinstall the plugin.",
    )


def dev_template(language: str, name: str) -> str:
    """A developer-repository template, falling back to English when `tr` lacks it."""
    return _read("dev", language, name)


def hub_template(language: str, name: str) -> str:
    """A hub template, falling back to English when `tr` lacks it."""
    return _read("hub", language, name)


def render(text: str, values: Mapping[str, str]) -> str:
    """Substitute `{{key}}` for every key given, leaving unknown placeholders intact.

    Matching is on the placeholder's exact inner text, so a template may carry both a
    substitutable `{{ROLE}}` and an illustrative `{{what this role implements}}` that must
    survive to be caught by validation.
    """

    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key in values:
            return values[key]
        return match.group(0)

    return PLACEHOLDER.sub(replace, text)


def find_placeholders(text: str) -> list[tuple[int, str]]:
    """Return `(line_number, placeholder)` for every remaining placeholder.

    Line numbers are 1-based so `hub validate` can print `file:line`.
    """
    found: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in PLACEHOLDER.finditer(line):
            found.append((number, match.group(0)))
    return found


def write_if_absent(path: Path, content: str) -> bool:
    """Write `content` only when `path` does not exist. Returns whether it wrote.

    This is what makes `init` and `pull` idempotent and keeps invariant I9: a developer's
    `plan.md` is created once and never replaced.
    """
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def write_if_changed(path: Path, content: str) -> bool:
    """Write only when the content differs. Returns whether it wrote.

    Used for plugin-owned files such as `PROTOCOL.md`, which should pick up an upgrade but
    must not make a second `init` report a change.
    """
    try:
        if path.read_text(encoding="utf-8") == content:
            return False
    except (OSError, UnicodeDecodeError):
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def append_line_if_absent(path: Path, line: str, *, heading: Optional[str] = None) -> bool:
    """Append `line` to a text file unless it is already there.

    Written for `CLAUDE.md`, where invariant I7 requires `init` to **add** rather than
    replace. Two details matter:

    * an empty or missing file gets no leading blank line, which appendix B2 #1 calls out
    * an existing file is separated by exactly one blank line
    """
    try:
        existing = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        existing = ""

    if line.strip() and line.strip() in existing:
        return False

    block = ""
    if heading and heading not in existing:
        block += heading + "\n"
    block += line + "\n"

    if not existing.strip():
        new = block
    else:
        separator = (
            "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        )
        new = existing + separator + block

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return True


def merge_gitignore(path: Path, entries: list[str]) -> bool:
    """Add ignore entries, preserving whatever is already there."""
    try:
        existing = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        existing = ""

    present = {line.strip() for line in existing.splitlines()}
    missing = [entry for entry in entries if entry not in present]
    if not missing:
        return False

    block = "\n".join(missing) + "\n"
    if not existing.strip():
        new = block
    else:
        separator = "" if existing.endswith("\n") else "\n"
        new = existing + separator + block

    path.write_text(new, encoding="utf-8")
    return True


def package_scaffold(language: str, roles: list[str]) -> dict[str, str]:
    """The Markdown files a new package starts with, keyed by package-relative path.

    `contracts.md` appears only for a multi-role package, because that is what makes it
    required exactly then — and an empty `contracts.md` in a single-role package is a
    validation warning, not a helpful file.
    """
    out: dict[str, str] = {}
    for name in ("research.md", "scope.md", "acceptance.md", "decisions.md"):
        out[name] = hub_template(language, f"package/{name}")
    if len(roles) > 1:
        out["contracts.md"] = hub_template(language, "package/contracts.md")
    role_template = hub_template(language, "package/roles/role.md")
    for role in roles:
        out[f"roles/{role}.md"] = render(role_template, {"ROLE": role})
    return out
