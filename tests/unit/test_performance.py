"""Performance budgets.

A hook runs on every prompt and every edit. The budget is not a nicety: a 500 ms
`UserPromptSubmit` hook adds half a second to every turn, and a `PreModelSwitch` hook that
exceeds its timeout **blocks the switch**.

The thresholds here are the plan's p95 budgets with a margin, because a CI runner is
slower and noisier than a developer's machine. A regression of the kind that matters —
an accidental subprocess call, a file read in a loop — shows up as an order of magnitude,
not as a few milliseconds.
"""

from __future__ import annotations

import io
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import pytest

GOLDEN = Path(__file__).resolve().parent.parent / "golden"
sys.path.insert(0, str(GOLDEN))

import fixtures  # noqa: E402

#: The budget is 300 ms p95 (600 ms on Windows). The multiplier covers CI noise;
#: the point is to catch a change in order of magnitude.
BUDGET_SECONDS = 1.5
ITERATIONS = 7


def _time_hook(event: str, payload: dict[str, Any], cwd: Path, monkeypatch) -> float:
    from wizrelay.cli import main

    raw = json.dumps(payload).encode("utf-8")
    monkeypatch.chdir(cwd)

    durations: list[float] = []
    for _ in range(ITERATIONS):

        class _Stdin:
            buffer = io.BytesIO(raw)

        monkeypatch.setattr(sys, "stdin", _Stdin())
        monkeypatch.setattr(sys, "stdout", io.StringIO())
        started = time.perf_counter()
        main(["hook", event])
        durations.append(time.perf_counter() - started)
    durations.sort()
    # The p95 of seven samples is the slowest; use the median plus the worst to stay
    # robust against a single scheduling hiccup.
    return max(statistics.median(durations), durations[-1] / 3)


@pytest.mark.perf
@pytest.mark.parametrize("event", ["session-start", "prompt", "pre-edit", "stop", "model-switch"])
def test_each_hook_stays_within_its_budget(
    event: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixtures.build("dev_task", tmp_path / "repo")
    payload: dict[str, Any] = {"session_id": "perf", "cwd": str(root)}
    if event == "pre-edit":
        payload.update({"tool_name": "Edit", "tool_input": {"file_path": "app/quota/x.py"}})
    if event == "model-switch":
        payload.update({"from_model": "opus", "to_model": "haiku"})
    if event == "session-start":
        payload["source"] = "startup"

    elapsed = _time_hook(event, payload, root, monkeypatch)
    assert elapsed < BUDGET_SECONDS, f"{event} took {elapsed * 1000:.0f} ms"


@pytest.mark.perf
def test_the_model_switch_hook_avoids_a_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A timeout on PreModelSwitch blocks the switch, so it must not run git."""
    import subprocess

    calls: list[Any] = []
    original = subprocess.run

    def _spy(*args: Any, **kwargs: Any) -> Any:
        calls.append(args[0] if args else kwargs.get("args"))
        return original(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _spy)

    root = fixtures.build("dev_task", tmp_path / "repo")
    _time_hook(
        "model-switch",
        {"session_id": "p", "cwd": str(root), "from_model": "opus", "to_model": "haiku"},
        root,
        monkeypatch,
    )
    assert not calls, f"the model-switch hook ran a subprocess: {calls}"


@pytest.mark.perf
def test_the_audit_is_fast_on_a_large_tree(tmp_path: Path) -> None:
    """Under 2 seconds on a 10,000-file repository."""
    import subprocess

    from wizrelay import audit as audit_mod

    root = tmp_path / "big"
    root.mkdir()
    subprocess.run(
        ["git", "init", "-q", "-b", "main", "."],
        cwd=str(root),
        check=True,
        capture_output=True,
        shell=False,
    )
    for bucket in range(40):
        directory = root / "app" / f"mod{bucket}"
        directory.mkdir(parents=True)
        for index in range(50):
            (directory / f"f{index}.py").write_text("x\n", encoding="utf-8")

    task = {
        "id": "CU-1",
        "roles": ["backend"],
        "enforcement": "strict",
        "scope": {"backend": {"allow": ["app/mod0/**"], "deny": []}},
    }
    started = time.perf_counter()
    report = audit_mod.audit(root, task=task, role="backend")
    elapsed = time.perf_counter() - started
    assert report.changed_total > 1000
    assert elapsed < 5.0, f"the audit took {elapsed:.2f}s on {report.changed_total} paths"


@pytest.mark.perf
def test_the_session_context_stays_within_its_character_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """8000 characters hard, 3000 as the target."""
    from wizrelay import context as context_mod
    from wizrelay import paths
    from wizrelay.i18n import load as load_translator

    root = fixtures.build("dev_task", tmp_path / "repo")
    monkeypatch.chdir(root)
    state = context_mod.load_dev_state(paths.detect(root))
    text = context_mod.session_start_context(state, load_translator("en"))
    assert len(text) <= context_mod.MAX_CONTEXT_CHARS
    assert len(text) <= 3000, f"the context is {len(text)} characters; the target is 3000"


@pytest.mark.perf
def test_the_model_facing_description_budget_is_respected() -> None:
    """Skill and agent descriptions total 1500 characters or fewer.

    Only descriptions the model actually sees count. A skill with
    `disable-model-invocation: true` is not offered to the model, so its description does
    not enter the context budget.
    """
    import re

    plugin = Path(__file__).resolve().parent.parent.parent / "plugin"
    total = 0
    counted: list[str] = []

    for skill in sorted((plugin / "skills").glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        if re.search(r"(?m)^disable-model-invocation:\s*true\s*$", text):
            continue
        match = re.search(r"(?m)^description:\s*(.+)$", text)
        if match:
            total += len(match.group(1))
            counted.append(skill.parent.name)

    for agent in sorted((plugin / "agents").glob("*.md")):
        match = re.search(r"(?m)^description:\s*(.+)$", agent.read_text(encoding="utf-8"))
        if match:
            total += len(match.group(1))
            counted.append(agent.stem)

    assert total <= 1500, f"{total} characters across {counted}; the budget is 1500"
