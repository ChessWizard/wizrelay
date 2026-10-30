"""Repository states the golden cases run against.

A golden case names a fixture rather than describing one, so twenty cases share seven
repository states and a change to a state shows up in every case that depends on it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

TASK_ID = "CU-86c1abcd"
FOLDER = f"{TASK_ID}-tenant-quota"

ACCEPTANCE = """# Acceptance criteria

## AC-1 [backend] A tenant at its limit is rejected

Given a tenant at its daily limit
When a send is attempted
Then the request is rejected with 429
Verification: `pytest -q tests/quota`
"""


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _task(
    *, enforcement: str = "strict", roles=("backend",), scope_roles=("backend",)
) -> dict[str, Any]:
    scope = {
        role: {"allow": ["app/quota/**", "tests/quota/**"], "deny": ["app/billing/**"]}
        for role in scope_roles
    }
    return {
        "schema_version": 1,
        "id": TASK_ID,
        "tracker": {"type": "clickup", "ref": "86c1abcd"},
        "title": "Tenant quota",
        "slug": "tenant-quota",
        "version": 2,
        "status": "published",
        "updated_at": "2026-10-30",
        "roles": list(roles),
        "enforcement": enforcement,
        "scope": scope,
        "routing": {
            "signals": {"complexity": "medium", "risk": "high", "ambiguity": "low"},
            "role_signals": {},
            "overrides": {},
        },
    }


def _base_repo(root: Path) -> Path:
    for directory in ("app/quota", "app/billing", "tests/quota", "src"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# Project\n", encoding="utf-8")
    (root / "poetry.lock").write_text("lock\n", encoding="utf-8")
    return root


def _config(
    root: Path, *, role: str = "backend", language: str = "en", anchor: bool = True
) -> None:
    _write_json(
        root / ".wizrelay" / "config.json",
        {
            "schema_version": 1,
            "role": role,
            "language": language,
            "prompt_anchor": anchor,
            "session_title": True,
            "base_ref": "origin/main",
            "tracker": {"type": "clickup", "id_prefix": "CU-"},
        },
    )
    _write_json(
        root / ".wizrelay" / "profile.json",
        {
            "schema_version": 1,
            "stack": "Python 3.12",
            "commands": {"test": "pytest -q"},
            "codebase_size": "medium",
            "test_maturity": "medium",
        },
    )
    (root / ".wizrelay" / "tasks").mkdir(parents=True, exist_ok=True)


def _install_task(root: Path, task: dict[str, Any], *, with_lock: bool = True) -> Path:
    package = root / ".wizrelay" / "tasks" / FOLDER
    (package / "roles").mkdir(parents=True, exist_ok=True)
    _write_json(package / "task.json", task)
    (package / "research.md").write_text(
        "# Research\n\nSee `app/quota/x.py:1`.\n", encoding="utf-8"
    )
    (package / "scope.md").write_text("# Scope\n\nbackend only.\n", encoding="utf-8")
    (package / "acceptance.md").write_text(ACCEPTANCE, encoding="utf-8")
    (package / "decisions.md").write_text(
        "# Decisions\n\n## D-001 A choice (v1, 2026-10-30)\n", encoding="utf-8"
    )
    (package / "roles" / "backend.md").write_text(
        "# backend\n\nStart at `app/quota/`.\n", encoding="utf-8"
    )
    (package / "plan.md").write_text(
        "# Plan\n\n- [x] AC-1 done\n- [ ] AC-1 tests\n", encoding="utf-8"
    )
    (package / "questions.md").write_text(
        "# Questions\n\n## Q-001 Open one\n\nStatus: OPEN\n", encoding="utf-8"
    )

    if with_lock:
        from wizrelay import lock
        from wizrelay import package as package_mod

        digests = {
            relative: lock.digest_file(package / relative)
            for relative in package_mod.researcher_files(package)
        }
        document = lock.build(
            task_id=TASK_ID,
            folder=FOLDER,
            version=int(task["version"]),
            files=digests,
            pulled_at="2026-10-30T09:00:00+00:00",
            title=task["title"],
            hub_id="test-hub-00000000",
            role="backend",
            status="published",
            routing={
                "tier": "T2-standard",
                "score": 6,
                "phases": {
                    "plan": {"model": "opus", "effort": "high"},
                    "implement": {"model": "sonnet", "effort": "high"},
                    "verify": {"model": "sonnet", "effort": "high"},
                    "ask": {"model": "sonnet", "effort": "low"},
                },
                "launch": "claude --model opusplan --effort high",
            },
        )
        (package / lock.LOCK_FILENAME).write_text(lock.serialize(document), encoding="utf-8")

    (root / ".wizrelay" / ".active-task").write_text(FOLDER + "\n", encoding="utf-8")
    return package


# --------------------------------------------------------------------------------------
# The named fixtures
# --------------------------------------------------------------------------------------


def silent(root: Path) -> Path:
    """A plain directory: no marker, so the plugin must do nothing (invariant I5)."""
    _base_repo(root)
    return root


def dev_no_task(root: Path) -> Path:
    _base_repo(root)
    _config(root)
    return root


def dev_task(root: Path) -> Path:
    _base_repo(root)
    _config(root)
    _install_task(root, _task())
    return root


def dev_task_ask(root: Path) -> Path:
    _base_repo(root)
    _config(root)
    _install_task(root, _task(enforcement="ask"))
    return root


def dev_task_off(root: Path) -> Path:
    _base_repo(root)
    _config(root)
    _install_task(root, _task(enforcement="off"))
    return root


def dev_no_scope_for_role(root: Path) -> Path:
    """The task names the role but defines no scope for it."""
    _base_repo(root)
    _config(root, role="mobile")
    _install_task(root, _task(roles=("backend", "mobile"), scope_roles=("backend",)))
    return root


def dev_no_anchor(root: Path) -> Path:
    _base_repo(root)
    _config(root, anchor=False)
    _install_task(root, _task())
    return root


def dev_task_turkish(root: Path) -> Path:
    _base_repo(root)
    _config(root, language="tr")
    _install_task(root, _task())
    return root


def dev_task_stale(root: Path) -> Path:
    """The lock records an older version than the package: `sync` is needed."""
    _base_repo(root)
    _config(root)
    package = _install_task(root, _task())
    from wizrelay import lock

    document = lock.load(package / lock.LOCK_FILENAME) or {}
    document["version"] = 1
    (package / lock.LOCK_FILENAME).write_text(lock.serialize(document), encoding="utf-8")
    return root


def dev_task_tampered(root: Path) -> Path:
    """A researcher file no longer matches the lock."""
    _base_repo(root)
    _config(root)
    package = _install_task(root, _task())
    (package / "acceptance.md").write_text(ACCEPTANCE + "\nEdited locally.\n", encoding="utf-8")
    return root


def hub(root: Path) -> Path:
    _write_json(
        root / "wizrelay-hub.json",
        {
            "schema_version": 1,
            "name": "golden-hub",
            "language": "en",
            "tracker": {"type": "clickup"},
            "roles": ["backend"],
        },
    )
    package = root / "tasks" / FOLDER
    package.mkdir(parents=True)
    _write_json(package / "task.json", _task())
    (package / "acceptance.md").write_text(ACCEPTANCE, encoding="utf-8")
    return root


def hub_empty(root: Path) -> Path:
    _write_json(
        root / "wizrelay-hub.json",
        {"schema_version": 1, "name": "empty-hub", "language": "en"},
    )
    (root / "tasks").mkdir(parents=True)
    return root


BUILDERS: dict[str, Callable[[Path], Path]] = {
    "silent": silent,
    "dev_no_task": dev_no_task,
    "dev_task": dev_task,
    "dev_task_ask": dev_task_ask,
    "dev_task_off": dev_task_off,
    "dev_no_scope_for_role": dev_no_scope_for_role,
    "dev_no_anchor": dev_no_anchor,
    "dev_task_turkish": dev_task_turkish,
    "dev_task_stale": dev_task_stale,
    "dev_task_tampered": dev_task_tampered,
    "hub": hub,
    "hub_empty": hub_empty,
}


def build(name: str, root: Path) -> Path:
    try:
        builder = BUILDERS[name]
    except KeyError:  # pragma: no cover - a typo in a golden case
        raise AssertionError(
            f"unknown fixture {name!r}; known: {', '.join(sorted(BUILDERS))}"
        ) from None
    root.mkdir(parents=True, exist_ok=True)
    return builder(root)
