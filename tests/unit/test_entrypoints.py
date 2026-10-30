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


@pytest.mark.parametrize("launcher", ["wizrelay.py", "wizrelay"])
def test_the_launcher_survives_the_library_already_being_on_the_path(launcher: str) -> None:
    """An editable install puts `plugin/lib` on `sys.path` before the launcher runs.

    The launcher's own directory holds a `wizrelay.py`, and a script's directory comes
    first on `sys.path`. If the launcher only inserted the library when it was absent, this
    is the case where it would skip the insert and `import wizrelay` would find the
    launcher instead of the package, failing with `'wizrelay' is not a package`.
    """
    if launcher == "wizrelay" and sys.platform == "win32":
        pytest.skip("the sh launcher needs a POSIX shell")
    target = PLUGIN / "bin" / launcher
    command = [sys.executable, str(target)] if launcher.endswith(".py") else [str(target)]
    result = subprocess.run(
        [*command, "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        shell=False,
        check=False,
        env={**os.environ, "PYTHONPATH": str(PLUGIN / "lib")},
    )
    assert result.returncode == 0, result.stderr
    assert "wizrelay" in result.stdout


def test_the_bundled_library_wins_over_an_installed_one(tmp_path: Path) -> None:
    """The bundled copy has to win: its version is the one the hook contract matches."""
    impostor = tmp_path / "wizrelay"
    impostor.mkdir()
    (impostor / "__init__.py").write_text("", encoding="utf-8")
    (impostor / "cli.py").write_text(
        'def main(argv=None):\n    print("impostor")\n    return 0\n', encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(PLUGIN / "bin" / "wizrelay.py"), "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        shell=False,
        check=False,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
    )
    assert result.returncode == 0, result.stderr
    assert "impostor" not in result.stdout, "an installed copy shadowed the bundled one"
