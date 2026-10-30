#!/usr/bin/env python3
"""Prepare a release: bump the version, cut the changelog, print the tag command.

Deliberately does not touch git: `make release` prepares a
release without pushing, and §1.3 rule 9 forbids publishing without the plan owner's
approval, so the signed tag stays a manual step.

Single source of truth: `version` in plugin/.claude-plugin/plugin.json.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "plugin" / ".claude-plugin" / "plugin.json"
PYPROJECT = REPO / "pyproject.toml"
INIT = REPO / "plugin" / "lib" / "wizrelay" / "__init__.py"
CHANGELOG = REPO / "CHANGELOG.md"

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")


def bump_manifest(version: str) -> None:
    """Rewrite `version` in place, keeping key order and formatting stable."""
    text = MANIFEST.read_text(encoding="utf-8")
    data = json.loads(text)
    data["version"] = version
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def bump_pyproject(version: str) -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    new, count = re.subn(r'(?m)^version = "[^"]+"$', f'version = "{version}"', text, count=1)
    if count != 1:
        raise SystemExit('pyproject.toml: could not find a single `version = "..."` line')
    PYPROJECT.write_text(new, encoding="utf-8")


def bump_init(version: str) -> None:
    text = INIT.read_text(encoding="utf-8")
    new, count = re.subn(
        r'(?m)^__version__ = "[^"]+"$', f'__version__ = "{version}"', text, count=1
    )
    if count != 1:
        raise SystemExit('__init__.py: could not find a single `__version__ = "..."` line')
    INIT.write_text(new, encoding="utf-8")


def cut_changelog(version: str) -> None:
    """Turn the `Unreleased` heading into a dated release and open a fresh one."""
    text = CHANGELOG.read_text(encoding="utf-8")
    if "## [Unreleased]" not in text:
        raise SystemExit("CHANGELOG.md: no `## [Unreleased]` section to cut")
    today = dt.date.today().isoformat()
    text = text.replace(
        "## [Unreleased]",
        f"## [Unreleased]\n\n## [{version}] - {today}",
        1,
    )
    CHANGELOG.write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: release.py <x.y.z>", file=sys.stderr)
        return 2
    version = argv[1].lstrip("v")
    if not SEMVER.match(version):
        print(f"{version!r} is not a semantic version", file=sys.stderr)
        return 2

    bump_manifest(version)
    bump_pyproject(version)
    bump_init(version)
    cut_changelog(version)

    print(f"Version set to {version} in:")
    for path in (MANIFEST, PYPROJECT, INIT, CHANGELOG):
        print(f"  {path.relative_to(REPO)}")
    print("\nNext steps (nothing has been committed or pushed):")
    print("  1. Review the changelog entry and `git diff`")
    print("  2. make all")
    print(f"  3. git commit -am 'release: v{version}'")
    print(f"  4. git tag -s v{version} -m 'v{version}'")
    print(f"  5. git push origin main && git push origin v{version}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
