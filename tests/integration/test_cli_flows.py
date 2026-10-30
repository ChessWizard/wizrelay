"""CLI scenarios.

Every hub here is a local git repository: there is no network in this suite.
The CLI runs in-process so coverage sees it and a failure produces a real traceback.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from wizrelay import lock, package, paths

TASK_ID = "CU-86c1abcd"
FOLDER = f"{TASK_ID}-tenant-quota"


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=str(root), check=True, capture_output=True, text=True, shell=False
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------
# B2 #1 — init
# --------------------------------------------------------------------------------------


def test_init_creates_everything_and_is_idempotent(tmp_path: Path, run_cli, hub: Path) -> None:
    root = tmp_path / "fresh"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main", ".")

    code, out, _err = run_cli("init", "--role", "backend", "--hub-path", str(hub), cwd=root)
    assert code == 0
    for relative in (
        ".wizrelay/config.json",
        ".wizrelay/profile.json",
        ".wizrelay/PROTOCOL.md",
        ".wizrelay/tasks",
        "CLAUDE.md",
        ".gitignore",
        ".claude/settings.json",
    ):
        assert (root / relative).exists(), f"{relative} was not created"

    # The second run changes nothing.
    before = {
        p: p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git/" not in p.as_posix()
    }
    code, out, _err = run_cli("init", "--role", "backend", cwd=root)
    assert code == 0
    assert "nothing changed" in out
    after = {
        p: p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git/" not in p.as_posix()
    }
    assert before == after


def test_init_appends_to_claude_md_without_a_leading_blank_line(
    tmp_path: Path, run_cli, hub: Path
) -> None:
    root = tmp_path / "empty-claude"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main", ".")
    (root / "CLAUDE.md").write_text("", encoding="utf-8")

    run_cli("init", "--role", "backend", "--hub-path", str(hub), cwd=root)
    text = (root / "CLAUDE.md").read_text(encoding="utf-8")
    assert not text.startswith("\n"), "an empty CLAUDE.md must not gain a leading blank line"
    assert "@.wizrelay/PROTOCOL.md" in text


def test_init_preserves_existing_content(tmp_path: Path, run_cli, hub: Path) -> None:
    root = tmp_path / "existing"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main", ".")
    (root / "CLAUDE.md").write_text("# Project\n\nOur own rules.\n", encoding="utf-8")
    (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    (root / ".claude").mkdir()
    (root / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"allow": ["Bash(npm test)"]}}), encoding="utf-8"
    )

    run_cli("init", "--role", "backend", "--hub-path", str(hub), cwd=root)

    # Invariant I7: init adds, never replaces.
    assert "Our own rules." in (root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "node_modules/" in (root / ".gitignore").read_text(encoding="utf-8")
    settings = _read_json(root / ".claude" / "settings.json")
    assert settings["permissions"]["allow"] == ["Bash(npm test)"]
    assert any("acceptance.md" in rule for rule in settings["permissions"]["deny"])


def test_init_writes_edit_deny_rules_not_write_rules(tmp_path: Path, run_cli, hub: Path) -> None:
    # A `Write(path)` rule matches nothing at all; only `Edit(path)` works
    # .
    root = tmp_path / "deny"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main", ".")
    run_cli("init", "--role", "backend", "--hub-path", str(hub), cwd=root)
    rules = _read_json(root / ".claude" / "settings.json")["permissions"]["deny"]
    assert rules
    assert all(rule.startswith("Edit(") for rule in rules)
    assert all(rule.startswith("Edit(/.wizrelay/") for rule in rules)


def test_init_outside_a_git_repository_fails_with_guidance(tmp_path: Path, run_cli) -> None:
    code, _out, err = run_cli("init", cwd=tmp_path)
    assert code == 2
    assert "git init" in err


def test_init_registers_the_marketplace_when_asked(tmp_path: Path, run_cli, hub: Path) -> None:
    root = tmp_path / "mk"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main", ".")
    run_cli(
        "init",
        "--role",
        "backend",
        "--hub-path",
        str(hub),
        "--marketplace",
        "acme/wizrelay",
        cwd=root,
    )
    settings = _read_json(root / ".claude" / "settings.json")
    assert settings["extraKnownMarketplaces"]["wizrelay"]["source"]["repo"] == "acme/wizrelay"
    assert settings["enabledPlugins"]["wizrelay@wizrelay"] is True


# --------------------------------------------------------------------------------------
# B2 #2, #3, #4, #5 — pull
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("reference", [TASK_ID, "86c1abcd", FOLDER])
def test_pull_finds_the_package_by_any_reference(dev_repo: Path, run_cli, reference: str) -> None:
    code, out, err = run_cli("pull", reference, cwd=dev_repo)
    assert code == 0, err
    assert TASK_ID in out


def test_pull_copies_researcher_files_and_writes_a_matching_lock(dev_repo: Path, run_cli) -> None:
    code, _out, err = run_cli("pull", TASK_ID, cwd=dev_repo)
    assert code == 0, err
    destination = dev_repo / ".wizrelay" / "tasks" / FOLDER

    assert (destination / "task.json").is_file()
    assert (destination / "roles" / "backend.md").is_file()
    # Invariant I8: a dot-prefixed file never reaches a developer repository.
    assert not (destination / ".validation.md").exists()
    # Developer files are created for you.
    assert (destination / "plan.md").is_file()
    assert (destination / "questions.md").is_file()

    # Every hash in the lock matches the file on disk.
    document = lock.load(destination / lock.LOCK_FILENAME)
    assert document is not None
    report = lock.verify(destination, document, present=package.researcher_files(destination))
    assert report.clean, report.as_dict()
    assert document["task_id"] == TASK_ID
    assert document["hub_id"]
    assert document["routing"]["tier"]


def test_pull_makes_the_package_active(dev_repo: Path, run_cli) -> None:
    run_cli("pull", TASK_ID, cwd=dev_repo)
    pointer = dev_repo / ".wizrelay" / paths.ACTIVE_TASK_FILE
    assert pointer.read_text(encoding="utf-8").strip() == FOLDER


def test_pull_never_overwrites_a_developer_file(dev_repo: Path, run_cli) -> None:
    """A developer file is never overwritten by a pull."""
    run_cli("pull", TASK_ID, cwd=dev_repo)
    destination = dev_repo / ".wizrelay" / "tasks" / FOLDER
    (destination / "plan.md").write_text("# MY plan\n\n- [ ] my step\n", encoding="utf-8")

    run_cli("pull", TASK_ID, cwd=dev_repo)
    assert (destination / "plan.md").read_text(encoding="utf-8") == "# MY plan\n\n- [ ] my step\n"


def test_pull_rejects_a_draft_unless_asked(dev_repo: Path, hub: Path, run_cli) -> None:
    """B2 #3."""
    task_path = hub / "tasks" / FOLDER / "task.json"
    document = _read_json(task_path)
    document["status"] = "draft"
    task_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    code, _out, err = run_cli("pull", TASK_ID, cwd=dev_repo)
    assert code == 2
    assert "draft" in err.lower() or "allow-draft" in err

    code, _out, err = run_cli("pull", TASK_ID, "--allow-draft", cwd=dev_repo)
    assert code == 0, err


