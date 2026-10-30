"""The hook contract, locked.

Every case is a directory holding `input.json` and `expected.json`. `input.json` names a
repository fixture and the event payload; `expected.json` states what the handler must
print.

Why the contract lives in data rather than in Python: a behaviour change then shows up as a
diff in a file whose only purpose is to describe behaviour. The rule is that a hook
change appears in a golden test *first*, and that is only enforceable if the expectation is
easy to read and hard to fudge.

Expectation keys:

``empty``
    No output at all. This is what invariant I5 requires in an unmarked directory, and
    what "no decision" means for `pre-edit`.
``decision`` / ``reason_contains``
    `hookSpecificOutput.permissionDecision` and substrings of its reason.
``contains`` / ``absent`` / ``max_chars``
    Applied to `additionalContext`.
``keys`` / ``absent_keys``
    Top-level keys that must be present or absent, such as `sessionTitle`.
``system_message_contains``
    Substrings of `systemMessage`.
``text_matches``
    A regex for a plain-text response, which is what `UserPromptSubmit` returns.
"""

from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

GOLDEN_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(GOLDEN_ROOT))

import fixtures  # noqa: E402 - the path has to be set up first

CASES: list[Path] = sorted(path.parent for path in GOLDEN_ROOT.rglob("input.json"))


def _case_id(path: Path) -> str:
    return f"{path.parent.name}/{path.name}"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(event: str, payload: Any, cwd: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Run one hook handler in-process and return exactly what it wrote to stdout."""
    from wizrelay.cli import main

    raw = (
        b"not json at all" if payload == "__RAW_NOT_JSON__" else json.dumps(payload).encode("utf-8")
    )

    class _Stdin:
        buffer = io.BytesIO(raw)

    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "stdin", _Stdin())

    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    code = main(["hook", event])
    assert code == 0, f"a hook must always exit 0; {event} exited {code}"
    return out.getvalue()


@pytest.mark.parametrize("case_dir", CASES, ids=_case_id)
def test_golden_case(case_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = _load(case_dir / "input.json")
    expected = _load(case_dir / "expected.json")

    root = fixtures.build(spec["fixture"], tmp_path / "repo")

    payload = spec["payload"]
    if isinstance(payload, dict):
        payload = dict(payload)
        payload.setdefault("cwd", str(root))

    stdout = _run(spec["event"], payload, root, monkeypatch)

    if expected.get("empty"):
        assert stdout == "", f"{_case_id(case_dir)} must produce no output, got {stdout!r}"
        return

    assert stdout.strip(), f"{_case_id(case_dir)} produced no output"

    if "text_matches" in expected:
        line = stdout.strip()
        assert re.match(expected["text_matches"], line), (
            f"{line!r} does not match {expected['text_matches']!r}"
        )
        if "max_chars" in expected:
            assert len(line) <= expected["max_chars"]
        return

    document = json.loads(stdout)

    for key in expected.get("keys", []):
        assert key in document, f"{key} is missing from the response"
    for key in expected.get("absent_keys", []):
        assert key not in document, f"{key} must not be present"

    specific = document.get("hookSpecificOutput") or {}

    if "decision" in expected:
        assert specific.get("permissionDecision") == expected["decision"]
        reason = specific.get("permissionDecisionReason") or ""
        for needle in expected.get("reason_contains", []):
            assert needle in reason, f"{needle!r} is missing from the reason: {reason!r}"
        # A deny or ask with no reason tells the user nothing.
        assert reason, "a decision must carry a reason"

    context = specific.get("additionalContext") or ""
    for needle in expected.get("contains", []):
        assert needle in context, f"{needle!r} is missing from the context"
    for needle in expected.get("absent", []):
        assert needle not in context, f"{needle!r} should not be in the context"
    if "max_chars" in expected and context:
        assert len(context) <= expected["max_chars"], (
            f"context is {len(context)} characters; the cap is {expected['max_chars']}"
        )

    message = document.get("systemMessage") or ""
    for needle in expected.get("system_message_contains", []):
        assert needle in message, f"{needle!r} is missing from the systemMessage"

    # Nothing in the catalogue may be missing: `«key»` is the visible fallback.
    assert "«" not in stdout, "a missing i18n key leaked into a hook response"


# --------------------------------------------------------------------------------------
# Contract-wide properties, not tied to one case
# --------------------------------------------------------------------------------------


def test_every_event_has_cases() -> None:
    events = {case.parent.name for case in CASES}
    assert events == {"session-start", "prompt", "pre-edit", "stop", "model-switch"}


def test_every_fixture_is_used() -> None:
    used = {_load(case / "input.json")["fixture"] for case in CASES}
    unused = sorted(set(fixtures.BUILDERS) - used)
    assert not unused, f"fixtures defined but never exercised: {unused}"


def test_the_stop_hook_never_blocks() -> None:
    """Appendix B4: `Stop` must never return `decision: block`."""
    for case in CASES:
        if case.parent.name != "stop":
            continue
        expected = _load(case / "expected.json")
        assert expected.get("decision") is None
        assert "decision" not in expected.get("keys", [])


def test_every_pre_edit_decision_is_deny_or_ask() -> None:
    """`allow` would grant permission the user never gave."""
    for case in CASES:
        if case.parent.name != "pre-edit":
            continue
        decision = _load(case / "expected.json").get("decision")
        assert decision in (None, "deny", "ask"), f"{_case_id(case)} expects {decision}"


def test_no_hook_writes_outside_the_plugin_data_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In an unmarked directory nothing is written anywhere."""
    root = fixtures.build("silent", tmp_path / "repo")
    before = set(tmp_path.rglob("*"))
    for event in ("session-start", "prompt", "pre-edit", "stop", "model-switch"):
        _run(event, {"session_id": "s", "cwd": str(root)}, root, monkeypatch)
    after = set(tmp_path.rglob("*"))
    created = {p for p in after - before if "plugin-data" not in p.parts}
    assert not created, f"an unmarked directory had files written into it: {sorted(created)}"


def test_session_start_writes_a_heartbeat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Invariant I13: the heartbeat is how `brief` detects hooks that never ran."""
    from wizrelay import context as context_mod

    root = fixtures.build("dev_task", tmp_path / "repo")
    assert context_mod.heartbeat_seen("hb-session") is False
    _run("session-start", {"session_id": "hb-session", "cwd": str(root)}, root, monkeypatch)
    assert context_mod.heartbeat_seen("hb-session") is True


def test_a_heartbeat_is_written_even_in_an_unmarked_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The heartbeat records that the hook *ran*; whether the directory is connected is a
    # separate question. Writing it only for connected repositories would make the guard
    # warning fire in every unconnected one.
    from wizrelay import context as context_mod

    root = fixtures.build("silent", tmp_path / "repo")
    _run("session-start", {"session_id": "hb-plain", "cwd": str(root)}, root, monkeypatch)
    assert context_mod.heartbeat_seen("hb-plain") is True


def test_old_heartbeats_are_pruned(tmp_path: Path) -> None:
    import os
    import time

    from wizrelay import context as context_mod
    from wizrelay import paths

    context_mod.heartbeat_write("fresh")
    context_mod.heartbeat_write("ancient")
    stale = paths.heartbeat_dir() / "ancient"
    old = time.time() - 8 * 24 * 60 * 60
    os.utime(stale, (old, old))

    assert context_mod.heartbeat_prune() == 1
    assert context_mod.heartbeat_seen("fresh") is True
    assert context_mod.heartbeat_seen("ancient") is False
