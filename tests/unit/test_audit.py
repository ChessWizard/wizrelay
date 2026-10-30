"""Scope and integrity auditing."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from wizrelay import audit as audit_mod
from wizrelay import gitcmd, lock
from wizrelay.i18n import load as load_translator

TASK: dict[str, Any] = {
    "id": "CU-1",
    "roles": ["backend"],
    "enforcement": "strict",
    "scope": {"backend": {"allow": ["app/quota/**"], "deny": ["app/billing/**"]}},
}


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=str(root), check=True, capture_output=True, text=True, shell=False
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main", ".")
    for directory in ("app/quota", "app/billing", "docs"):
        (root / directory).mkdir(parents=True)
    (root / "app" / "quota" / "a.py").write_text("x\n", encoding="utf-8")
    (root / "app" / "billing" / "b.py").write_text("y\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("z\n", encoding="utf-8")
    (root / "old.py").write_text("o\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    return root


def test_a_clean_tree_has_no_violations(repo: Path) -> None:
    report = audit_mod.audit(repo, task=TASK, role="backend")
    assert report.clean is True
    assert report.violations == 0


def test_in_scope_denied_and_out_of_scope_are_separated(repo: Path) -> None:
    (repo / "app" / "quota" / "a.py").write_text("changed\n", encoding="utf-8")
    (repo / "app" / "billing" / "b.py").write_text("changed\n", encoding="utf-8")
    (repo / "docs" / "guide.md").write_text("changed\n", encoding="utf-8")

    report = audit_mod.audit(repo, task=TASK, role="backend")
    assert report.in_scope == ["app/quota/a.py"]
    assert report.forbidden == [("app/billing/b.py", "app/billing/**")]
    assert report.out_of_scope == ["docs/guide.md"]
    assert report.violations == 2


def test_a_rename_reports_only_the_destination(repo: Path) -> None:
    """Appendix B2 #9: a rename record occupies two porcelain entries."""
    _git(repo, "mv", "old.py", "new.py")
    report = audit_mod.audit(repo, task=TASK, role="backend")
    assert "new.py" in report.out_of_scope
    assert "old.py" not in report.out_of_scope


def test_untracked_files_are_reported(repo: Path) -> None:
    (repo / "surprise.txt").write_text("x\n", encoding="utf-8")
    report = audit_mod.audit(repo, task=TASK, role="backend")
    assert "surprise.txt" in report.out_of_scope


def test_deleted_files_are_reported(repo: Path) -> None:
    (repo / "docs" / "guide.md").unlink()
    report = audit_mod.audit(repo, task=TASK, role="backend")
    assert "docs/guide.md" in report.out_of_scope


def test_lock_files_are_incidental_at_any_depth(repo: Path) -> None:
    (repo / "poetry.lock").write_text("x\n", encoding="utf-8")
    (repo / "app" / "quota" / "package-lock.json").write_text("{}\n", encoding="utf-8")
    report = audit_mod.audit(repo, task=TASK, role="backend")
    assert "poetry.lock" in report.incidental
    assert report.clean is True