def test_pull_warns_when_the_role_is_not_in_the_task(dev_repo: Path, run_cli) -> None:
    """B2 #5."""
    config_path = dev_repo / ".wizrelay" / "config.json"
    document = _read_json(config_path)
    document["role"] = "mobile"
    config_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    code, out, _err = run_cli("pull", TASK_ID, cwd=dev_repo)
    assert code == 0
    assert "no scope" in out.lower() or "mobile" in out


def test_pull_rejects_an_ambiguous_reference(dev_repo: Path, hub: Path, run_cli) -> None:
    import shutil

    shutil.copytree(hub / "tasks" / FOLDER, hub / "tasks" / f"{TASK_ID}-other")
    code, _out, err = run_cli("pull", TASK_ID, cwd=dev_repo)
    assert code == 2
    assert "more than one" in err


def test_pull_removes_a_file_deleted_in_the_hub(dev_repo: Path, hub: Path, run_cli) -> None:
    """B2 #6."""
    run_cli("pull", TASK_ID, cwd=dev_repo)
    destination = dev_repo / ".wizrelay" / "tasks" / FOLDER
    assert (destination / "roles" / "backend.md").exists()

    (hub / "tasks" / FOLDER / "roles" / "backend.md").unlink()
    code, out, _err = run_cli("pull", TASK_ID, cwd=dev_repo)
    assert code == 0
    assert not (destination / "roles" / "backend.md").exists()
    assert "roles/backend.md" in out


def test_pull_refuses_an_oversized_package_by_name(dev_repo: Path, hub: Path, run_cli) -> None:
    """An oversized package is refused by name, before anything is written."""
    (hub / "tasks" / FOLDER / "huge.bin").write_bytes(b"0" * (package.MAX_FILE_BYTES + 1))
    code, _out, err = run_cli("pull", TASK_ID, cwd=dev_repo)
    assert code == 1
    assert "huge.bin" in err


# --------------------------------------------------------------------------------------
# B2 #7 — sync
# --------------------------------------------------------------------------------------


