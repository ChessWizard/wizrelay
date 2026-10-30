"""The three entry points must stay in step."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PLUGIN = REPO_ROOT / "plugin"


def test_hook_launcher_exists_and_is_python() -> None:
    launcher = PLUGIN / "bin" / "wizrelay.py"
    assert launcher.is_file()
    text = launcher.read_text(encoding="utf-8")
    assert "from wizrelay.cli import main" in text
    assert "sys.path.insert(0" in text, (
        "the launcher has to put plugin/lib on sys.path: a plugin is never pip-installed"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="no POSIX permission bits")
def test_path_launcher_is_executable() -> None:
    launcher = PLUGIN / "bin" / "wizrelay"
    assert launcher.is_file()
    mode = launcher.stat().st_mode
    assert mode & stat.S_IXUSR, "plugin/bin/wizrelay must be executable to be on PATH"
    assert launcher.read_text(encoding="utf-8").startswith("#!/bin/sh")


def test_console_script_target_exists() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'wizrelay = "wizrelay.cli:main"' in pyproject
    from wizrelay.cli import main

    assert callable(main)


def test_module_runner_exists() -> None:
    from wizrelay import __main__

    assert hasattr(__main__, "main")


def test_hooks_json_uses_the_launcher_in_exec_form() -> None:
    import json

    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert "hooks" in hooks, "the top-level 'hooks' wrapper is required"
    for event, groups in hooks["hooks"].items():
        for group in groups:
            for handler in group["hooks"]:
                assert handler["type"] == "command"
                # Exec form: `args` present means no shell, so a plugin path containing a
                # space stays one argument.
                assert "args" in handler, f"{event} must use exec form"
                assert handler["command"] == "python3", f"{event} must run python3"
                assert handler["args"][0].startswith("${CLAUDE_PLUGIN_ROOT}/bin/wizrelay.py")
                assert "timeout" in handler, f"{event} must set an explicit timeout"


def test_only_pretooluse_fails_closed() -> None:
    """Edit protection fails closed; everything else fails open."""
    import json

    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    for event, groups in hooks.items():
        for group in groups:
            for handler in group["hooks"]:
                failure = handler.get("onFailure")
                if event == "PreToolUse":
                    assert failure == "block", "PreToolUse must fail closed"
                else:
                    assert failure in (None, "continue"), (
                        f"{event} must fail open: a session must never become unusable"
                    )


@pytest.mark.skipif(sys.platform == "win32", reason="the sh launcher needs a POSIX shell")
def test_the_path_launcher_actually_runs() -> None:
    result = subprocess.run(
        [str(PLUGIN / "bin" / "wizrelay"), "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        shell=False,
        check=False,
        env={**os.environ, "PATH": os.environ.get("PATH", "")},
    )
    assert result.returncode == 0, result.stderr
    assert "wizrelay" in result.stdout
