#!/usr/bin/env python3
"""Structural checks on plugin/ that do not need the `claude` CLI.

`claude plugin validate` is authoritative, but it is not always installed —
CI runners and this repository's own development machines may not have it. This script
re-checks the rules that matter most for wizrelay and that are cheap to verify from the
documented manifest contract:

* plugin.json parses, declares a kebab-case `name`, a `version` and a `description`
* the name is not one Claude Code reserves
* no CLAUDE.md sits at the plugin root (Claude Code would not load it and validate warns)
* every skill is `skills/<name>/SKILL.md` with parseable frontmatter and a `description`
* every agent has `name` and `description` and sets none of the fields plugins ignore
* hooks/hooks.json has the top-level "hooks" wrapper and only documented handler fields
* the marketplace entry name matches the manifest name
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugin"

KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED_PREFIXES = ("claude-", "anthropic-", "anthropics-", "cc-plugin-")
RESERVED_EXACT = {"claude", "anthropic", "anthropics", "claude-code", "claude-mods"}

# Fields Claude Code ignores on a plugin-provided agent.
AGENT_IGNORED = ("permissionMode", "hooks", "mcpServers", "initialPrompt")
# Handler fields documented for a command hook.
HOOK_HANDLER_FIELDS = {
    "type",
    "command",
    "args",
    "timeout",
    "onFailure",
    "if",
    "async",
    "asyncRewake",
    "shell",
    "once",
}
HOOK_EVENTS = {
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "PreModelSwitch",
    "PostModelSwitch",
    "SessionEnd",
    "PreCompact",
    "PostCompact",
}

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        err(f"{path.relative_to(REPO)}: not found")
    except json.JSONDecodeError as exc:
        err(f"{path.relative_to(REPO)}: invalid JSON at line {exc.lineno}: {exc.msg}")
    return None


def split_frontmatter(text: str) -> dict:
    """Parse the flat `key: value` frontmatter a SKILL.md or agent file uses.

    Deliberately not a YAML parser: the runtime is stdlib-only, and every field this
    project uses is a scalar or a comma-separated list on one line.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out: dict = {}
    for line in text[3:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip().strip("\"'")
    return out


def check_manifest() -> str:
    manifest = read_json(PLUGIN / ".claude-plugin" / "plugin.json")
    if not isinstance(manifest, dict):
        return ""
    name = str(manifest.get("name") or "")
    if not name:
        err("plugin.json: `name` is required")
    elif not KEBAB.match(name):
        err(f"plugin.json: `name` {name!r} is not kebab-case")
    lowered = name.lower()
    if lowered in RESERVED_EXACT or lowered.startswith(RESERVED_PREFIXES):
        err(f"plugin.json: `name` {name!r} is reserved by Claude Code")
    elif any(word in lowered for word in ("claude", "anthropic")):
        warn(f"plugin.json: `name` {name!r} reads as one of Anthropic's own")
    for key in ("version", "description"):
        if not manifest.get(key):
            warn(f"plugin.json: `{key}` is missing; `--strict` would fail")
    if (PLUGIN / "CLAUDE.md").exists():
        err("plugin/CLAUDE.md is not loaded as context; move the content into a skill")
    return name


def check_skills() -> None:
    root = PLUGIN / "skills"
    if not root.is_dir():
        err("plugin/skills/ not found")
        return
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            warn(f"plugin/skills/{entry.name}: not a directory, so it is not a skill")
            continue
        skill = entry / "SKILL.md"
        if not skill.is_file():
            err(f"plugin/skills/{entry.name}/SKILL.md not found")
            continue
        text = skill.read_text(encoding="utf-8")
        front = split_frontmatter(text)
        if not front:
            err(f"{skill.relative_to(REPO)}: frontmatter missing or unparseable")
            continue
        if not front.get("description"):
            err(f"{skill.relative_to(REPO)}: `description` is required")
        lines = text.splitlines()
        if len(lines) > 200:
            err(f"{skill.relative_to(REPO)}: {len(lines)} lines, limit is 200")
        effort = front.get("effort")
        if effort and effort not in {"low", "medium", "high", "xhigh", "max"}:
            err(f"{skill.relative_to(REPO)}: effort {effort!r} is not a documented level")
        if front.get("background") and front.get("background") not in {"true", "false"}:
            err(f"{skill.relative_to(REPO)}: background must be true or false")
        if front.get("agent") and front.get("context") != "fork":
            warn(f"{skill.relative_to(REPO)}: `agent` has no effect without `context: fork`")


def check_agents() -> None:
    root = PLUGIN / "agents"
    if not root.is_dir():
        err("plugin/agents/ not found")
        return
    for path in sorted(root.glob("*.md")):
        front = split_frontmatter(path.read_text(encoding="utf-8"))
        if not front:
            err(f"{path.relative_to(REPO)}: frontmatter missing or unparseable")
            continue
        for key in ("name", "description"):
            if not front.get(key):
                err(f"{path.relative_to(REPO)}: `{key}` is required")
        if ":" in str(front.get("name", "")):
            err(f"{path.relative_to(REPO)}: `name` cannot contain ':'")
        for key in AGENT_IGNORED:
            if key in front:
                err(f"{path.relative_to(REPO)}: `{key}` is ignored in a plugin agent")


def check_hooks() -> None:
    path = PLUGIN / "hooks" / "hooks.json"
    data = read_json(path)
    if not isinstance(data, dict):
        return
    if "hooks" not in data:
        err('plugin/hooks/hooks.json: the top-level "hooks" wrapper is required')
        return
    for event, groups in data["hooks"].items():
        if event not in HOOK_EVENTS:
            warn(f"hooks.json: {event!r} is not an event this project verified")
        if not isinstance(groups, list):
            err(f"hooks.json: {event} must be a list of matcher groups")
            continue
        for group in groups:
            for handler in group.get("hooks", []):
                unknown = set(handler) - HOOK_HANDLER_FIELDS
                if unknown:
                    err(f"hooks.json: {event}: unknown handler fields {sorted(unknown)}")
                if handler.get("type") != "command":
                    continue
                if "args" not in handler:
                    warn(
                        f"hooks.json: {event}: shell form in use; exec form (`args`) is "
                        "safer for substituted paths"
                    )
                if "timeout" not in handler:
                    warn(f"hooks.json: {event}: no explicit timeout")
                of = handler.get("onFailure")
                if of not in (None, "continue", "block"):
                    err(f"hooks.json: {event}: onFailure {of!r} is not continue or block")


def check_marketplace(plugin_name: str) -> None:
    data = read_json(REPO / ".claude-plugin" / "marketplace.json")
    if not isinstance(data, dict):
        return
    for key in ("name", "owner", "plugins"):
        if key not in data:
            err(f"marketplace.json: `{key}` is required")
    if not (data.get("owner") or {}).get("name"):
        err("marketplace.json: `owner.name` is required")
    for i, entry in enumerate(data.get("plugins") or []):
        source = entry.get("source")
        if isinstance(source, str) and not source.startswith("./"):
            err(f"marketplace.json: plugins[{i}].source must start with './'")
        if entry.get("version"):
            warn(f"marketplace.json: plugins[{i}] sets `version`; plugin.json wins, so remove it")
        if plugin_name and entry.get("name") != plugin_name:
            err(
                f"marketplace.json: plugins[{i}].name {entry.get('name')!r} does not match "
                f"plugin.json name {plugin_name!r}"
            )


def main() -> int:
    name = check_manifest()
    check_skills()
    check_agents()
    check_hooks()
    check_marketplace(name)

    for line in warnings:
        print(f"warning: {line}")
    for line in errors:
        print(f"error: {line}")
    if errors:
        print(f"\nstructure check FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"structure check passed with {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