def test_sync_reports_no_changes(dev_repo: Path, run_cli) -> None:
    run_cli("pull", TASK_ID, cwd=dev_repo)
    code, out, _err = run_cli("sync", cwd=dev_repo)
    assert code == 0
    assert "nothing changed" in out
    assert "nothing to reconcile" in out


def test_sync_shows_the_version_change_and_a_diff(dev_repo: Path, hub: Path, run_cli) -> None:
    """`sync` reports the version change and the diff."""
    run_cli("pull", TASK_ID, cwd=dev_repo)

    task_path = hub / "tasks" / FOLDER / "task.json"
    document = _read_json(task_path)
    document["version"] = 2
    task_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    decisions = hub / "tasks" / FOLDER / "decisions.md"
    decisions.write_text(
        decisions.read_text(encoding="utf-8")
        + "\n## D-002 A new decision (v2, 2026-10-31)\n\n- Decision: cap it.\n",
        encoding="utf-8",
    )

    code, out, _err = run_cli("sync", cwd=dev_repo)
    assert code == 0
    assert "v1 to v2" in out
    assert "decisions.md" in out
    assert "+## D-002 A new decision (v2, 2026-10-31)" in out
    # decisions.md changed, so the next-step message says to re-read it.
    assert "Re-read it" in out


def test_sync_restores_a_locally_modified_researcher_file(dev_repo: Path, run_cli) -> None:
    """`sync` restores a researcher file edited locally."""
    run_cli("pull", TASK_ID, cwd=dev_repo)
    scope_path = dev_repo / ".wizrelay" / "tasks" / FOLDER / "scope.md"
    original = scope_path.read_text(encoding="utf-8")
    scope_path.write_text(original + "\nI edited this.\n", encoding="utf-8")

    code, out, _err = run_cli("sync", cwd=dev_repo)
    assert code == 0
    assert "Restored" in out
    assert scope_path.read_text(encoding="utf-8") == original


def test_sync_truncates_a_very_long_diff(dev_repo: Path, hub: Path, run_cli) -> None:
    run_cli("pull", TASK_ID, cwd=dev_repo)
    research = hub / "tasks" / FOLDER / "research.md"
    research.write_text("\n".join(f"line {i}" for i in range(600)) + "\n", encoding="utf-8")
    code, out, _err = run_cli("sync", cwd=dev_repo)
    assert code == 0
    assert "truncated at 250 lines" in out


def test_sync_without_an_active_task_explains_what_to_do(dev_repo: Path, run_cli) -> None:
    code, _out, err = run_cli("sync", cwd=dev_repo)
    assert code == 2
    assert "wizrelay pull" in err


# --------------------------------------------------------------------------------------
# B2 #8 — the active task
# --------------------------------------------------------------------------------------


def test_the_pointer_wins_over_the_branch_name(dev_repo: Path, hub: Path, run_cli) -> None:
    import shutil

    shutil.copytree(hub / "tasks" / FOLDER, hub / "tasks" / "CU-99999999-other")
    other = _read_json(hub / "tasks" / "CU-99999999-other" / "task.json")
    other["id"] = "CU-99999999"
    (hub / "tasks" / "CU-99999999-other" / "task.json").write_text(
        json.dumps(other, indent=2) + "\n", encoding="utf-8"
    )

    run_cli("pull", TASK_ID, cwd=dev_repo)
    run_cli("pull", "CU-99999999", cwd=dev_repo)
    _git(dev_repo, "checkout", "-q", "-b", f"feature/{TASK_ID}-x")

    code, out, _err = run_cli("status", "--json", cwd=dev_repo)
    assert code == 0
    payload = json.loads(out)
    # `pull` set the pointer to the second package, and the pointer wins.
    assert payload["task"]["id"] == "CU-99999999"
    assert payload["task"]["active_source"] == "pointer"


def test_the_branch_name_is_used_without_a_pointer(dev_repo: Path, run_cli) -> None:
    run_cli("pull", TASK_ID, cwd=dev_repo)
    (dev_repo / ".wizrelay" / paths.ACTIVE_TASK_FILE).unlink()
    _git(dev_repo, "checkout", "-q", "-b", f"feature/{TASK_ID}-quota")

    _code, out, _err = run_cli("status", "--json", cwd=dev_repo)
    payload = json.loads(out)
    assert payload["task"]["id"] == TASK_ID
    assert payload["task"]["active_source"] == "branch"


def test_activate_and_clear(dev_repo: Path, run_cli) -> None:
    run_cli("pull", TASK_ID, cwd=dev_repo)
    code, out, _err = run_cli("activate", "--clear", cwd=dev_repo)
    assert code == 0 and "cleared" in out
    code, out, _err = run_cli("activate", FOLDER, cwd=dev_repo)
    assert code == 0 and FOLDER in out
    code, _out, err = run_cli("activate", cwd=dev_repo)
    assert code == 2
    assert "activate" in err


