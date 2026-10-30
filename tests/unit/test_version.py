"""One version, three files."""

from __future__ import annotations

import json
import re
from pathlib import Path

import wizrelay

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_manifest_pyproject_and_package_agree() -> None:
    manifest = json.loads(
        (REPO_ROOT / "plugin" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "([^"]+)"$', pyproject)
    assert match, "pyproject.toml has no version line"

    assert manifest["version"] == wizrelay.__version__ == match.group(1), (
        f"plugin.json={manifest['version']} __init__={wizrelay.__version__} "
        f"pyproject={match.group(1)}. `make release VERSION=x.y.z` writes all three."
    )


def test_marketplace_entry_does_not_set_a_version() -> None:
    # plugin.json wins over the entry, and `claude plugin validate` warns when both set
    # it.
    marketplace = json.loads(
        (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    for entry in marketplace["plugins"]:
        assert "version" not in entry, f"{entry['name']} sets a version in the entry"


def test_marketplace_entry_name_matches_the_manifest() -> None:
    """R16: two plugins with one manifest name means one of them loses its hooks."""
    manifest = json.loads(
        (REPO_ROOT / "plugin" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    marketplace = json.loads(
        (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    names = {entry["name"] for entry in marketplace["plugins"]}
    assert manifest["name"] in names