def test_wizrelay_setup_files_are_not_violations(repo: Path) -> None:
    # The first audit after `init` must not report the files `init` itself wrote.
    for name in ("CLAUDE.md", ".gitignore", ".mcp.json"):
        (repo / name).write_text("x\n", encoding="utf-8")
    (repo / ".claude").mkdir(exist_ok=True)
    (repo / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
    report = audit_mod.audit(repo, task=TASK, role="backend")
    assert report.clean is True
    assert set(report.incidental) >= {"CLAUDE.md", ".gitignore", ".mcp.json"}


def test_the_plugin_directory_is_never_audited(repo: Path) -> None:
    (repo / ".wizrelay" / "tasks").mkdir(parents=True)
    (repo / ".wizrelay" / "config.json").write_text("{}\n", encoding="utf-8")
    report = audit_mod.audit(repo, task=TASK, role="backend")
    assert not any(path.startswith(".wizrelay") for path in report.out_of_scope)


def test_profile_incidental_allow_is_honoured(repo: Path) -> None:
    (repo / "docs" / "guide.md").write_text("changed\n", encoding="utf-8")
    report = audit_mod.audit(
        repo, task=TASK, role="backend", profile={"incidental_allow": ["docs/**"]}
    )
    assert report.out_of_scope == []
    assert "docs/guide.md" in report.incidental


def test_no_task_means_a_skip_not_a_failure(repo: Path) -> None:
    """Appendix B2 #10 and task 2.10: no task is a skip."""
    report = audit_mod.audit(repo, task=None)
    assert report.clean is True
    assert any("no task" in note.lower() for note in report.notes)


def test_a_role_with_no_scope_is_reported_without_a_verdict(repo: Path) -> None:
    (repo / "docs" / "guide.md").write_text("changed\n", encoding="utf-8")
    report = audit_mod.audit(repo, task=TASK, role="mobile")
    assert report.scope_defined is False
    assert report.clean is True
    assert any("no scope" in note.lower() for note in report.notes)


def test_a_missing_base_ref_degrades_with_a_note(repo: Path) -> None:
    report = audit_mod.audit(repo, task=TASK, role="backend", base="origin/nonexistent")
    assert report.base_available is False
    assert any("does not resolve" in note for note in report.notes)
    assert report.clean is True


def test_a_resolvable_base_is_used(repo: Path) -> None:
    _git(repo, "checkout", "-q", "-b", "feature")
    (repo / "docs" / "new.md").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "work")
    report = audit_mod.audit(repo, task=TASK, role="backend", base="main")
    assert report.base_available is True
    assert "docs/new.md" in report.out_of_scope


def test_integrity_is_reported_separately(repo: Path, tmp_path: Path) -> None:
    package = repo / ".wizrelay" / "tasks" / "CU-1-x"
    package.mkdir(parents=True)
    (package / "research.md").write_text("tampered\n", encoding="utf-8")
    document = {"files": {"research.md": lock.digest_bytes(b"original\n")}}
    report = audit_mod.audit(
        repo, task=TASK, role="backend", package_dir=package, lock_document=document
    )
    assert report.integrity is not None
    assert report.integrity.changed == ["research.md"]
    assert report.violations == 1


def test_markdown_rendering_names_every_section(repo: Path) -> None:
    (repo / "app" / "billing" / "b.py").write_text("changed\n", encoding="utf-8")
    (repo / "docs" / "guide.md").write_text("changed\n", encoding="utf-8")
    report = audit_mod.audit(repo, task=TASK, role="backend")
    text = audit_mod.render_markdown(report, load_translator("en"))
    assert "CU-1" in text
    assert "app/billing/b.py" in text
    assert "docs/guide.md" in text
    assert "«" not in text, "a missing i18n key leaked into the report"


def test_json_rendering_is_stable(repo: Path) -> None:
    report = audit_mod.audit(repo, task=TASK, role="backend")
    payload = audit_mod.render_json(report)
    assert payload["schema_version"] == 1
    assert set(payload) >= {
        "task_id",
        "role",
        "in_scope",
        "out_of_scope",
        "forbidden",
        "incidental",
        "integrity",
        "violations",
        "clean",
        "notes",
    }


def test_the_in_scope_list_is_truncated_in_markdown(repo: Path) -> None:
    for index in range(25):
        (repo / "app" / "quota" / f"f{index}.py").write_text("x\n", encoding="utf-8")
    report = audit_mod.audit(repo, task=TASK, role="backend")
    text = audit_mod.render_markdown(report, load_translator("en"))
    assert "and 5 more" in text


def test_git_failure_is_reported_rather_than_raised(tmp_path: Path) -> None:
    report = audit_mod.audit(tmp_path, task=TASK, role="backend")
    assert report.clean is True
    assert any("git status" in note for note in report.notes)


def test_changed_paths_handles_a_copy_record(repo: Path) -> None:
    # A copy record, like a rename, occupies two entries.
    paths_list, ok = gitcmd.changed_paths(repo)
    assert ok is True
    assert isinstance(paths_list, list)