# --------------------------------------------------------------------------------------
# B2 #9, #10 — audit
# --------------------------------------------------------------------------------------


def test_audit_exit_codes(dev_repo: Path, run_cli) -> None:
    """B2 #10."""
    run_cli("pull", TASK_ID, cwd=dev_repo)
    code, _out, _err = run_cli("audit", "--base", "", cwd=dev_repo)
    assert code == 0

    (dev_repo / "app" / "billing").mkdir(parents=True, exist_ok=True)
    (dev_repo / "app" / "billing" / "x.py").write_text("oops\n", encoding="utf-8")
    code, out, _err = run_cli("audit", "--base", "", cwd=dev_repo)
    assert code == 1
    assert "app/billing/x.py" in out

    code, _out, _err = run_cli("audit", "--base", "", "--no-fail", cwd=dev_repo)
    assert code == 0


def test_audit_json_output_carries_a_schema_version(dev_repo: Path, run_cli) -> None:
    """`audit --json` carries a schema version."""
    run_cli("pull", TASK_ID, cwd=dev_repo)
    code, out, _err = run_cli("audit", "--base", "", "--format", "json", cwd=dev_repo)
    assert code == 0
    payload = json.loads(out)
    assert payload["schema_version"] == 1
    assert payload["task_id"] == TASK_ID


def test_audit_finds_the_task_from_a_branch_name(dev_repo: Path, run_cli) -> None:
    """The active task is found from the branch name."""
    run_cli("pull", TASK_ID, cwd=dev_repo)
    (dev_repo / ".wizrelay" / paths.ACTIVE_TASK_FILE).unlink()

    code, out, _err = run_cli(
        "audit",
        "--base",
        "",
        "--branch",
        f"refs/heads/feature/{TASK_ID}-x",
        "--format",
        "json",
        cwd=dev_repo,
    )
    assert code == 0
    assert json.loads(out)["task_id"] == TASK_ID


def test_audit_skips_when_no_task_matches_the_branch(dev_repo: Path, run_cli) -> None:
    """A skip by default, a failure with --require-task."""
    run_cli("pull", TASK_ID, cwd=dev_repo)
    code, out, _err = run_cli(
        "audit", "--base", "", "--branch", "chore/bump-deps", "--format", "json", cwd=dev_repo
    )
    assert code == 0
    assert json.loads(out)["skipped"] is True

    code, _out, _err = run_cli(
        "audit", "--base", "", "--branch", "chore/bump-deps", "--require-task", cwd=dev_repo
    )
    assert code == 1


def test_audit_in_an_unconnected_repository_skips(tmp_path: Path, run_cli) -> None:
    root = tmp_path / "plain"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main", ".")
    code, out, _err = run_cli("audit", cwd=root)
    assert code == 0
    assert "not connected" in out


# --------------------------------------------------------------------------------------
# brief, status, route, doctor
# --------------------------------------------------------------------------------------


def test_brief_always_exits_zero(tmp_path: Path, dev_repo: Path, run_cli) -> None:
    """A non-zero exit from an injected command aborts the whole skill."""
    plain = tmp_path / "nowhere"
    plain.mkdir()
    for cwd, sentinel in (
        (plain, "NO_INIT"),
        (dev_repo, "NO_ACTIVE_TASK"),
    ):
        code, out, _err = run_cli("brief", cwd=cwd)
        assert code == 0
        assert out.startswith(sentinel), out[:80]

    run_cli("pull", TASK_ID, cwd=dev_repo)
    code, out, _err = run_cli("brief", "--phase", "plan", cwd=dev_repo)
    assert code == 0
    assert "Active research package" in out
    assert "plan phase" in out


def test_brief_warns_when_the_session_has_no_heartbeat(dev_repo: Path, run_cli) -> None:
    """`brief` warns when the session has no heartbeat."""
    run_cli("pull", TASK_ID, cwd=dev_repo)
    code, out, _err = run_cli("brief", "--session", "never-ran", cwd=dev_repo)
    assert code == 0
    assert out.startswith("WIZRELAY_NO_GUARD")
    assert "disableAllHooks" in out


def test_brief_is_quiet_when_the_heartbeat_exists(dev_repo: Path, run_cli) -> None:
    from wizrelay import context as context_mod

    run_cli("pull", TASK_ID, cwd=dev_repo)
    context_mod.heartbeat_write("live-session")
    code, out, _err = run_cli("brief", "--session", "live-session", cwd=dev_repo)
    assert code == 0
    assert "WIZRELAY_NO_GUARD" not in out


