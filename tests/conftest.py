"""Shared fixtures.

Two rules hold across the whole suite:

* **No network.** Every hub is a local git repository. A test that needs a hub builds one.
* **No shared state.** `isolate_environment` redirects the cache and plugin-data
  directories into the test's own `tmp_path`, so a test can never read a heartbeat or a
  hub clone another test left behind, and a developer's real `~/.cache` is never touched.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPO_ROOT / "plugin" / "lib"

# The package is imported from the plugin directory, so the suite runs against the files
# that ship rather than against an installed copy.
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))


@pytest.fixture(autouse=True)
def isolate_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point every per-user directory at this test's tmp_path."""
    monkeypatch.setenv("WIZRELAY_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "plugin-data"))
    monkeypatch.delenv("WIZRELAY_DEBUG", raising=False)
    monkeypatch.delenv("WIZRELAY_PYTHON", raising=False)
    monkeypatch.delenv("WIZRELAY_TRACKERS_DIR", raising=False)
    # Deterministic git, and no dependency on the developer's own identity.
    monkeypatch.setenv("GIT_AUTHOR_NAME", "wizrelay-test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "wizrelay-test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@example.invalid")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def git(*args: str, cwd: Path) -> None:
    """Run git, failing the test loudly on error."""
    subprocess.run(
        ["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True, shell=False
    )


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git("init", "-q", "-b", "main", ".", cwd=path)
    return path


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# Package content used by many tests
# --------------------------------------------------------------------------------------

TASK_ID = "CU-86c1abcd"
SLUG = "tenant-quota"
FOLDER = f"{TASK_ID}-{SLUG}"


def task_document(
    *,
    version: int = 1,
    status: str = "published",
    roles: Optional[list[str]] = None,
    enforcement: str = "strict",
    signals: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    roles = roles or ["backend"]
    scope = {
        "backend": {
            "allow": ["app/quota/**", "tests/quota/**"],
            "deny": ["app/billing/**"],
        }
    }
    if "frontend" in roles:
        scope["frontend"] = {"allow": ["src/features/quota/**"], "deny": []}
    return {
        "schema_version": 1,
        "id": TASK_ID,
        "tracker": {"type": "clickup", "ref": "86c1abcd"},
        "title": "Tenant quota",
        "slug": SLUG,
        "version": version,
        "status": status,
        "updated_at": "2026-10-30",
        "roles": roles,
        "repos": {"backend": "acme/api-service"},
        "enforcement": enforcement,
        "scope": scope,
        "routing": {
            "signals": signals or {"complexity": "medium", "risk": "high", "ambiguity": "low"},
            "role_signals": {},
            "overrides": {},
        },
        "changelog": [{"version": version, "date": "2026-10-30", "summary": "Published"}],
    }


ACCEPTANCE = """# Acceptance criteria

## AC-1 [backend] A tenant at its limit is rejected

Given a tenant at its daily limit
When a send is attempted
Then the request is rejected with 429
Verification: `pytest -q tests/quota`

## AC-2 [] Counters reset daily

Given a counter from yesterday
When the day rolls over
Then the counter reads zero
Verification: `pytest -q tests/quota/test_reset.py`
"""

DECISIONS = """# Decisions

## D-001 Fail open when the counter store is unavailable (v1, 2026-10-30)

- Question: What happens when Redis is unreachable?
- Decision: Allow the request and log a warning.
- Rationale: A quota is a cost control, not a safety control.
- Impact: AC-1 applies only when the counter is readable.
"""


@pytest.fixture
def hub(tmp_path: Path) -> Path:
    """A hub repository with one published package, committed."""
    root = init_repo(tmp_path / "hub")
    write_json(
        root / "wizrelay-hub.json",
        {
            "schema_version": 1,
            "name": "test-hub",
            "language": "en",
            "tracker": {"type": "clickup", "id_prefix": "CU-"},
            "roles": ["backend", "frontend"],
            "default_branch": "main",
            "base_ref": "origin/main",
        },
    )
    pkg = root / "tasks" / FOLDER
    pkg.mkdir(parents=True)
    write_json(pkg / "task.json", task_document())
    (pkg / "research.md").write_text(
        "# Research\n\nEvidence at `app/quota/x.py:1`.\n", encoding="utf-8"
    )
    (pkg / "scope.md").write_text("# Scope\n\nbackend: the quota module.\n", encoding="utf-8")
    (pkg / "acceptance.md").write_text(ACCEPTANCE, encoding="utf-8")
    (pkg / "decisions.md").write_text(DECISIONS, encoding="utf-8")
    (pkg / "roles").mkdir()
    (pkg / "roles" / "backend.md").write_text(
        "# backend\n\nStart at `app/quota/`.\n", encoding="utf-8"
    )
    # Private to the hub: must never reach a developer repository (invariant I8).
    (pkg / ".validation.md").write_text("# private\n", encoding="utf-8")
    git("add", "-A", cwd=root)
    git("commit", "-qm", "publish", cwd=root)
    return root


@pytest.fixture
def dev_repo(tmp_path: Path, hub: Path) -> Path:
    """A developer repository connected to `hub`, with a profile but nothing pulled."""
    root = init_repo(tmp_path / "backend")
    for directory in ("app/quota", "app/billing", "tests/quota", "src"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / "app" / "quota" / "__init__.py").write_text("", encoding="utf-8")
    (root / "README.md").write_text("# Backend\n", encoding="utf-8")
    config_dir = root / ".wizrelay"
    write_json(
        config_dir / "config.json",
        {
            "schema_version": 1,
            "hub": {"path": str(hub), "branch": "main"},
            "role": "backend",
            "tracker": {"type": "clickup", "id_prefix": "CU-"},
            "language": "en",
            "base_ref": "origin/main",
            "prompt_anchor": True,
            "session_title": True,
            "fetch_ttl_minutes": 10,
        },
    )
    write_json(
        config_dir / "profile.json",
        {
            "schema_version": 1,
            "stack": "Python 3.12",
            "commands": {"test": "pytest -q", "test_targeted": "pytest -q {path}"},
            "codebase_size": "medium",
            "test_maturity": "medium",
            "critical_paths": [],
            "legacy_paths": [],
            "incidental_allow": [],
        },
    )
    (config_dir / "tasks").mkdir(parents=True, exist_ok=True)
    git("add", "-A", cwd=root)
    git("commit", "-qm", "init", cwd=root)
    return root


@pytest.fixture
def run_cli(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> Callable[..., Any]:
    """Call `wizrelay` in-process and return `(exit_code, stdout, stderr)`.

    In-process rather than through a subprocess so coverage sees the code and a failure
    produces a real traceback.
    """
    from wizrelay.cli import main

    def _run(*args: str, cwd: Optional[Path] = None) -> Any:
        if cwd is not None:
            monkeypatch.chdir(cwd)
        capsys.readouterr()
        code = main(list(args))
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return _run


@pytest.fixture
def run_hook(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> Callable[..., Any]:
    """Feed an event payload to a hook handler and return `(exit_code, stdout)`."""
    import io

    from wizrelay.cli import main

    def _run(event: str, payload: Mapping[str, Any], *, cwd: Optional[Path] = None) -> Any:
        if cwd is not None:
            monkeypatch.chdir(cwd)
        raw = json.dumps(payload).encode("utf-8")

        class _Stdin:
            buffer = io.BytesIO(raw)

        monkeypatch.setattr(sys, "stdin", _Stdin())
        capsys.readouterr()
        code = main(["hook", event])
        return code, capsys.readouterr().out

    return _run