def test_brief_with_an_empty_session_id_does_not_warn(dev_repo: Path, run_cli) -> None:
    # The skills pass `${CLAUDE_SESSION_ID:-}`, which is empty when the variable is unset.
    # A false guard warning on every invocation would be worse than no warning at all.
    run_cli("pull", TASK_ID, cwd=dev_repo)
    code, out, _err = run_cli("brief", "--session", "", cwd=dev_repo)
    assert code == 0
    assert "WIZRELAY_NO_GUARD" not in out


def test_status_and_route(dev_repo: Path, run_cli) -> None:
    run_cli("pull", TASK_ID, cwd=dev_repo)
    code, out, _err = run_cli("status", cwd=dev_repo)
    assert code == 0
    assert TASK_ID in out
    assert "Launch command" in out

    code, out, _err = run_cli("route", "--json", cwd=dev_repo)
    assert code == 0
    payload = json.loads(out)
    assert payload["schema_version"] == 1
    assert payload["tier"]
    assert payload["launch"].startswith("claude --model")


def test_status_json_in_an_unconnected_repository(tmp_path: Path, run_cli) -> None:
    root = tmp_path / "plain2"
    root.mkdir()
    code, out, _err = run_cli("status", "--json", cwd=root)
    assert code == 0
    assert json.loads(out)["persona"] == "none"


def test_doctor_reports_and_exits_zero_when_healthy(dev_repo: Path, run_cli) -> None:
    run_cli("pull", TASK_ID, cwd=dev_repo)
    code, out, _err = run_cli("doctor", "--json", cwd=dev_repo)
    payload = json.loads(out)
    assert payload["schema_version"] == 1
    assert payload["persona"] == "developer"
    names = {check["name"] for check in payload["checks"]}
    assert {"python", "git", "duplicate-plugin-name", "role", "hub", "active-task"} <= names
    assert code in (0, 1)


def test_doctor_flags_a_placeholder_role(dev_repo: Path, run_cli) -> None:
    config_path = dev_repo / ".wizrelay" / "config.json"
    document = _read_json(config_path)
    document["role"] = "{{role}}"
    config_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    code, out, _err = run_cli("doctor", "--json", cwd=dev_repo)
    assert code == 1
    role_check = next(c for c in json.loads(out)["checks"] if c["name"] == "role")
    assert role_check["level"] == "error"


# --------------------------------------------------------------------------------------
# B2 #12, #13, #14 — hub commands
# --------------------------------------------------------------------------------------


def test_hub_init_then_new_then_validate_then_publish(tmp_path: Path, run_cli) -> None:
    hub_root = tmp_path / "newhub"
    hub_root.mkdir()
    _git(hub_root, "init", "-q", "-b", "main", ".")

    code, _out, err = run_cli("hub", "init", "--name", "acme", "--tracker", "clickup", cwd=hub_root)
    assert code == 0, err
    assert (hub_root / paths.HUB_MARKER).is_file()

    marker = _read_json(hub_root / paths.HUB_MARKER)
    marker.update({"name": "acme", "roles": ["backend"], "language": "en"})
    (hub_root / paths.HUB_MARKER).write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")

    code, out, err = run_cli(
        "hub", "new", "86c1abcd", "--title", "Tenant quota", "--roles", "backend", cwd=hub_root
    )
    assert code == 0, err
    directory = hub_root / "tasks" / f"{TASK_ID}-tenant-quota"
    assert (directory / "acceptance.md").is_file()
    # A single-role package gets no contracts.md.
    assert not (directory / "contracts.md").exists()

    # B2 #12: the scaffold is deliberately unpublishable.
    code, out, _err = run_cli("hub", "validate", TASK_ID, cwd=hub_root)
    assert code == 1
    assert "unfilled placeholder" in out
    assert ":" in out, "every finding needs a file:line reference"
    assert (directory / ".validation.md").is_file()

    # B2 #13: publish-prep refuses while errors remain.
    code, _out, err = run_cli("hub", "publish-prep", TASK_ID, "--summary", "First", cwd=hub_root)
    assert code == 1
    assert "validation error" in err


def test_hub_validate_reports_the_documented_errors_and_warnings(tmp_path: Path, run_cli) -> None:
    """B2 #12."""
    hub_root = tmp_path / "vhub"
    hub_root.mkdir()
    _git(hub_root, "init", "-q", "-b", "main", ".")
    run_cli("hub", "init", "--name", "v", cwd=hub_root)
    marker = _read_json(hub_root / paths.HUB_MARKER)
    marker.update({"name": "v", "roles": ["backend"], "language": "en"})
    (hub_root / paths.HUB_MARKER).write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")

    directory = hub_root / "tasks" / "CU-1-x"
    (directory / "roles").mkdir(parents=True)
    (directory / "task.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": "CU-1",
                "title": "T",
                "version": 0,
                "status": "draft",
                "roles": ["backend"],
                "scope": {"backend": {"allow": ["app/**"], "deny": []}},
                "routing": {"signals": {"ambiguity": "high"}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (directory / "research.md").write_text("# R\n\nTBD\n", encoding="utf-8")
    (directory / "scope.md").write_text("# S\n\nTODO: finish\n", encoding="utf-8")
    (directory / "acceptance.md").write_text(
        "# A\n\n## AC-1 [mobile] Wrong role\n\nJust prose.\n", encoding="utf-8"
    )
    (directory / "decisions.md").write_text("# D\n", encoding="utf-8")
    (directory / "roles" / "backend.md").write_text("# backend\n", encoding="utf-8")

    code, out, _err = run_cli("hub", "validate", "CU-1", cwd=hub_root)
    assert code == 1
    # Errors
    assert "contains TBD" in out
    assert "names unknown role 'mobile'" in out
    assert "role 'backend' has no acceptance criterion" in out
    # Warnings
    assert "contains TODO" in out
    assert "no verification line" in out
    assert "no Given/When/Then" in out
    assert "ambiguity is high" in out


def test_hub_publish_prep_bumps_the_version_and_keeps_the_format(hub: Path, run_cli) -> None:
    """B2 #13."""
    code, _out, err = run_cli(
        "hub", "publish-prep", TASK_ID, "--summary", "Retry-After cap", cwd=hub
    )
    assert code == 0, err
    document = _read_json(hub / "tasks" / FOLDER / "task.json")
    assert document["version"] == 2
    assert document["status"] == "published"
    assert document["changelog"][-1]["summary"] == "Retry-After cap"
    assert document["updated_at"]

    text = (hub / "tasks" / FOLDER / "task.json").read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert '  "id"' in text


def test_hub_comment_encodes_the_deep_link_and_fences_it(hub: Path, run_cli) -> None:
    """B2 #14."""
    code, out, err = run_cli("hub", "comment", TASK_ID, cwd=hub)
    assert code == 0, err
    assert out.startswith(f"[WIZRELAY-PUBLISH] {TASK_ID} — research v1 published")
    assert "**backend**" in out
    assert "AC-1:" in out
    assert f"/wizrelay:pull {TASK_ID}" in out
    # The prompt is encoded with safe="", so both `/` and `:` escape.
    assert "q=%2Fwizrelay%3Apull%20CU-86c1abcd" in out
    assert "claude-cli://open?repo=acme%2Fapi-service" in out
    # GitHub strips `claude-cli://` links, so the URL has to be in a fence.
    assert "```\nclaude-cli://" in out


def test_hub_comment_omits_a_deep_link_for_a_role_without_a_repo(hub: Path, run_cli) -> None:
    task_path = hub / "tasks" / FOLDER / "task.json"
    document = _read_json(task_path)
    document["roles"] = ["backend", "frontend"]
    document["scope"]["frontend"] = {"allow": ["src/**"], "deny": []}
    document["repos"] = {"backend": "acme/api-service"}
    task_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    code, out, _err = run_cli("hub", "comment", TASK_ID, cwd=hub)
    assert code == 0
    assert out.count("claude-cli://open") == 1


def test_hub_list(hub: Path, run_cli) -> None:
    code, out, _err = run_cli("hub", "list", "--json", cwd=hub)
    assert code == 0
    payload = json.loads(out)
    assert payload["packages"][0]["id"] == TASK_ID

    code, out, _err = run_cli("hub", "list", cwd=hub)
    assert code == 0
    assert TASK_ID in out


def test_a_hub_command_outside_a_hub_explains_itself(dev_repo: Path, run_cli) -> None:
    code, _out, err = run_cli("hub", "list", cwd=dev_repo)
    assert code == 2
    assert "hub init" in err


def test_a_manually_written_package_validates_the_same_way(
    tmp_path: Path, hub: Path, run_cli
) -> None:
    """A hand-written package validates like a generated one."""
    import shutil

    manual = hub / "tasks" / "CU-11111111-manual"
    shutil.copytree(hub / "tasks" / FOLDER, manual)
    document = _read_json(manual / "task.json")
    document["id"] = "CU-11111111"
    document["slug"] = "manual"
    (manual / "task.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    code_a, out_a, _err = run_cli("hub", "validate", TASK_ID, cwd=hub)
    code_b, out_b, _err = run_cli("hub", "validate", "CU-11111111", cwd=hub)
    assert code_a == code_b == 0
    assert "No errors and no warnings" in out_a
    assert "No errors and no warnings" in out_b


# --------------------------------------------------------------------------------------
# B2 #11 — TTL, and multiple hubs (invariants I3, I4)
# --------------------------------------------------------------------------------------


def test_a_local_hub_working_copy_is_never_modified(dev_repo: Path, hub: Path, run_cli) -> None:
    """A user with the hub open in an editor must not have their tree moved."""
    before = {
        p.relative_to(hub): p.read_bytes()
        for p in sorted(hub.rglob("*"))
        if p.is_file() and ".git/" not in p.as_posix()
    }
    run_cli("pull", TASK_ID, cwd=dev_repo)
    after = {
        p.relative_to(hub): p.read_bytes()
        for p in sorted(hub.rglob("*"))
        if p.is_file() and ".git/" not in p.as_posix()
    }
    assert before == after


def test_two_hubs_with_the_same_task_id_do_not_mix(tmp_path: Path, hub: Path, run_cli) -> None:
    """Two hubs sharing a task identifier stay apart."""
    import shutil

    second = tmp_path / "hub2"
    shutil.copytree(hub, second)
    marker = _read_json(second / paths.HUB_MARKER)
    marker["name"] = "second-hub"
    (second / paths.HUB_MARKER).write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    research = second / "tasks" / FOLDER / "research.md"
    research.write_text("# Research\n\nThis is the SECOND hub's analysis.\n", encoding="utf-8")

    first_repo = tmp_path / "repo-a"
    second_repo = tmp_path / "repo-b"
    for root, hub_path in ((first_repo, hub), (second_repo, second)):
        root.mkdir()
        _git(root, "init", "-q", "-b", "main", ".")
        run_cli("init", "--role", "backend", "--hub-path", str(hub_path), cwd=root)
        code, _out, err = run_cli("pull", TASK_ID, cwd=root)
        assert code == 0, err

    first_text = (first_repo / ".wizrelay" / "tasks" / FOLDER / "research.md").read_text(
        encoding="utf-8"
    )
    second_text = (second_repo / ".wizrelay" / "tasks" / FOLDER / "research.md").read_text(
        encoding="utf-8"
    )
    assert "SECOND hub" not in first_text
    assert "SECOND hub" in second_text

    # The locks record different hub identities, which is how they stay apart.
    first_lock = lock.load(first_repo / ".wizrelay" / "tasks" / FOLDER / lock.LOCK_FILENAME)
    second_lock = lock.load(second_repo / ".wizrelay" / "tasks" / FOLDER / lock.LOCK_FILENAME)
    assert first_lock is not None and second_lock is not None
    assert first_lock["hub_id"] != second_lock["hub_id"]


def test_one_hub_serves_two_roles(tmp_path: Path, hub: Path, run_cli) -> None:
    """Invariant I3: one package, two repositories, different scopes."""
    task_path = hub / "tasks" / FOLDER / "task.json"
    document = _read_json(task_path)
    document["roles"] = ["backend", "frontend"]
    document["scope"]["frontend"] = {"allow": ["src/features/quota/**"], "deny": []}
    task_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    acceptance = hub / "tasks" / FOLDER / "acceptance.md"
    acceptance.write_text(
        acceptance.read_text(encoding="utf-8")
        + "\n## AC-3 [frontend] The quota is visible\n\nThen it shows.\nVerification: `npm test`\n",
        encoding="utf-8",
    )
    (hub / "tasks" / FOLDER / "roles" / "frontend.md").write_text("# frontend\n", encoding="utf-8")

    scopes = {}
    for role in ("backend", "frontend"):
        root = tmp_path / f"repo-{role}"
        root.mkdir()
        _git(root, "init", "-q", "-b", "main", ".")
        run_cli("init", "--role", role, "--hub-path", str(hub), cwd=root)
        run_cli("pull", TASK_ID, cwd=root)
        code, out, _err = run_cli("status", "--json", cwd=root)
        assert code == 0
        scopes[role] = json.loads(out)["task"]["scope"]["allow"]

    assert scopes["backend"] != scopes["frontend"]
    assert "src/features/quota/**" in scopes["frontend"]


# --------------------------------------------------------------------------------------
# B2 — migrate
# --------------------------------------------------------------------------------------


def test_migrate_from_the_prototype_layout(tmp_path: Path, run_cli) -> None:
    """The prototype layout migrates without loss."""
    root = tmp_path / "proto"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main", ".")
    legacy = root / ".ai"
    (legacy / "tasks" / "CU-1-x").mkdir(parents=True)
    (legacy / "project-profile.json").write_text('{"schema_version": 1}\n', encoding="utf-8")
    (legacy / "config.json").write_text(
        '{"schema_version": 1, "role": "backend"}\n', encoding="utf-8"
    )
    (legacy / "PROTOCOL.md").write_text(
        "Files live in .ai/ and tags look like [RW-PUBLISH]. Run /task:pull.\n", encoding="utf-8"
    )
    (legacy / "tasks" / "CU-1-x" / "research.md").write_text("# R\n", encoding="utf-8")

    code, _out, err = run_cli("migrate", "--from-prototype", cwd=root)
    assert code == 0, err
    assert (root / ".wizrelay" / "profile.json").is_file()
    assert (root / ".wizrelay" / "config.json").is_file()
    assert (root / ".wizrelay" / "tasks" / "CU-1-x" / "research.md").is_file()
    assert not legacy.exists()

    protocol = (root / ".wizrelay" / "PROTOCOL.md").read_text(encoding="utf-8")
    assert ".wizrelay/" in protocol
    assert "[WIZRELAY-PUBLISH]" in protocol
    assert "/wizrelay:pull" in protocol
    assert ".ai/" not in protocol
    assert "[RW-" not in protocol


def test_migrate_with_nothing_to_do(tmp_path: Path, run_cli) -> None:
    root = tmp_path / "nothing"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main", ".")
    code, out, _err = run_cli("migrate", "--from-prototype", cwd=root)
    assert code == 0
    assert "Nothing to migrate" in out


# --------------------------------------------------------------------------------------
# Routing consistency across surfaces
# --------------------------------------------------------------------------------------


def test_pull_route_status_and_the_lock_agree_on_the_tier(
    dev_repo: Path, hub: Path, run_cli
) -> None:
    """A team policy has to reach every surface, not only `pull`.

    `pull` resolves the hub, so it reads `policies/routing-policy.json`. `route`, `status`
    and the session context do not resolve the hub, and before `hubrepo.local_policy`
    existed they silently fell back to the plugin default — so a user could be shown one
    tier and told to launch a session for another.
    """
    policy_path = hub / "policies" / "routing-policy.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "modifiers": {},
                "tiers": [
                    {
                        "name": "TEAM-only",
                        "max_score": 99,
                        "phases": {
                            "plan": {"model": "haiku", "effort": "low"},
                            "implement": {"model": "haiku", "effort": "low"},
                            "verify": {"model": "haiku", "effort": "low"},
                            "ask": {"model": "haiku", "effort": "low"},
                        },
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    code, pull_out, err = run_cli("pull", TASK_ID, cwd=dev_repo)
    assert code == 0, err
    assert "TEAM-only" in pull_out

    code, route_out, _err = run_cli("route", "--json", cwd=dev_repo)
    assert code == 0
    assert json.loads(route_out)["tier"] == "TEAM-only"

    code, status_out, _err = run_cli("status", "--json", cwd=dev_repo)
    assert code == 0
    assert json.loads(status_out)["routing"]["tier"] == "TEAM-only"

    document = lock.load(dev_repo / ".wizrelay" / "tasks" / FOLDER / lock.LOCK_FILENAME)
    assert document is not None
    assert document["routing"]["tier"] == "TEAM-only"

    code, brief_out, _err = run_cli("brief", cwd=dev_repo)
    assert code == 0
    assert "TEAM-only" in brief_out


def test_the_examples_directory_is_a_working_hub_and_two_repositories(
    tmp_path: Path, run_cli
) -> None:
    """The examples are documentation, so they have to keep working.

    Invariant I3 in miniature: one hub, one package, two roles, two different tiers.
    """
    import shutil

    repo_root = Path(__file__).resolve().parent.parent.parent
    workspace = tmp_path / "examples"
    shutil.copytree(repo_root / "examples", workspace)
    for name in ("hub", "dev-backend", "dev-frontend"):
        _git(workspace / name, "init", "-q", "-b", "main", ".")
        _git(workspace / name, "add", "-A")
        _git(workspace / name, "commit", "-qm", "init")

    code, out, err = run_cli("hub", "validate", "CU-86c1abcd", cwd=workspace / "hub")
    assert code == 0, f"the example package must validate cleanly: {out}{err}"

    tiers = {}
    for name in ("dev-backend", "dev-frontend"):
        code, _out, err = run_cli("pull", "CU-86c1abcd", cwd=workspace / name)
        assert code == 0, err
        code, out, _err = run_cli("route", "--json", cwd=workspace / name)
        assert code == 0
        tiers[name] = json.loads(out)["tier"]

    assert tiers["dev-backend"] != tiers["dev-frontend"], tiers
    assert tiers["dev-frontend"].startswith("T1")
